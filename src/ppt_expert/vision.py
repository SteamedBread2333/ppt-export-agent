from __future__ import annotations

import base64
import inspect
from collections.abc import Sequence
from pathlib import Path
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


def require_vision_host(host: HostRuntime) -> None:
    if host.critique_images is not None:
        return
    if host.model is not None and hasattr(host.model, "with_structured_output"):
        return
    raise RuntimeError(
        "Montage review requires HostRuntime.critique_images or a vision-capable model"
    )


async def critique_montage(host: HostRuntime, image_paths: Sequence[str]) -> list[QualityIssue]:
    require_vision_host(host)
    if not image_paths:
        raise RuntimeError("Montage critique requires render/montage.png")
    missing = [path for path in image_paths if not Path(path).is_file()]
    if missing:
        raise RuntimeError(f"Montage PNG missing: {', '.join(missing)}")
    result = await _invoke_critique(host, image_paths)
    return list(_coerce_critique(result).issues)


async def apply_vision_review(
    report: QualityReport,
    host: HostRuntime,
    image_paths: Sequence[str],
) -> QualityReport:
    require_vision_host(host)
    if not image_paths:
        raise RuntimeError("Vision review requires a contact-sheet PNG")
    result = await _invoke_critique(host, image_paths)
    return _merge_vision(report, _coerce_critique(result))


async def _invoke_critique(host: HostRuntime, image_paths: Sequence[str]) -> Any:
    if host.critique_images is not None:
        result = host.critique_images(VISION_PROMPT, list(image_paths), VisionCritique)
        return await result if inspect.isawaitable(result) else result
    return await _critique_with_model(host, image_paths)


async def _critique_with_model(host: HostRuntime, image_paths: Sequence[str]) -> Any:
    model = host.model
    from langchain_core.messages import HumanMessage

    parts: list[dict[str, Any]] = [{"type": "text", "text": VISION_PROMPT}]
    for path in image_paths:
        raw = Path(path).read_bytes()
        suffix = Path(path).suffix.lower()
        mime = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
        encoded = base64.b64encode(raw).decode("ascii")
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{encoded}"},
            }
        )
    runnable = model.with_structured_output(VisionCritique)
    message = HumanMessage(content=parts)
    result = (
        runnable.ainvoke([message]) if hasattr(runnable, "ainvoke") else runnable.invoke([message])
    )
    return await result if inspect.isawaitable(result) else result


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
    warnings = [item for item in report.warnings if item.code != "vision_review_unavailable"]
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
