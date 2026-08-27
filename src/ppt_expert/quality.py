from __future__ import annotations

from itertools import pairwise
from pathlib import Path

from ppt_expert.models import (
    DesignSpec,
    QualityIssue,
    QualityReport,
    SlideFamily,
    SlideQuality,
    StoryPage,
)

_ANALYTICAL = {
    SlideFamily.CHART_INTERPRETATION,
    SlideFamily.DUAL_CHART,
    SlideFamily.TABLE_COMPARISON,
    SlideFamily.SCENARIO_MATRIX,
    SlideFamily.ALLOCATION,
    SlideFamily.WATERFALL,
    SlideFamily.HEATMAP,
    SlideFamily.TIMELINE,
    SlideFamily.KPI_STRIP,
    SlideFamily.EXECUTIVE_SUMMARY,
}
_IMAGE_LED = {
    SlideFamily.HERO,
    SlideFamily.LEFT_IMAGE,
    SlideFamily.RIGHT_IMAGE,
    SlideFamily.TOP_IMAGE,
}


def score_deck(
    pages: list[StoryPage],
    design: DesignSpec,
    contact_sheet_path: str = "",
    vision_available: bool = False,
) -> QualityReport:
    issues: list[QualityIssue] = []
    dimensions = {
        "narrative": _narrative(pages, issues),
        "evidence": _evidence(pages, issues),
        "hierarchy": _hierarchy(pages, issues),
        "composition": _composition(pages, issues),
        "typography": _typography(design, issues),
        "data_visualization": _data_viz(pages, issues),
        "consistency": _consistency(pages, issues),
        "editability": _editability(pages, issues),
        "accessibility": _accessibility(design, issues),
    }
    _red_team(pages, issues)
    critic_scores = {
        "executive_editor": dimensions["narrative"],
        "information_designer": min(dimensions["evidence"], dimensions["data_visualization"]),
        "art_director": min(
            dimensions["hierarchy"], dimensions["composition"], dimensions["typography"]
        ),
        "production_engineer": min(
            dimensions["editability"], dimensions["accessibility"], dimensions["consistency"]
        ),
    }
    if max(critic_scores.values()) - min(critic_scores.values()) > 15:
        issues.append(
            QualityIssue(
                code="critic_disagreement",
                message="Independent critics disagree by more than 15 points",
                cause="One review lens is scoring a different failure mode",
                repair_scope="narrative",
                acceptance="Critic spread is within 15 points after adjudication",
            )
        )
    if not vision_available:
        issues.append(
            QualityIssue(
                code="vision_review_unavailable",
                message="Host has no image critique tool; visual review is structural only",
                cause="Rendered PNG review was skipped",
                repair_scope="slide",
                acceptance="Host supplies critique_images for rendered-slide review",
            )
        )
    blocking = [item for item in issues if item.severity == "error"]
    warnings = [item for item in issues if item.severity != "error"]
    mean = round(sum(dimensions.values()) / len(dimensions))
    conservative = min(critic_scores.values())
    score = min(mean, max(conservative, mean - 6))
    if blocking:
        score = min(score, 78)
    delivery = (
        "final"
        if score >= 90
        and not blocking
        and all(value >= 82 for value in dimensions.values())
        else "reviewable_draft"
    )
    return QualityReport(
        score=score,
        blocking_issues=blocking,
        warnings=warnings,
        dimensions=dimensions,
        critic_scores=critic_scores,
        slide_scores=[_slide_quality(page, issues) for page in pages],
        contact_sheet_path=contact_sheet_path,
        delivery=delivery,
        vision_review="completed" if vision_available else "structural_only",
    )


def write_quality_report(report: QualityReport, project_dir: Path) -> str:
    json_path = project_dir / "quality.json"
    md_path = project_dir / "QUALITY.md"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    lines = [
        "# QUALITY",
        "",
        f"- Score: {report.score}",
        f"- Delivery: {report.delivery}",
        f"- Vision: {report.vision_review}",
        f"- Contact sheet: {report.contact_sheet_path or 'None'}",
        "",
        "## Dimensions",
    ]
    for name, value in report.dimensions.items():
        lines.append(f"- {name}: {value}")
    lines.extend(["", "## Critics"])
    for name, value in report.critic_scores.items():
        lines.append(f"- {name}: {value}")
    lines.extend(["", "## Blocking issues"])
    lines.extend(_issue_lines(report.blocking_issues) or ["- None"])
    lines.extend(["", "## Warnings"])
    lines.extend(_issue_lines(report.warnings) or ["- None"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(md_path.resolve())


def _issue_lines(issues: list[QualityIssue]) -> list[str]:
    lines = []
    for issue in issues:
        page = f"Slide {issue.page}: " if issue.page else ""
        lines.append(f"- [{issue.severity}] {page}{issue.message} (`{issue.code}`)")
    return lines


def _narrative(pages: list[StoryPage], issues: list[QualityIssue]) -> int:
    score = 92
    if not pages:
        return 40
    missing = [page.number for page in pages if not page.takeaway and len(page.content) > 3]
    if missing:
        issues.append(
            QualityIssue(
                code="weak_takeaway",
                message="Long slides are missing an explicit takeaway",
                page=missing[0],
                cause="The governing message is buried in bullets",
                repair_scope="slide",
                acceptance="Every dense slide has a one-line takeaway",
            )
        )
        score -= 8
    if pages[0].resolved_family() not in {SlideFamily.COVER, SlideFamily.HERO}:
        issues.append(
            QualityIssue(
                code="weak_opening",
                message="The opening slide is not a cover or hero",
                page=1,
                severity="error",
                cause="The deck does not establish a briefing frame",
                repair_scope="narrative",
                acceptance="Slide 1 is a cover with a governing assertion",
            )
        )
        score -= 20
    if pages[-1].resolved_family() not in {SlideFamily.CONCLUSION, SlideFamily.HERO, SlideFamily.TEXT}:
        score -= 4
    return _clamp(score)


def _evidence(pages: list[StoryPage], issues: list[QualityIssue]) -> int:
    score = 90
    for page in pages:
        family = page.resolved_family()
        if family in _ANALYTICAL and not _has_visual_evidence(page):
            issues.append(
                QualityIssue(
                    code="missing_visual_evidence",
                    message="Analytical slide has no chart, table, KPI, or matrix",
                    page=page.number,
                    severity="error",
                    cause="Quantitative claims are still prose-only",
                    repair_scope="slide",
                    acceptance="The slide uses a native analytical visual",
                )
            )
            score -= 18
        if family in _ANALYTICAL and page.image_id:
            issues.append(
                QualityIssue(
                    code="decorative_evidence",
                    message="Analytical slide depends on generated artwork",
                    page=page.number,
                    severity="error",
                    cause="ImageGen is standing in for evidence",
                    repair_scope="slide",
                    acceptance="image_id is empty and a native visual carries the claim",
                )
            )
            score -= 20
    return _clamp(score)


def _hierarchy(pages: list[StoryPage], issues: list[QualityIssue]) -> int:
    score = 92
    unlabeled = sum(1 for page in pages if not page.eyebrow and not page.section)
    if unlabeled > len(pages) / 2:
        issues.append(
            QualityIssue(
                code="weak_hierarchy",
                message="Most slides lack an eyebrow or section label",
                cause="Hierarchy is title-plus-bullets only",
                repair_scope="component",
                acceptance="Eyebrows appear on a majority of slides",
            )
        )
        score -= 10
    return _clamp(score)


def _composition(pages: list[StoryPage], issues: list[QualityIssue]) -> int:
    families = [page.resolved_family() for page in pages]
    score = 90
    if len(set(families)) == 1 and len(pages) > 2:
        issues.append(
            QualityIssue(
                code="layout_cycling",
                message="Every slide uses the same family",
                cause="Composition is not chosen from slide semantics",
                repair_scope="rhythm",
                acceptance="Adjacent slides vary in family",
            )
        )
        score -= 16
    streak = 1
    for previous, current in pairwise(families):
        streak = streak + 1 if previous == current else 1
        if streak >= 3:
            issues.append(
                QualityIssue(
                    code="repetitive_rhythm",
                    message="Three or more consecutive slides share a family",
                    cause="Visual pacing is flat",
                    repair_scope="rhythm",
                    acceptance="No family repeats more than twice in a row",
                )
            )
            score -= 8
            break
    image_share = sum(1 for family in families if family in _IMAGE_LED) / max(len(families), 1)
    if image_share > 0.5:
        issues.append(
            QualityIssue(
                code="illustration_led",
                message="More than half of the deck is image-led",
                cause="Artwork is carrying slides that should be analytical",
                repair_scope="narrative",
                acceptance="Image-led slides stay in the minority",
            )
        )
        score -= 14
    return _clamp(score)


def _typography(design: DesignSpec, issues: list[QualityIssue]) -> int:
    score = 88
    if design.latin_font and design.east_asian_font:
        score += 6
    else:
        issues.append(
            QualityIssue(
                code="missing_script_fonts",
                message="Latin and East Asian families are not both recorded",
                cause="Typography was not approved as a profile",
                repair_scope="token",
                acceptance="DESIGN records latin_font and east_asian_font",
            )
        )
        score -= 12
    return _clamp(score)


def _data_viz(pages: list[StoryPage], issues: list[QualityIssue]) -> int:
    visual = sum(1 for page in pages if _has_visual_evidence(page))
    score = 70 + min(30, visual * 8)
    if visual == 0 and len(pages) > 2:
        issues.append(
            QualityIssue(
                code="no_native_visuals",
                message="The deck has no KPI, chart, table, or matrix",
                severity="error",
                cause="Every claim is still a bullet list",
                repair_scope="narrative",
                acceptance="At least one native analytical visual exists",
            )
        )
        score = 55
    return _clamp(score)


def _consistency(pages: list[StoryPage], issues: list[QualityIssue]) -> int:
    score = 92
    covers = [page for page in pages if page.resolved_family() == SlideFamily.COVER]
    if len(covers) > 1:
        issues.append(
            QualityIssue(
                code="repeated_cover",
                message="More than one cover treatment appears",
                cause="Opening language is reused as decoration",
                repair_scope="rhythm",
                acceptance="Only the first slide uses the cover family",
            )
        )
        score -= 8
    return _clamp(score)


def _editability(pages: list[StoryPage], issues: list[QualityIssue]) -> int:
    score = 94
    flattened = [
        page.number
        for page in pages
        if page.resolved_family() in _ANALYTICAL and page.image_id
    ]
    if flattened:
        issues.append(
            QualityIssue(
                code="flattened_evidence",
                message="Evidence is trapped in a raster instead of native shapes",
                page=flattened[0],
                cause="The renderer cannot keep the claim editable",
                repair_scope="component",
                acceptance="Analytical slides use native charts or tables",
            )
        )
        score -= 16
    return _clamp(score)


def _accessibility(design: DesignSpec, issues: list[QualityIssue]) -> int:
    contrast = _relative_luminance(design.text) - _relative_luminance(design.background)
    score = 90 if abs(contrast) > 0.35 else 72
    if abs(contrast) <= 0.35:
        issues.append(
            QualityIssue(
                code="weak_contrast",
                message="Body text may not contrast enough with the canvas",
                cause="Palette contrast is below the accessibility heuristic",
                repair_scope="token",
                acceptance="Text and background luminance differ by more than 0.35",
            )
        )
    return _clamp(score)


def _has_visual_evidence(page: StoryPage) -> bool:
    return bool(
        page.kpis
        or page.chart
        or page.chart_secondary
        or page.table
        or page.allocation
        or page.scenarios
        or page.waterfall
        or page.heatmap
        or page.milestones
        or page.quote
        or page.resolved_family() in {SlideFamily.PILLARS, SlideFamily.DATA_CARDS}
    )


def _red_team(pages: list[StoryPage], issues: list[QualityIssue]) -> None:
    for previous, current in pairwise(pages):
        if previous.resolved_family() == current.resolved_family() and previous.resolved_family() in _ANALYTICAL:
            issues.append(
                QualityIssue(
                    code="repeated_geometry",
                    message="Adjacent analytical slides share the same family",
                    page=current.number,
                    cause="Rhythm does not change when the argument changes",
                    repair_scope="rhythm",
                    acceptance="Adjacent analytical slides use different families",
                )
            )
            break
    for page in pages:
        family = page.resolved_family()
        if family in _ANALYTICAL and not page.source_note:
            issues.append(
                QualityIssue(
                    code="missing_source",
                    message="Analytical slide is missing a source or confidence note",
                    page=page.number,
                    cause="Evidence is not traceable",
                    repair_scope="component",
                    acceptance="Source or confidence is visible on analytical slides",
                )
            )
        if family in _IMAGE_LED and family in _ANALYTICAL:
            issues.append(
                QualityIssue(
                    code="decorative_primary_evidence",
                    message="Artwork is the primary evidence on an analytical slide",
                    page=page.number,
                    severity="error",
                    cause="A raster is standing in for a chart or table",
                    repair_scope="slide",
                    acceptance="Analytical slides use native visuals, not full-bleed images",
                )
            )


def _slide_quality(page: StoryPage, issues: list[QualityIssue]) -> SlideQuality:
    local = [issue.message for issue in issues if issue.page == page.number]
    score = 92 - 8 * len(local)
    return SlideQuality(
        page=page.number,
        score=_clamp(score),
        family=page.resolved_family().value,
        issues=local,
    )


def _relative_luminance(color: str) -> float:
    value = color.lstrip("#")
    red, green, blue = (int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _clamp(score: int) -> int:
    return max(40, min(100, score))
