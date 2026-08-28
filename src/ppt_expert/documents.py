from __future__ import annotations

import json
from pathlib import Path

from ppt_expert.models import DesignSpec, StoryPage


def write_contracts(project_dir: Path, pages: list[StoryPage], design: DesignSpec) -> tuple[str, str]:
    project_dir.mkdir(parents=True, exist_ok=True)
    story_path = project_dir / "STORY.md"
    design_path = project_dir / "DESIGN.md"

    story_lines = ["# STORY", ""]
    for page in pages:
        story_lines.extend(
            [
                f"## {page.number}. {page.title}",
                f"- Section: {page.section or 'Unassigned'}",
                f"- Role: {(page.role or page.resolved_role()).value}",
                f"- Layout: {page.layout.value}",
                f"- Family: {(page.family or page.resolved_family()).value}",
                f"- Artwork: {page.image_id or 'None'} — {page.visual_direction}",
            ]
        )
        if page.takeaway:
            story_lines.append(f"- Takeaway: {page.takeaway}")
        story_lines.extend(["- Core content:", *[f"  - {item}" for item in page.content], ""])
    story_path.write_text("\n".join(story_lines), encoding="utf-8")

    design_lines = [
        "# DESIGN",
        "",
        f"- Direction: {design.style_name} ({design.mood})",
        f"- Primary: {design.primary}",
        f"- Secondary: {design.secondary}",
        f"- Background: {design.background}",
        f"- Text: {design.text}",
        f"- Accent: {design.accent}",
        (
            f"- Title font: {' → '.join([design.title_font, *design.title_font_fallbacks])}, "
            f"{design.title_size}pt"
        ),
        (
            f"- Body font: {' → '.join([design.body_font, *design.body_font_fallbacks])}, "
            f"{design.body_size}pt"
        ),
        f"- Latin / numeric: {design.latin_font or design.title_font} / {design.numeric_font or design.body_font}",
        f"- East Asian: {design.east_asian_font or design.body_font}",
        f"- Typography profile: {design.typography_profile}",
        f"- Surface / muted: {design.surface or design.background} / {design.muted or design.text}",
        f"- Artwork direction: {design.illustration_style}",
        f"- Prohibited elements: {', '.join(design.forbidden_elements)}",
        (
            "- Composition: 12-column grid; analytical slides use native charts, "
            "tables, and KPI tiles before generated imagery."
        ),
        "",
    ]
    design_path.write_text("\n".join(design_lines), encoding="utf-8")
    (project_dir / "story.json").write_text(
        json.dumps([page.model_dump(mode="json") for page in pages], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (project_dir / "design.json").write_text(
        design.model_dump_json(indent=2), encoding="utf-8"
    )
    return str(story_path.resolve()), str(design_path.resolve())
