from __future__ import annotations

import json
from pathlib import Path

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from ppt_expert.assets import generate_assets
from ppt_expert.documents import write_contracts
from ppt_expert.models import (
    ArtifactBundle,
    DesignSpec,
    ImagePlan,
    ImageRequest,
    LayoutType,
    OutlinePlan,
    PPTAgentState,
    ReferenceAnalysis,
    StoryDesignBundle,
    StoryPage,
    StyleOption,
    StyleOptions,
    ValidationReport,
)
from ppt_expert.pptx import render_presentation
from ppt_expert.preview import render_previews
from ppt_expert.prompts import (
    image_plan_prompt,
    outline_prompt,
    repair_prompt,
    story_design_prompt,
    styles_prompt,
)
from ppt_expert.references import analyze_references
from ppt_expert.runtime import GraphContext
from ppt_expert.style_preview import render_style_cards
from ppt_expert.validation import validate_presentation, write_validation_report


def build_graph(checkpointer):
    async def parse_outline(
        state: PPTAgentState, runtime: Runtime[GraphContext]
    ) -> dict:
        outline = await runtime.context.host.generate_structured(
            outline_prompt(state["request"]), OutlinePlan
        )
        (Path(state["project_dir"]) / "outline.json").write_text(
            json.dumps(outline.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"outline": outline.model_dump(mode="json"), "repair_attempts": 0}

    def inspect_references(state: PPTAgentState) -> dict:
        template_path = state.get("template_path")
        image_paths = state.get("reference_images", [])
        if not template_path and not image_paths:
            return {"reference_analysis": {}, "reference_decision": "none"}
        analysis = analyze_references(template_path, image_paths)
        style_cards = render_style_cards(
            [analysis.style], Path(state["project_dir"]) / "reference-preview"
        )
        analysis = analysis.model_copy(
            update={"preview_paths": [*analysis.preview_paths, *style_cards]}
        )
        (Path(state["project_dir"]) / "references.json").write_text(
            analysis.model_dump_json(indent=2), encoding="utf-8"
        )
        return {"reference_analysis": analysis.model_dump(mode="json")}

    def route_reference(state: PPTAgentState) -> str:
        return "confirm_reference" if state.get("reference_analysis") else "propose_styles"

    def confirm_reference(state: PPTAgentState) -> dict:
        analysis = ReferenceAnalysis.model_validate(state["reference_analysis"])
        response = interrupt(
            {
                "type": "reference_confirmation",
                "message": "已从关联模板/图片提取风格，请确认使用、调整或忽略",
                "reference": analysis.model_dump(mode="json"),
                "actions": ["use", "adjust", "ignore"],
            }
        )
        payload = response if isinstance(response, dict) else {"action": str(response)}
        action = str(payload.get("action", "")).strip().lower()
        if action in {"use", "confirm", "use_reference", "a"}:
            style = analysis.style
            decision = "use"
        elif action == "adjust":
            style = StyleOption.model_validate(
                {**analysis.style.model_dump(mode="json"), **payload.get("style", {}), "key": "A"}
            )
            decision = "use"
        elif action in {"ignore", "generated", "regenerate"}:
            _write_reference_decision(Path(state["project_dir"]), "ignore")
            return {"reference_decision": "ignore"}
        else:
            raise ValueError("reference action must be use, adjust, or ignore")
        _write_reference_decision(Path(state["project_dir"]), decision)
        return {
            "reference_decision": decision,
            "selected_style": style.model_dump(mode="json"),
        }

    def route_confirmed_reference(state: PPTAgentState) -> str:
        return "build_story_design" if state["reference_decision"] == "use" else "propose_styles"

    async def propose_styles(
        state: PPTAgentState, runtime: Runtime[GraphContext]
    ) -> dict:
        result = await runtime.context.host.generate_structured(
            styles_prompt(state["outline"]), StyleOptions
        )
        project_dir = Path(state["project_dir"])
        previews = render_style_cards(result.options, project_dir / "style-previews")
        return {
            "styles": [item.model_dump(mode="json") for item in result.options],
            "style_preview_paths": previews,
        }

    def confirm_style(state: PPTAgentState) -> dict:
        choice = interrupt(
            {
                "type": "style_confirmation",
                "message": "请选择视觉风格 A/B/C/D",
                "styles": state["styles"],
                "preview_paths": state["style_preview_paths"],
            }
        )
        key = str(choice).strip().upper()
        selected = next((item for item in state["styles"] if item["key"] == key), None)
        if selected is None:
            raise ValueError("style choice must be A, B, C or D")
        return {"selected_style": selected}

    async def build_story_design(
        state: PPTAgentState, runtime: Runtime[GraphContext]
    ) -> dict:
        bundle = await runtime.context.host.generate_structured(
            story_design_prompt(state["outline"], state["selected_style"]),
            StoryDesignBundle,
        )
        outline = OutlinePlan.model_validate(state["outline"])
        pages = _normalize_story(outline, bundle.pages)
        design = _lock_design(bundle.design, StyleOption.model_validate(state["selected_style"]))
        design = _apply_reference_fonts(design, state)
        write_contracts(Path(state["project_dir"]), pages, design)
        return {
            "story": [page.model_dump(mode="json") for page in pages],
            "design": design.model_dump(mode="json"),
        }

    async def plan_images(
        state: PPTAgentState, runtime: Runtime[GraphContext]
    ) -> dict:
        plan = await runtime.context.host.generate_structured(
            image_plan_prompt(state["story"], state["design"]), ImagePlan
        )
        requests = _complete_image_plan(
            [StoryPage.model_validate(item) for item in state["story"]],
            DesignSpec.model_validate(state["design"]),
            plan.images,
        )
        return {"image_plan": [item.model_dump(mode="json") for item in requests]}

    async def create_assets(
        state: PPTAgentState, runtime: Runtime[GraphContext]
    ) -> dict:
        paths = await generate_assets(
            runtime.context.host,
            [ImageRequest.model_validate(item) for item in state["image_plan"]],
            DesignSpec.model_validate(state["design"]),
            Path(state["project_dir"]) / "assets",
        )
        return {"image_paths": paths}

    def render(state: PPTAgentState, runtime: Runtime[GraphContext]) -> dict:
        path = Path(state["project_dir"]) / f"{state['project_name']}.pptx"
        rendered = render_presentation(
            [StoryPage.model_validate(item) for item in state["story"]],
            DesignSpec.model_validate(state["design"]),
            state.get("image_paths", {}),
            path,
            runtime.context.config,
            template_path=(
                state.get("template_path")
                if state.get("reference_decision") == "use"
                else None
            ),
        )
        return {"pptx_path": rendered}

    def validate(state: PPTAgentState) -> dict:
        report = validate_presentation(
            state["pptx_path"],
            OutlinePlan.model_validate(state["outline"]),
            [StoryPage.model_validate(item) for item in state["story"]],
            DesignSpec.model_validate(state["design"]),
            state.get("image_paths", {}),
        )
        write_validation_report(report, Path(state["project_dir"]))
        return {"validation": report.model_dump(mode="json")}

    def route_after_validation(
        state: PPTAgentState, runtime: Runtime[GraphContext]
    ) -> str:
        report = ValidationReport.model_validate(state["validation"])
        if (
            report.valid
            or state.get("repair_attempts", 0)
            >= runtime.context.config.max_repair_attempts
        ):
            return "finish"
        return "repair"

    async def repair(state: PPTAgentState, runtime: Runtime[GraphContext]) -> dict:
        report = ValidationReport.model_validate(state["validation"])
        bundle = await runtime.context.host.generate_structured(
            repair_prompt(
                state["outline"],
                state["story"],
                state["design"],
                [issue.model_dump(mode="json") for issue in report.issues],
            ),
            StoryDesignBundle,
        )
        outline = OutlinePlan.model_validate(state["outline"])
        pages = _normalize_story(outline, bundle.pages)
        design = _lock_design(bundle.design, StyleOption.model_validate(state["selected_style"]))
        design = _apply_reference_fonts(design, state)
        write_contracts(Path(state["project_dir"]), pages, design)
        return {
            "story": [page.model_dump(mode="json") for page in pages],
            "design": design.model_dump(mode="json"),
            "repair_attempts": state.get("repair_attempts", 0) + 1,
        }

    def finish(state: PPTAgentState, runtime: Runtime[GraphContext]) -> dict:
        project_dir = Path(state["project_dir"]).resolve()
        previews = list(state.get("style_preview_paths", []))
        if state.get("reference_decision") == "use" and state.get("reference_analysis"):
            previews.extend(
                ReferenceAnalysis.model_validate(
                    state["reference_analysis"]
                ).preview_paths
            )
        if runtime.context.config.enable_libreoffice_preview:
            previews.extend(render_previews(state["pptx_path"], project_dir / "preview"))
        artifacts = ArtifactBundle(
            project_dir=str(project_dir),
            pptx_path=state["pptx_path"],
            story_path=str((project_dir / "STORY.md").resolve()),
            design_path=str((project_dir / "DESIGN.md").resolve()),
            report_path=str((project_dir / "VALIDATION.md").resolve()),
            preview_paths=previews,
        )
        return {"artifacts": artifacts.model_dump(mode="json")}

    builder = StateGraph(PPTAgentState, context_schema=GraphContext)
    builder.add_node("parse_outline", parse_outline)
    builder.add_node("inspect_references", inspect_references)
    builder.add_node("confirm_reference", confirm_reference)
    builder.add_node("propose_styles", propose_styles)
    builder.add_node("confirm_style", confirm_style)
    builder.add_node("build_story_design", build_story_design)
    builder.add_node("plan_images", plan_images)
    builder.add_node("generate_assets", create_assets)
    builder.add_node("render_pptx", render)
    builder.add_node("validate", validate)
    builder.add_node("repair", repair)
    builder.add_node("finish", finish)
    builder.add_edge(START, "parse_outline")
    builder.add_edge("parse_outline", "inspect_references")
    builder.add_conditional_edges(
        "inspect_references",
        route_reference,
        {
            "confirm_reference": "confirm_reference",
            "propose_styles": "propose_styles",
        },
    )
    builder.add_conditional_edges(
        "confirm_reference",
        route_confirmed_reference,
        {
            "build_story_design": "build_story_design",
            "propose_styles": "propose_styles",
        },
    )
    builder.add_edge("propose_styles", "confirm_style")
    builder.add_edge("confirm_style", "build_story_design")
    builder.add_edge("build_story_design", "plan_images")
    builder.add_edge("plan_images", "generate_assets")
    builder.add_edge("generate_assets", "render_pptx")
    builder.add_edge("render_pptx", "validate")
    builder.add_conditional_edges(
        "validate", route_after_validation, {"repair": "repair", "finish": "finish"}
    )
    builder.add_edge("repair", "render_pptx")
    builder.add_edge("finish", END)
    return builder.compile(checkpointer=checkpointer)


def _normalize_story(outline: OutlinePlan, proposed: list[StoryPage]) -> list[StoryPage]:
    normalized: list[StoryPage] = []
    for index, source in enumerate(outline.pages):
        page = proposed[index] if index < len(proposed) else None
        proposed_content = page.content if page and page.content else []
        content = proposed_content + [
            item for item in source.core_content if item not in proposed_content
        ]
        normalized.append(
            StoryPage(
                number=source.number,
                title=source.title,
                content=content,
                visual_direction=page.visual_direction if page else source.title,
                layout=page.layout if page else (LayoutType.HERO if index == 0 else LayoutType.TEXT),
                image_id=page.image_id if page else ("cover" if index == 0 else None),
                section=source.section,
            )
        )
    return normalized


def _lock_design(design: DesignSpec, style: StyleOption) -> DesignSpec:
    return design.model_copy(
        update={
            "style_name": style.name,
            "mood": style.mood,
            "primary": style.primary,
            "secondary": style.secondary,
            "background": style.background,
            "text": style.text,
            "accent": style.accent,
        }
    )


def _apply_reference_fonts(design: DesignSpec, state: PPTAgentState) -> DesignSpec:
    if state.get("reference_decision") != "use" or not state.get("reference_analysis"):
        return design
    analysis = ReferenceAnalysis.model_validate(state["reference_analysis"])
    updates: dict[str, str] = {}
    if analysis.title_font:
        updates["title_font"] = analysis.title_font
    if analysis.body_font:
        updates["body_font"] = analysis.body_font
    return design.model_copy(update=updates)


def _write_reference_decision(project_dir: Path, decision: str) -> None:
    (project_dir / "reference-selection.json").write_text(
        json.dumps({"decision": decision}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _complete_image_plan(
    pages: list[StoryPage], design: DesignSpec, proposed: list[ImageRequest]
) -> list[ImageRequest]:
    by_id = {item.image_id: item for item in proposed}
    expected: dict[str, list[int]] = {}
    for page in pages:
        if page.image_id:
            expected.setdefault(page.image_id, []).append(page.number)
    result: list[ImageRequest] = []
    for image_id, page_numbers in expected.items():
        if image_id in by_id:
            item = by_id[image_id].model_copy(update={"page_numbers": page_numbers})
        else:
            directions = "；".join(
                page.visual_direction for page in pages if page.image_id == image_id
            )
            item = ImageRequest(
                image_id=image_id,
                page_numbers=page_numbers,
                prompt=(
                    f"{design.illustration_style}，色调使用 {design.primary}、"
                    f"{design.secondary}、{design.background}，{directions}。"
                    "画面中不出现任何文字、水印、签名和清晰五官"
                ),
            )
        result.append(item)
    return result
