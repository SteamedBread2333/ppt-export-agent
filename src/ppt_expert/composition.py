from __future__ import annotations

import json
from pathlib import Path

from ppt_expert.models import ChartType, DesignSpec, SlideFamily, StoryPage
from ppt_expert.quality import score_deck

_KEY_FAMILIES = {
    SlideFamily.COVER,
    SlideFamily.CHART_INTERPRETATION,
    SlideFamily.DUAL_CHART,
    SlideFamily.TABLE_COMPARISON,
    SlideFamily.EXECUTIVE_SUMMARY,
}


def choose_compositions(
    pages: list[StoryPage],
    design: DesignSpec,
    output_dir: str | Path | None = None,
) -> list[StoryPage]:
    selected = list(pages)
    decisions: list[dict[str, object]] = []
    for index, page in enumerate(pages):
        if page.resolved_family() not in _KEY_FAMILIES:
            continue
        for variant, label in _variants(page):
            trial = selected.copy()
            trial[index] = variant
            current_score = score_deck(selected, design).score
            proposed_score = score_deck(trial, design).score
            winner = "variant" if proposed_score > current_score else "incumbent"
            decisions.append(
                {
                    "page": page.number,
                    "family": page.resolved_family().value,
                    "candidate": label,
                    "incumbent_score": current_score,
                    "variant_score": proposed_score,
                    "winner": winner,
                }
            )
            if proposed_score > current_score:
                selected = trial
    if output_dir is not None:
        path = Path(output_dir) / "composition.json"
        path.write_text(
            json.dumps({"decisions": decisions}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return selected


def _variants(page: StoryPage) -> list[tuple[StoryPage, str]]:
    variants: list[tuple[StoryPage, str]] = []
    if page.chart is not None and page.chart.chart_type == ChartType.LINE:
        chart = page.chart.model_copy(update={"chart_type": ChartType.COLUMN})
        variants.append(
            (page.model_copy(update={"chart": chart, "composition": "column_emphasis"}), "column")
        )
    if page.resolved_family() == SlideFamily.COVER and page.kpis and not page.subtitle:
        variants.append(
            (
                page.model_copy(
                    update={"subtitle": page.takeaway or page.content[0], "composition": "thesis"}
                ),
                "thesis_subtitle",
            )
        )
    if page.chart is not None and page.chart_secondary is None and len(page.chart.series) > 1:
        primary = page.chart.model_copy(update={"series": page.chart.series[:1]})
        secondary = page.chart.model_copy(update={"series": page.chart.series[1:2]})
        variants.append(
            (
                page.model_copy(
                    update={
                        "chart": primary,
                        "chart_secondary": secondary,
                        "family": SlideFamily.DUAL_CHART,
                        "composition": "dual",
                    }
                ),
                "dual_split",
            )
        )
    return variants
