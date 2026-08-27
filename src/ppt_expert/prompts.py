from __future__ import annotations

import json
from typing import Any

SYSTEM_RULES = """You are an expert presentation designer. Follow these rules:
1. Preserve the user's outline. Do not add, remove, or alter slide counts, titles,
   or core facts; only refine the writing.
2. Choose a slide family from the slide's job, not by cycling a fixed layout list.
   One assertion per slide.
3. Visual-first means native charts, tables, KPI tiles, scenario matrices, and
   allocation graphics. Assign image_id only for image-led narrative slides
   (hero, left_image, right_image, top_image). Analytical slides must not depend
   on generated artwork.
4. Use only the approved palette and the approved typography stack.
5. Every image prompt must define a consistent art style, palette, and scene.
   Show people from the back or in profile, and explicitly prohibit text,
   watermarks, signatures, and identifiable facial details.
6. Keep body copy concise. Put numbers into kpis, chart, table, or allocation
   fields instead of burying them in bullets.
"""


def outline_prompt(request: str) -> str:
    return f"""{SYSTEM_RULES}
Parse the user input into a slide-by-slide outline. If the user provides only a
topic with no slide count, create a complete ten-slide structure. Preserve any
explicit numbering or structure exactly.

User input:
{request}
"""


def styles_prompt(outline: dict[str, Any]) -> str:
    return f"""{SYSTEM_RULES}
Create four distinct, professional visual directions labeled A, B, C, and D.
Each direction must include a name, mood, and five #RRGGBB colors with sufficient
contrast for readable body copy.

Outline:
{json.dumps(outline, ensure_ascii=False)}
"""


def story_design_prompt(
    outline: dict[str, Any],
    style: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
    brief: dict[str, Any] | None = None,
) -> str:
    return f"""{SYSTEM_RULES}
Produce a slide-by-slide STORY and DESIGN from the outline and approved direction.
- Page count, numbering, titles, and core facts must map one-to-one to the outline.
- layout must be one of: hero, left_image, right_image, top_image, text, data_cards.
- family should be one of: cover, section, executive_summary, kpi_strip,
  chart_interpretation, dual_chart, table_comparison, scenario_matrix, allocation,
  waterfall, heatmap, timeline, pillars, quote, conclusion, appendix, hero,
  left_image, right_image, top_image, text, data_cards.
- Cover slides need eyebrow, subtitle, and 2–4 kpis. Analytical slides need chart,
  table, scenarios, allocation, waterfall, or heatmap when the evidence is quantitative.
- Bind evidence_ids to the EvidenceItem ids supplied below. Do not invent metrics.
- chart uses chart_type line|column|bar|area, categories, and series[].values as numbers.
- Assign a stable image_id only when the family is image-led. Leave image_id null
  for covers and analytical slides that can be drawn with vectors.
- Every DESIGN color must come from the approved direction.

Brief:
{json.dumps(brief or {}, ensure_ascii=False)}

Evidence:
{json.dumps(evidence or [], ensure_ascii=False)}

Outline:
{json.dumps(outline, ensure_ascii=False)}

Approved direction:
{json.dumps(style, ensure_ascii=False)}
"""


def image_plan_prompt(story: list[dict[str, Any]], design: dict[str, Any]) -> str:
    return f"""{SYSTEM_RULES}
Create an artwork plan only for image-led slides that already have an image_id.
Do not invent artwork for covers, KPI strips, charts, tables, scenarios, or
allocation slides. Include each image_id exactly once and list every reuse
location in page_numbers. Write prompts in the deck's language, incorporate the
DESIGN art direction and palette, and end each prompt by prohibiting text,
watermarks, signatures, and identifiable facial details.

STORY:
{json.dumps(story, ensure_ascii=False)}

DESIGN:
{json.dumps(design, ensure_ascii=False)}
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
length, titles, or facts, and do not introduce colors outside the approved
palette. Preserve native charts, tables, KPIs, and typography.
Return the complete repaired result.{user_notes}

Outline: {json.dumps(outline, ensure_ascii=False)}
STORY: {json.dumps(story, ensure_ascii=False)}
DESIGN: {json.dumps(design, ensure_ascii=False)}
Issues: {json.dumps(issues, ensure_ascii=False)}
"""
