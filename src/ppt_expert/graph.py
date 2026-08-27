from __future__ import annotations

import json
import time
from pathlib import Path

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from ppt_expert.assets import generate_assets
from ppt_expert.audition import render_contact_sheet, render_style_auditions
from ppt_expert.composition import choose_compositions
from ppt_expert.documents import write_contracts
from ppt_expert.enrichment import enrich_story
from ppt_expert.models import (
    ArtifactBundle,
    DeckBrief,
    DesignSpec,
    EvidenceBundle,
    EvidenceItem,
    ImagePlan,
    ImageRequest,
    LayoutType,
    OutlinePlan,
    PPTAgentState,
    QualityReport,
    ReferenceAnalysis,
    SlideFamily,
    StoryDesignBundle,
    StoryPage,
    StyleOption,
    StyleOptions,
    TypographyProfile,
    ValidationReport,
)
from ppt_expert.planning import attach_evidence, build_brief, extract_evidence
from ppt_expert.pptx import render_presentation
from ppt_expert.preview import render_previews
from ppt_expert.prompts import (
    image_plan_prompt,
    outline_prompt,
    repair_prompt,
    story_design_prompt,
    styles_prompt,
)
from ppt_expert.quality import score_deck, write_quality_report
from ppt_expert.references import analyze_references
from ppt_expert.repair import merge_repaired_pages
from ppt_expert.runtime import GraphContext
from ppt_expert.style_preview import render_style_cards
from ppt_expert.telemetry import prompt_tokens, record_metric
from ppt_expert.typography import build_profiles, render_specimens, select_profile
from ppt_expert.validation import validate_presentation, write_validation_report
from ppt_expert.vision import apply_vision_review


def build_graph(checkpointer):
    async def parse_outline(
        state: PPTAgentState, runtime: Runtime[GraphContext]
    ) -> dict:
        outline = await _generate(
            runtime, outline_prompt(state["request"]), OutlinePlan, state, "parse_outline"
        )
        brief = build_brief(outline, state["request"])
        evidence = extract_evidence(outline)
        project_dir = Path(state["project_dir"])
        (project_dir / "outline.json").write_text(
            json.dumps(outline.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (project_dir / "brief.json").write_text(brief.model_dump_json(indent=2), encoding="utf-8")
        (project_dir / "evidence.json").write_text(
            evidence.model_dump_json(indent=2), encoding="utf-8"
        )
        return {
            "outline": outline.model_dump(mode="json"),
            "brief": brief.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in evidence.items],
            "repair_attempts": 0,
        }

    def route_brief(state: PPTAgentState) -> str:
        brief = DeckBrief.model_validate(state.get("brief") or {"objective": "draft"})
        return "confirm_brief" if brief.needs_confirmation() else "inspect_references"

    def confirm_brief(state: PPTAgentState) -> dict:
        brief = DeckBrief.model_validate(state["brief"])
        response = interrupt(
            {
                "type": "brief_confirmation",
                "message": "Audience or objective is incomplete. Confirm or edit the brief.",
                "brief": brief.model_dump(mode="json"),
                "actions": ["continue", "edit"],
            }
        )
        payload = response if isinstance(response, dict) else {"action": str(response)}
        action = str(payload.get("action", "continue")).strip().lower()
        if action in {"continue", "ok", "use"}:
            return {}
        if action == "edit":
            updated = brief.model_copy(update=payload.get("brief", {}))
            return {"brief": updated.model_dump(mode="json")}
        raise ValueError("brief action must be continue or edit")

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
                "message": (
                    "A visual direction was extracted from the linked template "
                    "or images. Choose use, adjust, or ignore."
                ),
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
        return "propose_typography" if state["reference_decision"] == "use" else "propose_styles"

    async def propose_styles(
        state: PPTAgentState, runtime: Runtime[GraphContext]
    ) -> dict:
        result = await _generate(
            runtime, styles_prompt(state["outline"]), StyleOptions, state, "propose_styles"
        )
        project_dir = Path(state["project_dir"])
        previews = render_style_auditions(
            result.options,
            OutlinePlan.model_validate(state["outline"]),
            project_dir / "style-previews",
        )
        return {
            "styles": [item.model_dump(mode="json") for item in result.options],
            "style_preview_paths": previews,
        }

    def confirm_style(state: PPTAgentState) -> dict:
        choice = interrupt(
            {
                "type": "style_confirmation",
                "message": (
                    "Choose visual direction A, B, C, or D. Each preview shows a "
                    "cover, an analytical slide, and a close using this deck's copy."
                ),
                "styles": state["styles"],
                "preview_paths": state["style_preview_paths"],
            }
        )
        key = str(choice).strip().upper()
        selected = next((item for item in state["styles"] if item["key"] == key), None)
        if selected is None:
            raise ValueError("style choice must be A, B, C or D")
        return {"selected_style": selected}

    def propose_typography(state: PPTAgentState) -> dict:
        style = StyleOption.model_validate(state["selected_style"])
        outline = OutlinePlan.model_validate(state["outline"])
        reference = None
        if state.get("reference_decision") == "use" and state.get("reference_analysis"):
            reference = ReferenceAnalysis.model_validate(state["reference_analysis"])
        profiles = build_profiles(reference)
        previews = render_specimens(
            profiles, style, outline, Path(state["project_dir"]) / "typography-previews"
        )
        return {
            "typography_profiles": [item.model_dump(mode="json") for item in profiles],
            "typography_preview_paths": previews,
        }

    def confirm_typography(state: PPTAgentState) -> dict:
        profiles = [
            TypographyProfile.model_validate(item) for item in state["typography_profiles"]
        ]
        recommended = next((item.id for item in profiles if item.recommended), profiles[0].id)
        choice = interrupt(
            {
                "type": "typography_confirmation",
                "message": (
                    "Choose a typography profile. Specimens use this deck's headline, "
                    "body copy, and numerals."
                ),
                "profiles": [item.model_dump(mode="json") for item in profiles],
                "preview_paths": state["typography_preview_paths"],
                "recommended": recommended,
                "actions": ["use", "custom"],
            }
        )
        selected = select_profile(profiles, choice)
        (Path(state["project_dir"]) / "typography-selection.json").write_text(
            selected.model_dump_json(indent=2), encoding="utf-8"
        )
        return {"selected_typography": selected.model_dump(mode="json")}

    async def build_story_design(
        state: PPTAgentState, runtime: Runtime[GraphContext]
    ) -> dict:
        bundle = await _generate(
            runtime,
            story_design_prompt(
                state["outline"],
                state["selected_style"],
                evidence=list(state.get("evidence", [])),
                brief=state.get("brief"),
            ),
            StoryDesignBundle,
            state,
            "build_story_design",
        )
        outline = OutlinePlan.model_validate(state["outline"])
        pages, design = _complete_story(outline, bundle.pages, bundle.design, state)
        write_contracts(Path(state["project_dir"]), pages, design)
        return {
            "story": [page.model_dump(mode="json") for page in pages],
            "design": design.model_dump(mode="json"),
        }

    async def plan_images(
        state: PPTAgentState, runtime: Runtime[GraphContext]
    ) -> dict:
        plan = await _generate(
            runtime,
            image_plan_prompt(state["story"], state["design"]),
            ImagePlan,
            state,
            "plan_images",
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
            return "critique"
        return "repair"

    async def repair(state: PPTAgentState, runtime: Runtime[GraphContext]) -> dict:
        report = ValidationReport.model_validate(state["validation"])
        quality_issues = []
        if state.get("quality"):
            quality = QualityReport.model_validate(state["quality"])
            quality_issues = [
                item.model_dump(mode="json")
                for item in [*quality.blocking_issues, *quality.warnings]
            ]
        failing = sorted(
            {
                issue.page
                for issue in report.issues
                if issue.page is not None
            }
        )
        bundle = await _generate(
            runtime,
            repair_prompt(
                state["outline"],
                state["story"],
                state["design"],
                [issue.model_dump(mode="json") for issue in report.issues] + quality_issues,
                pages=failing,
                notes=state.get("draft_notes", ""),
            ),
            StoryDesignBundle,
            state,
            "repair",
        )
        outline = OutlinePlan.model_validate(state["outline"])
        pages, design = _complete_story(outline, bundle.pages, bundle.design, state)
        if failing:
            current = [StoryPage.model_validate(item) for item in state["story"]]
            pages = merge_repaired_pages(current, pages, failing)
        write_contracts(Path(state["project_dir"]), pages, design)
        return {
            "story": [page.model_dump(mode="json") for page in pages],
            "design": design.model_dump(mode="json"),
            "repair_attempts": state.get("repair_attempts", 0) + 1,
        }

    async def critique(state: PPTAgentState, runtime: Runtime[GraphContext]) -> dict:
        started = time.perf_counter()
        pages = [StoryPage.model_validate(item) for item in state["story"]]
        design = DesignSpec.model_validate(state["design"])
        project_dir = Path(state["project_dir"])
        contact = render_contact_sheet(pages, design, project_dir / "preview")
        report = score_deck(
            pages,
            design,
            contact,
            vision_available=runtime.context.host.critique_images is not None,
        )
        report = await apply_vision_review(
            report, runtime.context.host, [contact] if contact else []
        )
        write_quality_report(report, project_dir)
        record_metric(
            project_dir,
            "critique",
            started,
            score=report.score,
            vision_review=report.vision_review,
        )
        return {
            "quality": report.model_dump(mode="json"),
            "contact_sheet_path": contact,
        }

    def route_after_critique(
        state: PPTAgentState, runtime: Runtime[GraphContext]
    ) -> str:
        report = QualityReport.model_validate(state["quality"])
        if (
            report.blocking_issues
            and state.get("repair_attempts", 0) < runtime.context.config.max_repair_attempts
        ):
            return "repair"
        return "confirm_draft"

    def confirm_draft(state: PPTAgentState) -> dict:
        report = QualityReport.model_validate(state["quality"])
        choice = interrupt(
            {
                "type": "draft_confirmation",
                "message": (
                    "Review the contact sheet and quality score, then approve "
                    "delivery or request a targeted revision."
                ),
                "quality": report.model_dump(mode="json"),
                "contact_sheet_path": state.get("contact_sheet_path"),
                "validation": state.get("validation"),
                "actions": ["approve", "revise"],
            }
        )
        payload = choice if isinstance(choice, dict) else {"action": str(choice)}
        action = str(payload.get("action", "approve")).strip().lower()
        if action in {"approve", "accept", "ok", "yes", "a"}:
            return {"draft_decision": "approve"}
        if action == "revise":
            return {
                "draft_decision": "revise",
                "draft_notes": str(payload.get("notes", "")).strip(),
            }
        raise ValueError("draft action must be approve or revise")

    def route_draft(state: PPTAgentState, runtime: Runtime[GraphContext]) -> str:
        if (
            state.get("draft_decision") == "revise"
            and state.get("repair_attempts", 0)
            < runtime.context.config.max_repair_attempts
        ):
            return "repair"
        return "finish"

    def finish(state: PPTAgentState, runtime: Runtime[GraphContext]) -> dict:
        project_dir = Path(state["project_dir"]).resolve()
        previews = list(state.get("style_preview_paths", []))
        if state.get("reference_decision") == "use" and state.get("reference_analysis"):
            previews.extend(
                ReferenceAnalysis.model_validate(
                    state["reference_analysis"]
                ).preview_paths
            )
        previews.extend(state.get("typography_preview_paths", []))
        contact = state.get("contact_sheet_path")
        if contact:
            previews.append(contact)
        if runtime.context.config.enable_libreoffice_preview:
            previews.extend(render_previews(state["pptx_path"], project_dir / "preview"))
        artifacts = ArtifactBundle(
            project_dir=str(project_dir),
            pptx_path=state["pptx_path"],
            story_path=str((project_dir / "STORY.md").resolve()),
            design_path=str((project_dir / "DESIGN.md").resolve()),
            report_path=str((project_dir / "VALIDATION.md").resolve()),
            preview_paths=previews,
            quality_path=str((project_dir / "QUALITY.md").resolve()),
            contact_sheet_path=contact or "",
        )
        return {"artifacts": artifacts.model_dump(mode="json")}

    builder = StateGraph(PPTAgentState, context_schema=GraphContext)
    builder.add_node("parse_outline", parse_outline)
    builder.add_node("confirm_brief", confirm_brief)
    builder.add_node("inspect_references", inspect_references)
    builder.add_node("confirm_reference", confirm_reference)
    builder.add_node("propose_styles", propose_styles)
    builder.add_node("confirm_style", confirm_style)
    builder.add_node("propose_typography", propose_typography)
    builder.add_node("confirm_typography", confirm_typography)
    builder.add_node("build_story_design", build_story_design)
    builder.add_node("plan_images", plan_images)
    builder.add_node("generate_assets", create_assets)
    builder.add_node("render_pptx", render)
    builder.add_node("validate", validate)
    builder.add_node("repair", repair)
    builder.add_node("critique", critique)
    builder.add_node("confirm_draft", confirm_draft)
    builder.add_node("finish", finish)
    builder.add_edge(START, "parse_outline")
    builder.add_conditional_edges(
        "parse_outline",
        route_brief,
        {
            "confirm_brief": "confirm_brief",
            "inspect_references": "inspect_references",
        },
    )
    builder.add_edge("confirm_brief", "inspect_references")
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
            "propose_typography": "propose_typography",
            "propose_styles": "propose_styles",
        },
    )
    builder.add_edge("propose_styles", "confirm_style")
    builder.add_edge("confirm_style", "propose_typography")
    builder.add_edge("propose_typography", "confirm_typography")
    builder.add_edge("confirm_typography", "build_story_design")
    builder.add_edge("build_story_design", "plan_images")
    builder.add_edge("plan_images", "generate_assets")
    builder.add_edge("generate_assets", "render_pptx")
    builder.add_edge("render_pptx", "validate")
    builder.add_conditional_edges(
        "validate", route_after_validation, {"repair": "repair", "critique": "critique"}
    )
    builder.add_conditional_edges(
        "critique",
        route_after_critique,
        {"repair": "repair", "confirm_draft": "confirm_draft"},
    )
    builder.add_conditional_edges(
        "confirm_draft", route_draft, {"repair": "repair", "finish": "finish"}
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
        layout = page.layout if page else (LayoutType.HERO if index == 0 else LayoutType.TEXT)
        normalized.append(
            StoryPage(
                number=source.number,
                title=source.title,
                content=content,
                visual_direction=page.visual_direction if page else source.title,
                layout=layout,
                image_id=page.image_id if page else None,
                section=source.section,
                family=_infer_family(index, page, layout),
                eyebrow=page.eyebrow if page else "",
                subtitle=page.subtitle if page else "",
                takeaway=page.takeaway if page else "",
                source_note=page.source_note if page else "",
                kpis=page.kpis if page else [],
                chart=page.chart if page else None,
                table=page.table if page else None,
                allocation=page.allocation if page else [],
                scenarios=page.scenarios if page else [],
                waterfall=page.waterfall if page else [],
                heatmap=page.heatmap if page else None,
                milestones=page.milestones if page else [],
                quote=page.quote if page else "",
                chart_secondary=page.chart_secondary if page else None,
                evidence_ids=page.evidence_ids if page else [],
                visual_form=page.visual_form if page else None,
                confidence=page.confidence if page else "estimated",
                purpose=page.purpose if page else "",
                composition=page.composition if page else "",
            )
        )
    return normalized


def _complete_story(
    outline: OutlinePlan,
    proposed: list[StoryPage],
    design: DesignSpec,
    state: PPTAgentState,
) -> tuple[list[StoryPage], DesignSpec]:
    pages = enrich_story(_normalize_story(outline, proposed))
    locked = _finalize_design(design, state)
    bundle = EvidenceBundle(
        items=[EvidenceItem.model_validate(item) for item in state.get("evidence", [])]
    )
    pages = attach_evidence(pages, bundle)
    pages = choose_compositions(pages, locked, Path(state["project_dir"]))
    return pages, locked


def _infer_family(index: int, page: StoryPage | None, layout: LayoutType) -> SlideFamily:
    if page and page.family is not None:
        return page.family
    if page and page.chart_secondary is not None:
        return SlideFamily.DUAL_CHART
    if page and page.chart is not None:
        return SlideFamily.CHART_INTERPRETATION
    if page and page.waterfall:
        return SlideFamily.WATERFALL
    if page and page.heatmap is not None:
        return SlideFamily.HEATMAP
    if page and page.milestones:
        return SlideFamily.TIMELINE
    if page and page.quote:
        return SlideFamily.QUOTE
    if page and page.table is not None:
        return SlideFamily.TABLE_COMPARISON
    if page and page.scenarios:
        return SlideFamily.SCENARIO_MATRIX
    if page and page.allocation:
        return SlideFamily.ALLOCATION
    if page and page.kpis:
        return SlideFamily.COVER if index == 0 else SlideFamily.KPI_STRIP
    if index == 0 and layout == LayoutType.HERO:
        return SlideFamily.HERO if page and page.image_id else SlideFamily.COVER
    return SlideFamily(layout.value)


def _finalize_design(design: DesignSpec, state: PPTAgentState) -> DesignSpec:
    design = _lock_design(design, StyleOption.model_validate(state["selected_style"]))
    design = _apply_typography(design, state)
    return _complete_palette(design)


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


def _apply_typography(design: DesignSpec, state: PPTAgentState) -> DesignSpec:
    selected = state.get("selected_typography")
    if not selected:
        return _apply_reference_fonts(design, state)
    profile = TypographyProfile.model_validate(selected)
    return design.model_copy(
        update={
            "title_font": profile.east_asian_font,
            "body_font": profile.east_asian_font,
            "latin_font": profile.latin_font,
            "east_asian_font": profile.east_asian_font,
            "numeric_font": profile.numeric_font,
            "typography_profile": profile.id,
            "title_font_fallbacks": profile.fallbacks or design.title_font_fallbacks,
            "body_font_fallbacks": profile.fallbacks or design.body_font_fallbacks,
        }
    )


def _apply_reference_fonts(design: DesignSpec, state: PPTAgentState) -> DesignSpec:
    if state.get("reference_decision") != "use" or not state.get("reference_analysis"):
        return design
    analysis = ReferenceAnalysis.model_validate(state["reference_analysis"])
    updates: dict[str, str] = {}
    if analysis.title_font:
        updates["title_font"] = analysis.title_font
        updates["latin_font"] = analysis.title_font
    if analysis.body_font:
        updates["body_font"] = analysis.body_font
        updates["east_asian_font"] = analysis.body_font
    return design.model_copy(update=updates)


def _complete_palette(design: DesignSpec) -> DesignSpec:
    return design.model_copy(
        update={
            "muted": design.muted or _mix_hex(design.text, design.background, 0.42),
            "surface": design.surface or _mix_hex(design.background, design.primary, 0.1),
            "positive": design.positive or design.secondary,
            "negative": design.negative or design.primary,
            "warning": design.warning or design.accent,
        }
    )


def _mix_hex(start: str, end: str, amount: float) -> str:
    def channel(color: str, index: int) -> int:
        return int(color[1 + index * 2 : 3 + index * 2], 16)

    mixed = [
        round(channel(start, index) + (channel(end, index) - channel(start, index)) * amount)
        for index in range(3)
    ]
    return "#{:02X}{:02X}{:02X}".format(*mixed)


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
        if page.image_id and page.needs_artwork():
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
                    f"{design.illustration_style}. Use {design.primary}, "
                    f"{design.secondary}, and {design.background}. {directions}. "
                    "No text, watermarks, signatures, or identifiable facial details."
                ),
            )
        result.append(item)
    return result


async def _generate(runtime: Runtime[GraphContext], prompt: str, schema, state: PPTAgentState, node: str):
    started = time.perf_counter()
    result = await runtime.context.host.generate_structured(prompt, schema)
    record_metric(
        Path(state["project_dir"]),
        node,
        started,
        schema=schema.__name__,
        cache_hit=runtime.context.host.last_cache_hit,
        prompt_tokens=prompt_tokens(prompt),
    )
    return result
