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
                f"- 分部：{page.section or '未分部'}",
                f"- 版式：{page.layout.value}",
                f"- 配图：{page.image_id or '无'} — {page.visual_direction}",
                "- 核心内容：",
                *[f"  - {item}" for item in page.content],
                "",
            ]
        )
    story_path.write_text("\n".join(story_lines), encoding="utf-8")

    design_lines = [
        "# DESIGN",
        "",
        f"- 风格：{design.style_name}（{design.mood}）",
        f"- 主色：{design.primary}",
        f"- 辅色：{design.secondary}",
        f"- 底色：{design.background}",
        f"- 正文色：{design.text}",
        f"- 强调色：{design.accent}",
        (
            f"- 标题字体：{' → '.join([design.title_font, *design.title_font_fallbacks])}，"
            f"{design.title_size}pt"
        ),
        (
            f"- 正文字体：{' → '.join([design.body_font, *design.body_font_fallbacks])}，"
            f"{design.body_size}pt"
        ),
        f"- 配图规范：{design.illustration_style}",
        f"- 禁止元素：{'、'.join(design.forbidden_elements)}",
        "- 版式：Hero 约占 1/4；内容页以非对称图文布局为主，图片 55–60%。",
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
