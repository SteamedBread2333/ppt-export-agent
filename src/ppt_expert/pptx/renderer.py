from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

from ppt_expert.config import AgentConfig
from ppt_expert.models import DesignSpec, DesignTokens, StoryPage
from ppt_expert.pptx.primitives import Canvas, paint_background, speaker_notes
from ppt_expert.pptx.slides import compose_slide
from ppt_expert.recipes import tokens_for


def render_presentation(
    pages: list[StoryPage],
    design: DesignSpec,
    image_paths: dict[str, str],
    output_path: Path,
    config: AgentConfig,
    template_path: str | Path | None = None,
    tokens: DesignTokens | None = None,
) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs = Presentation(str(template_path)) if template_path else Presentation()
    if template_path:
        _clear_slides(prs)
    tokens = tokens or _tokens_from_design(design)
    prs.slide_width = Inches(tokens.page.w)
    prs.slide_height = Inches(tokens.page.h)
    _write_metadata(prs, design)
    blank = min(prs.slide_layouts, key=lambda layout: len(layout.placeholders))
    for page in pages:
        slide = prs.slides.add_slide(blank)
        for placeholder in list(slide.placeholders):
            placeholder._element.getparent().remove(placeholder._element)
        dark = page.is_dark()
        fill = tokens.colors.dark_bg if dark else tokens.colors.bg
        if not template_path:
            paint_background(slide, fill, prs.slide_width, prs.slide_height)
        canvas = Canvas(slide=slide, tokens=tokens, dark=dark)
        compose_slide(canvas, page, image_paths.get(page.image_id or ""))
        speaker_notes(slide, page)
    prs.save(output_path)
    return str(output_path.resolve())


def _tokens_from_design(design: DesignSpec) -> DesignTokens:
    from ppt_expert.models import RecipeId

    try:
        recipe = RecipeId(design.typography_profile)
    except ValueError:
        recipe = RecipeId.CONSULTING
    tokens = tokens_for(recipe)
    colors = tokens.colors.model_copy(
        update={
            "accent": design.primary or tokens.colors.accent,
            "bg": design.background or tokens.colors.bg,
            "ink": design.text or tokens.colors.ink,
            "ink2": design.secondary or tokens.colors.ink2,
            "surface": design.surface or tokens.colors.surface,
            "muted": design.muted or tokens.colors.muted,
            "positive": design.positive or tokens.colors.positive,
            "caution": design.warning or tokens.colors.caution,
            "risk": design.negative or tokens.colors.risk,
        }
    )
    fonts = tokens.fonts.model_copy(
        update={
            "cn": design.east_asian_font or design.body_font or tokens.fonts.cn,
            "display": design.title_font or tokens.fonts.display,
            "num": design.latin_font or tokens.fonts.num,
        }
    )
    return tokens.model_copy(update={"colors": colors, "fonts": fonts})


def _write_metadata(presentation: Presentation, design: DesignSpec) -> None:
    core = presentation.core_properties
    core.title = design.style_name
    core.subject = design.mood
    core.author = "PPT Expert"
    core.category = design.typography_profile


def _clear_slides(presentation: Presentation) -> None:
    slide_ids = presentation.slides._sldIdLst
    for slide_id in list(slide_ids):
        presentation.part.drop_rel(slide_id.rId)
        slide_ids.remove(slide_id)
