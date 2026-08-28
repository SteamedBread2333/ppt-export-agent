from __future__ import annotations

import json
from typing import Any

from ppt_expert.recipes import FOUNDATIONS

SYSTEM_RULES = """You are a presentation visual director, not a slide filler.
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


def intent_prompt(request: str) -> str:
    foundations = "\n".join(f"- {item}" for item in FOUNDATIONS)
    return f"""{SYSTEM_RULES}
Production foundations:
{foundations}

Fill the four production slots from the user request:
- topic: what the deck is about
- audience: who sees it and in what setting
- objective: the judgment or action it must produce
- slide_count, density (low/medium/high), editable, delivery_format

User input:
{request}
"""


def outline_prompt(request: str, intent: dict[str, Any] | None = None) -> str:
    return f"""{SYSTEM_RULES}
Parse the user input into a slide-by-slide outline of assertion titles.
If the user provides only a topic, create a complete structure of
{ (intent or {}).get("slide_count", 8) } slides. Preserve explicit numbering.

Intent:
{json.dumps(intent or {}, ensure_ascii=False)}

User input:
{request}
"""


def story_design_prompt(
    outline: dict[str, Any],
    brief: dict[str, Any] | None = None,
    evidence: list[dict[str, Any]] | None = None,
) -> str:
    return f"""{SYSTEM_RULES}
Produce STORY pages from the outline and approved style brief.
- Page count, numbering, titles, and core facts map one-to-one to the outline.
- role must be one of: cover, overview, context, evidence, structure, expansion,
  scenario, close. First page is cover, last page is close.
- Cover needs eyebrow, subtitle, 2–4 kpis. Analytical pages need chart, table,
  scenarios, or allocation when the evidence is quantitative.
- Bind evidence_ids. chart uses chart_type line|column|bar|area and numeric series.
- layout may be text. family may match the role. image_id stays null on consulting
  evidence pages.
- DESIGN colors must come from the approved brief; do not invent hex values.

Style brief:
{json.dumps(brief or {}, ensure_ascii=False)}

Evidence:
{json.dumps(evidence or [], ensure_ascii=False)}

Outline:
{json.dumps(outline, ensure_ascii=False)}
"""


def repair_prompt(
    outline: dict[str, Any],
    story: list[dict[str, Any]],
    design: dict[str, Any],
    issues: list[dict[str, Any]],
    pages: list[int] | None = None,
    notes: str = "",
) -> str:
    scope = f"Repair only slides {pages}." if pages else "Repair only the responsible parts."
    user_notes = f"\nReviewer notes: {notes}" if notes else ""
    return f"""{SYSTEM_RULES}
Validation or critique found the issues below. {scope} Do not change outline
length, titles, or facts. Preserve native charts, tables, KPIs, and tokens.
Return the complete repaired result.{user_notes}

Outline: {json.dumps(outline, ensure_ascii=False)}
STORY: {json.dumps(story, ensure_ascii=False)}
DESIGN: {json.dumps(design, ensure_ascii=False)}
Issues: {json.dumps(issues, ensure_ascii=False)}
"""
