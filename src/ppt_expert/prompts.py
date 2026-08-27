from __future__ import annotations

import json
from typing import Any

SYSTEM_RULES = """You are an expert presentation designer. Follow these rules:
1. Preserve the user's outline. Do not add, remove, or alter slide counts, titles,
   or core facts; only refine the writing.
2. Design visuals before copy. Distribute hero slides evenly across roughly one
   quarter of the deck.
3. Prefer asymmetric content layouts with approximately 55–60% imagery and
   40–45% text.
4. Use only the approved palette and choose broadly available fonts with fallbacks.
5. Every image prompt must define a consistent art style, palette, and scene.
   Show people from the back or in profile, and explicitly prohibit text,
   watermarks, signatures, and identifiable facial details.
6. Keep body copy concise. Prefer two to five short points per slide.
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


def story_design_prompt(outline: dict[str, Any], style: dict[str, Any]) -> str:
    return f"""{SYSTEM_RULES}
Produce a slide-by-slide STORY and DESIGN from the outline and approved direction.
- Page count, numbering, titles, and core facts must map one-to-one to the outline.
- layout must be one of: hero, left_image, right_image, top_image, text, data_cards.
- Assign a stable image_id to slides that need artwork. Reuse an image_id for the
  same scene when appropriate.
- Distribute hero slides evenly and prefer a hero treatment for the cover.
- Every DESIGN color must come from the approved direction.

Outline:
{json.dumps(outline, ensure_ascii=False)}

Approved direction:
{json.dumps(style, ensure_ascii=False)}
"""


def image_plan_prompt(story: list[dict[str, Any]], design: dict[str, Any]) -> str:
    return f"""{SYSTEM_RULES}
Create an artwork plan for every non-empty image_id in STORY. Include each image_id
exactly once and list every reuse location in page_numbers. Write prompts in the
deck's language, incorporate the DESIGN art direction and palette, and end each
prompt by prohibiting text, watermarks, signatures, and identifiable facial details.

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
) -> str:
    return f"""{SYSTEM_RULES}
Validation found the issues below. Repair only the responsible parts of STORY or
DESIGN. Do not change outline length, titles, or facts, and do not introduce colors
outside the approved palette. Return the complete repaired result.

Outline: {json.dumps(outline, ensure_ascii=False)}
STORY: {json.dumps(story, ensure_ascii=False)}
DESIGN: {json.dumps(design, ensure_ascii=False)}
Issues: {json.dumps(issues, ensure_ascii=False)}
"""
