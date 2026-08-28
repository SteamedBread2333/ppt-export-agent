from __future__ import annotations

import json
import time
from pathlib import Path

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import interrupt

from ppt_expert.assets import generate_assets
from ppt_expert.documents import write_contracts
from ppt_expert.enrichment import enrich_story
from ppt_expert.environment import survey_environment, write_environment
from ppt_expert.guards import inspect_guards, write_guard_report
from ppt_expert.models import (
    ArtifactBundle,
    DesignSpec,
    DesignTokens,
    EnvironmentReport,
    GuardReport,
    ImageRequest,
    IntentSlots,
    OutlinePlan,
    PageRole,
    PPTAgentState,
    RecipeId,
    StoryDesignBundle,
    StoryPage,
    StyleBrief,
    ValidationReport,
    VolumeReview,
)
from ppt_expert.planning import attach_evidence, extract_evidence
from ppt_expert.pptx import render_presentation
from ppt_expert.preview import cleanup_render_intermediates
from ppt_expert.prompts import intent_prompt, outline_prompt, repair_prompt, story_design_prompt
from ppt_expert.recipes import (
    FOUNDATIONS,
    build_style_brief,
    match_recipe_with_reason,
    recipe_choices,
    tokens_for,
)
from ppt_expert.repair import merge_repaired_pages
from ppt_expert.review import review_volume
from ppt_expert.runtime import GraphContext
from ppt_expert.telemetry import prompt_tokens, record_metric
from ppt_expert.validation import validate_presentation, write_validation_report


def build_graph(checkpointer):
    async def parse_intent(state: PPTAgentState, runtime: Runtime[GraphContext]) -> dict:
        intent = await _generate(
            runtime, intent_prompt(state["request"]), IntentSlots, state, "parse_intent"
        )
        outline = await _generate(
            runtime,
            outline_prompt(state["request"], intent.model_dump(mode="json")),
            OutlinePlan,
            state,
            "parse_outline",
        )
        evidence = extract_evidence(outline)
        project = Path(state["project_dir"])
        (project / "intent.json").write_text(intent.model_dump_json(indent=2), encoding="utf-8")
        (project / "foundations.json").write_text(
            json.dumps(FOUNDATIONS, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (project / "outline.json").write_text(
            json.dumps(outline.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "intent": intent.model_dump(mode="json"),
            "outline": outline.model_dump(mode="json"),
            "evidence": [item.model_dump(mode="json") for item in evidence.items],
            "repair_attempts": 0,
        }

    def route_intent(state: PPTAgentState) -> str:
        intent = IntentSlots.model_validate(state["intent"])
        return "confirm_intent" if intent.needs_confirmation() else "match_recipe"

    def confirm_intent(state: PPTAgentState) -> dict:
        intent = IntentSlots.model_validate(state["intent"])
        response = interrupt(
            {
                "type": "intent_confirmation",
                "message": "Topic, audience, or objective is incomplete.",
                "intent": intent.model_dump(mode="json"),
                "actions": ["continue", "edit"],
            }
        )
        payload = response if isinstance(response, dict) else {"action": str(response)}
        if str(payload.get("action", "continue")).lower() in {"continue", "ok", "use"}:
            return {}
        updated = intent.model_copy(update=payload.get("intent", {}))
        return {"intent": updated.model_dump(mode="json")}

    def match_recipe_node(state: PPTAgentState) -> dict:
        intent = IntentSlots.model_validate(state["intent"])
        recipe_id, reason = match_recipe_with_reason(state["request"], intent)
        mixing = (
            "No canonical recipe fully matched; mixing consulting structure with an open brief."
            if recipe_id == RecipeId.OPEN
            else ""
        )
        brief = build_style_brief(intent, recipe_id, mixing_note=mixing)
        tokens = tokens_for(recipe_id)
        Path(state["project_dir"], "style-brief.json").write_text(
            brief.model_dump_json(indent=2), encoding="utf-8"
        )
        return {
            "recipe_id": recipe_id.value,
            "match_reason": reason,
            "style_brief": brief.model_dump(mode="json"),
            "tokens": tokens.model_dump(mode="json"),
        }

    def confirm_recipe(state: PPTAgentState) -> dict:
        brief = StyleBrief.model_validate(state["style_brief"])
        tokens = DesignTokens.model_validate(state["tokens"])
        recommended = brief.recipe_id
        options = recipe_choices(recommended)
        response = interrupt(
            {
                "type": "recipe_confirmation",
                "message": "Choose a style recipe before typesetting.",
                "recommended": recommended.value,
                "reason": state.get("match_reason", ""),
                "recipe_id": recommended.value,
                "visual_proposition": brief.visual_proposition,
                "options": options,
                "brief": brief.model_dump(mode="json"),
                "palette": tokens.colors.model_dump(),
                "actions": [item["id"] for item in options] + ["use"],
            }
        )
        payload = response if isinstance(response, dict) else {"action": str(response)}
        action = str(payload.get("action") or payload.get("recipe_id") or "use").strip().lower()
        if action in {"use", "ok", "confirm", "a", "recommended", recommended.value}:
            return {}
        try:
            chosen = RecipeId(action)
        except ValueError as exc:
            raise ValueError("recipe action must be a recipe id or use") from exc
        intent = IntentSlots.model_validate(state["intent"])
        note = f"User chose {chosen.value} over recommended {recommended.value}"
        selected = build_style_brief(intent, chosen, mixing_note=note)
        Path(state["project_dir"], "style-brief.json").write_text(
            selected.model_dump_json(indent=2), encoding="utf-8"
        )
        return {
            "recipe_id": chosen.value,
            "style_brief": selected.model_dump(mode="json"),
            "tokens": tokens_for(chosen).model_dump(mode="json"),
        }

    def survey_env(state: PPTAgentState, runtime: Runtime[GraphContext]) -> dict:
        report = survey_environment(enable_visual=runtime.context.config.enable_libreoffice_preview)
        write_environment(report, state["project_dir"])
        (Path(state["project_dir"]) / "render").mkdir(parents=True, exist_ok=True)
        return {"environment": report.model_dump(mode="json")}

    async def plan_narrative(state: PPTAgentState, runtime: Runtime[GraphContext]) -> dict:
        bundle = await _generate(
            runtime,
            story_design_prompt(
                state["outline"],
                brief=state.get("style_brief"),
                evidence=list(state.get("evidence", [])),
            ),
            StoryDesignBundle,
            state,
            "plan_narrative",
        )
        outline = OutlinePlan.model_validate(state["outline"])
        pages = _complete_story(outline, bundle.pages, state)
        tokens = DesignTokens.model_validate(state["tokens"])
        design = tokens.to_design_spec()
        write_contracts(Path(state["project_dir"]), pages, design)
        (Path(state["project_dir"]) / "tokens.json").write_text(
            tokens.model_dump_json(indent=2), encoding="utf-8"
        )
        return {
            "story": [page.model_dump(mode="json") for page in pages],
            "design": design.model_dump(mode="json"),
        }

    async def build_pptx(state: PPTAgentState, runtime: Runtime[GraphContext]) -> dict:
        pages = [StoryPage.model_validate(item) for item in state["story"]]
        design = DesignSpec.model_validate(state["design"])
        tokens = DesignTokens.model_validate(state["tokens"])
        image_paths = dict(state.get("image_paths") or {})
        needed = [
            ImageRequest(
                image_id=page.image_id,
                page_numbers=[page.number],
                prompt=page.visual_direction or design.illustration_style,
            )
            for page in pages
            if page.image_id and page.image_id not in image_paths
        ]
        if needed:
            image_paths.update(
                await generate_assets(
                    runtime.context.host,
                    needed,
                    design,
                    Path(state["project_dir"]) / "assets",
                )
            )
        path = Path(state["project_dir"]) / f"{state['project_name']}.pptx"
        rendered = render_presentation(
            pages,
            design,
            image_paths,
            path,
            runtime.context.config,
            template_path=state.get("template_path"),
            tokens=tokens,
        )
        return {"pptx_path": rendered, "image_paths": image_paths}

    def guard_text(state: PPTAgentState) -> dict:
        report = inspect_guards(state["pptx_path"])
        write_guard_report(report, state["project_dir"])
        return {"guards": report.model_dump(mode="json")}

    def route_guards(state: PPTAgentState, runtime: Runtime[GraphContext]) -> str:
        report = GuardReport.model_validate(state["guards"])
        if (
            not report.clean
            and state.get("repair_attempts", 0) < runtime.context.config.max_repair_attempts
        ):
            return "repair_guards"
        return "render_overview"

    def repair_guards(state: PPTAgentState) -> dict:
        return {"repair_attempts": state.get("repair_attempts", 0) + 1}

    def render_overview(state: PPTAgentState) -> dict:
        env = EnvironmentReport.model_validate(state.get("environment") or {})
        pages = [StoryPage.model_validate(item) for item in state["story"]]
        tokens = DesignTokens.model_validate(state.get("tokens") or {})
        review = review_volume(
            state["pptx_path"],
            pages,
            state["project_dir"],
            visual_review=env.visual_review,
            layout_scheme=tokens.layout_scheme,
        )
        (Path(state["project_dir"]) / "review.json").write_text(
            review.model_dump_json(indent=2), encoding="utf-8"
        )
        return {"review": review.model_dump(mode="json"), "montage_path": review.montage_path}

    async def inspect_reps(state: PPTAgentState, runtime: Runtime[GraphContext]) -> dict:
        env = EnvironmentReport.model_validate(state.get("environment") or {})
        review = VolumeReview.model_validate(state.get("review") or {})
        project = Path(state["project_dir"])
        if env.visual_review == "full" and review.pdf_path and review.representative_pages:
            from ppt_expert.preview import render_representative_pages

            render_representative_pages(
                review.pdf_path,
                project / "render",
                review.representative_pages,
                dpi=130,
            )
        from ppt_expert.vision import critique_montage

        extra = await critique_montage(
            runtime.context.host,
            [path for path in [review.montage_path] if path],
        )
        if extra:
            review.issues.extend(extra)
            (project / "review.json").write_text(review.model_dump_json(indent=2), encoding="utf-8")
        return {"review": review.model_dump(mode="json")}

    def route_review(state: PPTAgentState, runtime: Runtime[GraphContext]) -> str:
        review = VolumeReview.model_validate(state.get("review") or {})
        blocking = [item for item in review.issues if item.severity == "error"]
        if blocking and state.get("repair_attempts", 0) < runtime.context.config.max_repair_attempts:
            return "repair_pages"
        return "xml_audit"

    def xml_audit(state: PPTAgentState) -> dict:
        report = validate_presentation(
            state["pptx_path"],
            OutlinePlan.model_validate(state["outline"]),
            [StoryPage.model_validate(item) for item in state["story"]],
            DesignSpec.model_validate(state["design"]),
            state.get("image_paths", {}),
        )
        write_validation_report(report, Path(state["project_dir"]))
        return {"validation": report.model_dump(mode="json")}

    def route_xml(state: PPTAgentState, runtime: Runtime[GraphContext]) -> str:
        report = ValidationReport.model_validate(state["validation"])
        if (
            not report.valid
            and state.get("repair_attempts", 0) < runtime.context.config.max_repair_attempts
        ):
            return "repair_pages"
        return "confirm_delivery"

    async def repair_pages(state: PPTAgentState, runtime: Runtime[GraphContext]) -> dict:
        report = ValidationReport.model_validate(state.get("validation") or {"valid": True, "issues": [], "pptx_path": ""})
        review_issues = []
        if state.get("review"):
            review_issues = VolumeReview.model_validate(state["review"]).issues
        failing = sorted(
            {issue.page for issue in report.issues if issue.page is not None}
            | {issue.page for issue in review_issues if issue.page is not None}
        )
        bundle = await _generate(
            runtime,
            repair_prompt(
                state["outline"],
                state["story"],
                state["design"],
                [issue.model_dump(mode="json") for issue in report.issues]
                + [issue.model_dump(mode="json") for issue in review_issues],
                pages=failing,
                notes=state.get("delivery_notes", ""),
            ),
            StoryDesignBundle,
            state,
            "repair_pages",
        )
        outline = OutlinePlan.model_validate(state["outline"])
        pages = _complete_story(outline, bundle.pages, state)
        if failing:
            current = [StoryPage.model_validate(item) for item in state["story"]]
            pages = merge_repaired_pages(current, pages, failing)
        tokens = DesignTokens.model_validate(state["tokens"])
        design = tokens.to_design_spec()
        write_contracts(Path(state["project_dir"]), pages, design)
        return {
            "story": [page.model_dump(mode="json") for page in pages],
            "design": design.model_dump(mode="json"),
            "repair_attempts": state.get("repair_attempts", 0) + 1,
        }

    def confirm_delivery(state: PPTAgentState) -> dict:
        validation = ValidationReport.model_validate(state["validation"])
        review = VolumeReview.model_validate(state.get("review") or {})
        choice = interrupt(
            {
                "type": "delivery_confirmation",
                "message": "Review the montage and package audit, then approve delivery.",
                "validation": validation.model_dump(mode="json"),
                "review": review.model_dump(mode="json"),
                "montage_path": state.get("montage_path"),
                "actions": ["approve", "revise"],
            }
        )
        payload = choice if isinstance(choice, dict) else {"action": str(choice)}
        action = str(payload.get("action", "approve")).strip().lower()
        if action in {"approve", "accept", "ok", "yes"}:
            return {"delivery_decision": "approve"}
        if action == "revise":
            return {
                "delivery_decision": "revise",
                "delivery_notes": str(payload.get("notes", "")).strip(),
            }
        raise ValueError("delivery action must be approve or revise")

    def route_delivery(state: PPTAgentState, runtime: Runtime[GraphContext]) -> str:
        if (
            state.get("delivery_decision") == "revise"
            and state.get("repair_attempts", 0) < runtime.context.config.max_repair_attempts
        ):
            return "repair_pages"
        return "cleanup"

    def cleanup(state: PPTAgentState, runtime: Runtime[GraphContext]) -> dict:
        project = Path(state["project_dir"]).resolve()
        cleanup_render_intermediates(project / "render")
        delivery = project / "DELIVERY.md"
        brief = StyleBrief.model_validate(state["style_brief"])
        env = EnvironmentReport.model_validate(state.get("environment") or {})
        lines = [
            "# DELIVERY",
            "",
            f"- Recipe: {brief.recipe_id.value}",
            f"- Proposition: {brief.visual_proposition}",
            f"- Tension: {brief.tension}",
            f"- Visual review: {env.visual_review}",
            f"- Montage: {state.get('montage_path') or 'degraded (no soffice/pdftoppm)'}",
            "",
            "## Engineering",
            "- Editable native pptx via python-pptx tokens, primitives, and page roles.",
            "- Short numeric tokens are single-line protected.",
            "",
            "## Provenance",
            "- Figures are illustrative unless a source_note says otherwise.",
            "",
        ]
        delivery.write_text("\n".join(lines), encoding="utf-8")
        artifacts = ArtifactBundle(
            project_dir=str(project),
            pptx_path=state["pptx_path"],
            story_path=str((project / "STORY.md").resolve()),
            design_path=str((project / "DESIGN.md").resolve()),
            report_path=str((project / "VALIDATION.md").resolve()),
            preview_paths=[path for path in [state.get("montage_path")] if path],
            contact_sheet_path=state.get("montage_path") or "",
            montage_path=state.get("montage_path") or "",
            delivery_path=str(delivery.resolve()),
        )
        return {"artifacts": artifacts.model_dump(mode="json")}

    builder = StateGraph(PPTAgentState, context_schema=GraphContext)
    builder.add_node("parse_intent", parse_intent)
    builder.add_node("confirm_intent", confirm_intent)
    builder.add_node("match_recipe", match_recipe_node)
    builder.add_node("confirm_recipe", confirm_recipe)
    builder.add_node("survey_env", survey_env)
    builder.add_node("plan_narrative", plan_narrative)
    builder.add_node("build_pptx", build_pptx)
    builder.add_node("guard_text", guard_text)
    builder.add_node("repair_guards", repair_guards)
    builder.add_node("render_overview", render_overview)
    builder.add_node("inspect_reps", inspect_reps)
    builder.add_node("xml_audit", xml_audit)
    builder.add_node("repair_pages", repair_pages)
    builder.add_node("confirm_delivery", confirm_delivery)
    builder.add_node("cleanup", cleanup)
    builder.add_edge(START, "parse_intent")
    builder.add_conditional_edges(
        "parse_intent",
        route_intent,
        {"confirm_intent": "confirm_intent", "match_recipe": "match_recipe"},
    )
    builder.add_edge("confirm_intent", "match_recipe")
    builder.add_edge("match_recipe", "confirm_recipe")
    builder.add_edge("confirm_recipe", "survey_env")
    builder.add_edge("survey_env", "plan_narrative")
    builder.add_edge("plan_narrative", "build_pptx")
    builder.add_edge("build_pptx", "guard_text")
    builder.add_conditional_edges(
        "guard_text",
        route_guards,
        {"repair_guards": "repair_guards", "render_overview": "render_overview"},
    )
    builder.add_edge("repair_guards", "build_pptx")
    builder.add_edge("render_overview", "inspect_reps")
    builder.add_conditional_edges(
        "inspect_reps",
        route_review,
        {"repair_pages": "repair_pages", "xml_audit": "xml_audit"},
    )
    builder.add_conditional_edges(
        "xml_audit",
        route_xml,
        {"repair_pages": "repair_pages", "confirm_delivery": "confirm_delivery"},
    )
    builder.add_conditional_edges(
        "confirm_delivery",
        route_delivery,
        {"repair_pages": "repair_pages", "cleanup": "cleanup"},
    )
    builder.add_edge("repair_pages", "build_pptx")
    builder.add_edge("cleanup", END)
    return builder.compile(checkpointer=checkpointer)


def _complete_story(outline: OutlinePlan, proposed: list[StoryPage], state: PPTAgentState) -> list[StoryPage]:
    from ppt_expert.models import EvidenceBundle, EvidenceItem

    pages = enrich_story(_normalize_story(outline, proposed))
    bundle = EvidenceBundle(
        items=[EvidenceItem.model_validate(item) for item in state.get("evidence", [])]
    )
    pages = attach_evidence(pages, bundle)
    return [_assign_role(index, page, len(pages)) for index, page in enumerate(pages)]


def _normalize_story(outline: OutlinePlan, proposed: list[StoryPage]) -> list[StoryPage]:
    from ppt_expert.models import LayoutType

    normalized: list[StoryPage] = []
    for index, source in enumerate(outline.pages):
        page = proposed[index] if index < len(proposed) else None
        proposed_content = page.content if page and page.content else []
        content = proposed_content + [item for item in source.core_content if item not in proposed_content]
        normalized.append(
            StoryPage(
                number=source.number,
                title=source.title,
                content=content,
                visual_direction=page.visual_direction if page else source.title,
                layout=page.layout if page else LayoutType.TEXT,
                image_id=page.image_id if page else None,
                section=source.section,
                family=page.family if page else None,
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
                role=page.role if page else None,
                speaker_notes=page.speaker_notes if page else (page.takeaway if page else source.title),
            )
        )
    return normalized


def _assign_role(index: int, page: StoryPage, total: int) -> StoryPage:
    role = page.role
    if role is None:
        if index == 0:
            role = PageRole.COVER
        elif index == total - 1:
            role = PageRole.CLOSE
        elif page.scenarios:
            role = PageRole.SCENARIO
        elif page.allocation:
            role = PageRole.STRUCTURE
        elif page.table or page.waterfall or page.heatmap:
            role = PageRole.EVIDENCE
        elif page.chart:
            role = PageRole.CONTEXT
        elif index == 1:
            role = PageRole.OVERVIEW
        else:
            role = PageRole.EXPANSION
    notes = page.speaker_notes or page.takeaway or page.title
    return page.model_copy(update={"role": role, "speaker_notes": notes})


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
