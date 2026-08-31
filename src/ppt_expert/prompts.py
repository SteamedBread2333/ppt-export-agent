from __future__ import annotations

import json
from typing import Any

from ppt_expert.recipes import FOUNDATIONS

STORY_RULES = """You are a presentation visual director, not a slide filler.
1. Preserve the user's outline. Do not add, remove, or alter slide counts, titles,
   or core facts; only refine the writing into assertions.
2. Choose a narrative page role: cover, overview, context, evidence, structure,
   expansion, scenario, close. Adjacent pages must not share a silhouette.
3. Evidence is native charts, tables, KPI tiles, scenario matrices, and allocation
   graphics. Assign image_id only when the approved recipe's image behavior allows.
4. Use only role-named design tokens. Never invent palette hex values.
5. Every slide needs a takeaway (implication) and speaker notes describing intent.
6. Put numbers into kpis, chart, table, or allocation fields.
"""


def parse_prompt(request: str) -> str:
    return f"""Fill intent slots and a slide-by-slide outline from the user request.
Intent: topic, audience, objective, slide_count, density, editable, delivery_format.
Leave audience or objective empty when the request does not state them.
Outline: contiguous page numbers, assertion titles, core facts preserved from the request.
If the user gives no outline, create slide_count slides (default 8).

User input:
{request}
"""


def story_design_prompt(
    outline: dict[str, Any],
    brief: dict[str, Any] | None = None,
    evidence: list[dict[str, Any]] | None = None,
) -> str:
    foundations = "\n".join(f"- {item}" for item in FOUNDATIONS)
    return f"""{STORY_RULES}
Production foundations:
{foundations}

Produce STORY pages from the outline and approved style brief.
- Page count, numbering, titles, and core facts map one-to-one to the outline.
- role must be one of: cover, overview, context, evidence, structure, expansion,
  scenario, close. First page is cover, last page is close.
- Cover needs eyebrow, subtitle, 2–4 kpis. Analytical pages need chart, table,
  scenarios, or allocation when the evidence is quantitative.
- Bind evidence_ids. chart uses chart_type line|column|bar|area and numeric series.
- layout may be text. family may match the role. image_id stays null on consulting
  evidence pages.
- Do not invent colors, fonts, or a design spec; tokens are already approved.

Style brief:
{_dumps(brief or {})}

Evidence:
{_dumps(evidence or [])}

Outline:
{_dumps(outline)}
"""


def repair_prompt(
    outline: dict[str, Any],
    story: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    pages: list[int] | None = None,
    notes: str = "",
) -> str:
    user_notes = f"\nReviewer notes: {notes}" if notes else ""
    failing = [number for number in (pages or []) if number]
    if failing:
        scope = (
            f"Repair only slides {failing}. Return only those pages. "
            "Do not rewrite locked slides."
        )
        payload = {
            "repair": [item for item in story if item.get("number") in set(failing)],
            "locked": [_page_context(item) for item in story if item.get("number") not in set(failing)],
        }
    else:
        scope = "Repair only the responsible parts. Return the complete story."
        payload = {"story": story}
    return f"""{STORY_RULES}
Validation or critique found the issues below. {scope} Do not change outline
length, titles, or facts. Preserve native charts, tables, KPIs, and tokens.{user_notes}

Outline: {_dumps(_outline_context(outline))}
Pages: {_dumps(payload)}
Issues: {_dumps(issues)}
"""


def _page_context(page: dict[str, Any]) -> dict[str, Any]:
    return _compact(
        {
            "number": page.get("number"),
            "title": page.get("title"),
            "role": page.get("role"),
            "family": page.get("family"),
            "takeaway": page.get("takeaway"),
        }
    )


def _outline_context(outline: dict[str, Any]) -> dict[str, Any]:
    pages = [
        {
            "number": page.get("number"),
            "title": page.get("title"),
            "core_content": page.get("core_content"),
        }
        for page in outline.get("pages") or []
    ]
    return _compact(
        {
            "title": outline.get("title"),
            "audience": outline.get("audience"),
            "purpose": outline.get("purpose"),
            "pages": pages,
        }
    )


def _dumps(value: Any) -> str:
    return json.dumps(_compact(value), ensure_ascii=False, separators=(",", ":"))


def _compact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _compact(item) for key, item in value.items() if not _omit(item)}
    if isinstance(value, list):
        return [_compact(item) for item in value]
    return value


def _omit(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}
