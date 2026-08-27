from __future__ import annotations

import re

from ppt_expert.models import (
    DeckArchetype,
    DeckBrief,
    EvidenceBundle,
    EvidenceItem,
    OutlinePlan,
    SlideFamily,
    StoryPage,
    VisualForm,
)

_NUMBER = re.compile(r"(?<![\w./])([-+]?\d+(?:\.\d+)?)(%|亿|万|bp|ppt)?")
_STRATEGY = ("strategy", "outlook", "allocation", "scenario", "策略", "展望", "配置")
_PRODUCT = ("product", "launch", "roadmap", "产品", "发布")
_NARRATIVE = ("story", "tribute", "纪念", "故事")


def build_brief(outline: OutlinePlan, request: str) -> DeckBrief:
    blob = f"{outline.title} {outline.purpose} {request}".casefold()
    return DeckBrief(
        objective=outline.purpose or outline.title,
        audience=outline.audience,
        decision_context=request.strip().splitlines()[0][:240] if request.strip() else outline.title,
        duration_minutes=max(12, len(outline.pages) * 2),
        language=_language(outline.title + outline.purpose),
        slide_count=len(outline.pages),
        primary_archetype=_archetype(blob),
        density="high" if len(outline.pages) >= 8 else "medium",
    )


def extract_evidence(outline: OutlinePlan) -> EvidenceBundle:
    items: list[EvidenceItem] = []
    for page in outline.pages:
        for index, statement in enumerate(page.core_content, 1):
            match = _NUMBER.search(statement)
            kind = "metric" if match else "claim"
            items.append(
                EvidenceItem(
                    id=f"p{page.number}.{index}",
                    kind=kind,  # type: ignore[arg-type]
                    statement=statement,
                    value=float(match.group(1)) if match else None,
                    unit=match.group(2) or "" if match else "",
                    source=page.title,
                    confidence="confirmed" if match else "estimated",
                )
            )
    return EvidenceBundle(items=items)


def attach_evidence(pages: list[StoryPage], bundle: EvidenceBundle) -> list[StoryPage]:
    by_statement = {item.statement: item for item in bundle.items}
    attached: list[StoryPage] = []
    for page in pages:
        ids = [by_statement[item].id for item in page.content if item in by_statement]
        form = page.visual_form or _visual_form(page)
        attached.append(
            page.model_copy(update={"evidence_ids": ids or page.evidence_ids, "visual_form": form})
        )
    return attached


def _visual_form(page: StoryPage) -> VisualForm:
    family = page.resolved_family()
    mapping = {
        SlideFamily.KPI_STRIP: VisualForm.KPI,
        SlideFamily.EXECUTIVE_SUMMARY: VisualForm.KPI,
        SlideFamily.COVER: VisualForm.KPI,
        SlideFamily.CHART_INTERPRETATION: VisualForm.CHART,
        SlideFamily.DUAL_CHART: VisualForm.CHART,
        SlideFamily.TABLE_COMPARISON: VisualForm.TABLE,
        SlideFamily.SCENARIO_MATRIX: VisualForm.MATRIX,
        SlideFamily.ALLOCATION: VisualForm.ALLOCATION,
        SlideFamily.WATERFALL: VisualForm.WATERFALL,
        SlideFamily.HEATMAP: VisualForm.HEATMAP,
        SlideFamily.TIMELINE: VisualForm.TIMELINE,
        SlideFamily.PILLARS: VisualForm.DIAGRAM,
        SlideFamily.QUOTE: VisualForm.QUOTE,
    }
    if page.chart or page.chart_secondary:
        return VisualForm.CHART
    if page.table:
        return VisualForm.TABLE
    if page.waterfall:
        return VisualForm.WATERFALL
    if page.heatmap:
        return VisualForm.HEATMAP
    return mapping.get(family, VisualForm.NARRATIVE)


def _archetype(blob: str) -> DeckArchetype:
    if any(token in blob for token in _STRATEGY):
        return DeckArchetype.STRATEGY
    if any(token in blob for token in _PRODUCT):
        return DeckArchetype.PRODUCT
    if any(token in blob for token in _NARRATIVE):
        return DeckArchetype.NARRATIVE
    return DeckArchetype.RESEARCH


def _language(text: str) -> str:
    return "zh" if any("\u4e00" <= character <= "\u9fff" for character in text) else "en"
