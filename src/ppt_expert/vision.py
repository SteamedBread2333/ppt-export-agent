from __future__ import annotations

import inspect
from collections.abc import Sequence
from typing import Any

from ppt_expert.models import QualityIssue, QualityReport, VisionCritique
from ppt_expert.runtime import HostRuntime

VISION_PROMPT = """You are an independent visual critic. Review the rendered contact
sheet (and any slide images). Score 0-100. List concrete issues with slide number,
severity, observed problem, probable cause, repair scope, and a measurable
acceptance condition. Do not give vague advice such as "make it more professional".
Evaluate five-second comprehension, evidence prominence, alignment, whitespace,
contrast, density, chart legibility, and template repetition.

Reject these as ugly, not as style:
- stacked gray cards with accent bars (card soup)
- title hairline colliding with the first module
- default Excel chart walls and rotated date clutter
- IMPLICATION / KPI chrome boxes that repeat on every slide
- adjacent pages that share the same tiled silhouette
"""


async def critique_montage(host: HostRuntime, image_paths: Sequence[str]) -> list[QualityIssue]:
    if host.critique_images is None or not image_paths:
        return []
    try:
        result = host.critique_images(VISION_PROMPT, list(image_paths), VisionCritique)
        result = await result if inspect.isawaitable(result) else result
        # Montage taste cannot be repaired by rewriting copy; surface it, do not loop.
        return [
            issue.model_copy(update={"severity": "warning"})
            for issue in _coerce_critique(result).issues
        ]
    except Exception:  # noqa: BLE001
        return []


async def apply_vision_review(
    report: QualityReport,
    host: HostRuntime,
    image_paths: Sequence[str],
) -> QualityReport:
    if host.critique_images is None or not image_paths:
        return report
    try:
        result = host.critique_images(VISION_PROMPT, list(image_paths), VisionCritique)
        result = await result if inspect.isawaitable(result) else result
        critique = _coerce_critique(result)
    except Exception:  # noqa: BLE001 - host vision is optional and must not abort delivery
        return report.model_copy(
            update={
                "warnings": [
                    *report.warnings,
                    QualityIssue(
                        code="vision_review_failed",
                        message="Host image critique raised an error; structural scores stand",
                        cause="critique_images did not return a usable VisionCritique",
                        repair_scope="slide",
                        acceptance="Host critique_images returns a scored visual review",
                    ),
                ]
            }
        )
    return _merge_vision(report, critique)


def _coerce_critique(result: Any) -> VisionCritique:
    if isinstance(result, VisionCritique):
        return result
    if isinstance(result, QualityReport):
        issues = [*result.blocking_issues, *result.warnings]
        return VisionCritique(score=result.score, issues=issues, notes=result.vision_review)
    if isinstance(result, dict):
        return VisionCritique.model_validate(result)
    raise TypeError("critique_images must return VisionCritique, QualityReport, or dict")


def _merge_vision(report: QualityReport, critique: VisionCritique) -> QualityReport:
    warnings = [
        item
        for item in report.warnings
        if item.code != "vision_review_unavailable"
    ]
    blocking = list(report.blocking_issues)
    for issue in critique.issues:
        if issue.severity == "error":
            blocking.append(issue)
        else:
            warnings.append(issue)
    score = max(40, min(100, min(report.score, critique.score)))
    dimensions = dict(report.dimensions)
    dimensions["rendered_visual"] = critique.score
    delivery = (
        "final"
        if score >= 90
        and not blocking
        and all(value >= 82 for value in dimensions.values())
        else "reviewable_draft"
    )
    return report.model_copy(
        update={
            "score": min(score, 78) if blocking else score,
            "blocking_issues": blocking,
            "warnings": warnings,
            "dimensions": dimensions,
            "delivery": delivery,
            "vision_review": critique.notes or "completed",
        }
    )
