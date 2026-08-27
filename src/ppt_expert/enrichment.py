from __future__ import annotations

import re

from ppt_expert.models import (
    ChartSeries,
    ChartSpec,
    ChartType,
    KPIItem,
    LayoutType,
    SlideFamily,
    StoryPage,
)

_NUMBER = re.compile(r"(?<![\w./])([-+]?\d+(?:\.\d+)?)(%|亿|万|bp|ppt)?")
_ARTWORK_FAMILIES = {
    SlideFamily.HERO,
    SlideFamily.LEFT_IMAGE,
    SlideFamily.RIGHT_IMAGE,
    SlideFamily.TOP_IMAGE,
}
_ANALYTICAL_FAMILIES = {
    SlideFamily.CHART_INTERPRETATION,
    SlideFamily.TABLE_COMPARISON,
    SlideFamily.SCENARIO_MATRIX,
    SlideFamily.ALLOCATION,
    SlideFamily.KPI_STRIP,
    SlideFamily.EXECUTIVE_SUMMARY,
    SlideFamily.DUAL_CHART,
    SlideFamily.WATERFALL,
    SlideFamily.HEATMAP,
    SlideFamily.TIMELINE,
}


def enrich_story(pages: list[StoryPage]) -> list[StoryPage]:
    total = len(pages)
    return [_enrich_page(index, page, total) for index, page in enumerate(pages)]


def _enrich_page(index: int, page: StoryPage, total: int) -> StoryPage:
    updates: dict = {}
    family = page.resolved_family()
    metrics = _metrics(page)
    if family in _ANALYTICAL_FAMILIES and page.image_id:
        updates["image_id"] = None
    if index == 0 and family in {SlideFamily.COVER, SlideFamily.HERO} and not page.kpis:
        updates["kpis"] = _kpis_from_metrics(metrics) or _structural_kpis(page, total)
        updates["family"] = SlideFamily.COVER
        updates["eyebrow"] = page.eyebrow or page.section or "BRIEFING"
        updates["image_id"] = None
    elif (
        not page.chart
        and not page.table
        and not page.allocation
        and not page.scenarios
        and family not in ({SlideFamily.COVER, SlideFamily.CONCLUSION} | _ARTWORK_FAMILIES)
        and len(metrics) >= 3
    ):
        updates["chart"] = _chart_from_metrics(metrics)
        updates["family"] = SlideFamily.CHART_INTERPRETATION
        updates["layout"] = LayoutType.TEXT
        updates["image_id"] = None
    if not page.takeaway and page.content:
        updates["takeaway"] = page.content[0]
    if not page.eyebrow:
        updates["eyebrow"] = page.section or _default_eyebrow(index, total, family)
    if family in _ANALYTICAL_FAMILIES and not page.source_note:
        updates["source_note"] = "From outline · confidence labeled on the slide"
    return page.model_copy(update=updates) if updates else page


def _default_eyebrow(index: int, total: int, family: SlideFamily) -> str:
    if index == 0:
        return "BRIEFING"
    if index == total - 1 or family == SlideFamily.CONCLUSION:
        return "NEXT STEP"
    return family.value.replace("_", " ").upper()


def _metrics(page: StoryPage) -> list[tuple[str, float, str]]:
    found: list[tuple[str, float, str]] = []
    for item in page.content:
        for match in _NUMBER.finditer(item):
            raw, suffix = match.group(1), match.group(2) or ""
            found.append((f"{raw}{suffix}", float(raw), item))
    return found


def _kpis_from_metrics(metrics: list[tuple[str, float, str]]) -> list[KPIItem]:
    kpis: list[KPIItem] = []
    seen: set[str] = set()
    for display, _value, source in metrics:
        if display in seen:
            continue
        seen.add(display)
        kpis.append(KPIItem(value=display, label=_clip_label(source), note="From outline"))
        if len(kpis) == 3:
            break
    return kpis


def _structural_kpis(page: StoryPage, total: int) -> list[KPIItem]:
    return [
        KPIItem(value=str(total), label="Slides", note="Outline fidelity"),
        KPIItem(value=str(len(page.content)), label="Assertions", note="Cover claims"),
        KPIItem(value="1", label="Takeaway", note="One governing message"),
    ]


def _chart_from_metrics(metrics: list[tuple[str, float, str]]) -> ChartSpec:
    categories = [f"{index + 1}" for index, _item in enumerate(metrics[:6])]
    values = [item[1] for item in metrics[:6]]
    return ChartSpec(
        chart_type=ChartType.COLUMN,
        categories=categories,
        series=[ChartSeries(name="Evidence", values=values)],
    )


def _clip_label(value: str) -> str:
    cleaned = _NUMBER.sub("", value).strip(" ·:-")
    return cleaned[:22] or "Metric"
