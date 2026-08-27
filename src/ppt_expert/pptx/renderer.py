from __future__ import annotations

from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Inches, Pt

from ppt_expert.config import AgentConfig
from ppt_expert.models import DesignSpec, LayoutType, StoryPage


def _rgb(value: str) -> RGBColor:
    value = value.lstrip("#")
    return RGBColor.from_string(value)


def render_presentation(
    pages: list[StoryPage],
    design: DesignSpec,
    image_paths: dict[str, str],
    output_path: Path,
    config: AgentConfig,
    template_path: str | Path | None = None,
) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs = Presentation(str(template_path)) if template_path else Presentation()
    if template_path:
        _clear_slides(prs)
    prs.slide_width = Inches(config.slide_width_inches)
    prs.slide_height = Inches(config.slide_height_inches)
    blank_layout = min(prs.slide_layouts, key=lambda layout: len(layout.placeholders))
    for page in pages:
        slide = prs.slides.add_slide(blank_layout)
        for placeholder in list(slide.placeholders):
            placeholder._element.getparent().remove(placeholder._element)
        if not template_path:
            _background(slide, design.background, prs.slide_width, prs.slide_height)
        image_path = image_paths.get(page.image_id or "")
        if page.layout == LayoutType.HERO:
            _hero(slide, page, design, image_path, prs.slide_width, prs.slide_height)
        elif page.layout == LayoutType.LEFT_IMAGE:
            _split(slide, page, design, image_path, image_left=True)
        elif page.layout == LayoutType.RIGHT_IMAGE:
            _split(slide, page, design, image_path, image_left=False)
        elif page.layout == LayoutType.TOP_IMAGE:
            _top_image(slide, page, design, image_path)
        elif page.layout == LayoutType.DATA_CARDS:
            _data_cards(slide, page, design)
        else:
            _text_page(slide, page, design)
        _page_number(slide, page.number, design)
    prs.save(output_path)
    return str(output_path.resolve())


def _clear_slides(presentation: Presentation) -> None:
    slide_ids = presentation.slides._sldIdLst
    for slide_id in list(slide_ids):
        presentation.part.drop_rel(slide_id.rId)
        slide_ids.remove(slide_id)


def _background(slide, color: str, width: int, height: int) -> None:
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = _rgb(color)
    shape.line.fill.background()


def _picture_cover(slide, image_path: str | None, left, top, width, height):
    if not image_path or not Path(image_path).exists():
        return None
    with Image.open(image_path) as image:
        source_ratio = image.width / image.height
    target_ratio = width / height
    picture = slide.shapes.add_picture(image_path, left, top, width, height)
    if source_ratio > target_ratio:
        crop = (1 - target_ratio / source_ratio) / 2
        picture.crop_left = crop
        picture.crop_right = crop
    else:
        crop = (1 - source_ratio / target_ratio) / 2
        picture.crop_top = crop
        picture.crop_bottom = crop
    return picture


def _textbox(slide, text: str, left, top, width, height, size: int, color: str, font: str,
             bold: bool = False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    frame.margin_left = frame.margin_right = Inches(0.04)
    frame.margin_top = frame.margin_bottom = Inches(0.03)
    frame.vertical_anchor = MSO_ANCHOR.TOP
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    paragraph.alignment = align
    paragraph.font.name = font
    paragraph.font.size = Pt(size)
    paragraph.font.bold = bold
    paragraph.font.color.rgb = _rgb(color)
    return box


def _content_text(page: StoryPage) -> str:
    return "\n".join(f"•  {item}" for item in page.content)


def _hero(slide, page, design, image_path, width, height) -> None:
    _picture_cover(slide, image_path, 0, 0, width, height)
    overlay = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, Inches(4.45), width, Inches(3.05)
    )
    overlay.fill.solid()
    overlay.fill.fore_color.rgb = _rgb(design.primary)
    overlay.fill.transparency = 10
    overlay.line.fill.background()
    _textbox(
        slide, page.title, Inches(0.95), Inches(4.78), Inches(11.4), Inches(1.05),
        min(44, design.title_size + 12), "#FFFFFF", design.title_font, True, PP_ALIGN.CENTER
    )
    if page.content:
        _textbox(
            slide, " · ".join(page.content[:3]), Inches(1.3), Inches(5.92),
            Inches(10.7), Inches(0.8), min(20, design.body_size), "#FFFFFF",
            design.body_font, False, PP_ALIGN.CENTER
        )


def _split(slide, page, design, image_path, image_left: bool) -> None:
    image_x = Inches(0) if image_left else Inches(6.25)
    text_x = Inches(7.0) if image_left else Inches(0.75)
    _picture_cover(slide, image_path, image_x, 0, Inches(7.08), Inches(7.5))
    accent_x = text_x
    accent = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, accent_x, Inches(0.82), Inches(0.75), Inches(0.1)
    )
    accent.fill.solid()
    accent.fill.fore_color.rgb = _rgb(design.accent)
    accent.line.fill.background()
    _textbox(
        slide, page.title, text_x, Inches(1.08), Inches(5.45), Inches(1.25),
        design.title_size, design.text, design.title_font, True
    )
    _textbox(
        slide, _content_text(page), text_x, Inches(2.55), Inches(5.25), Inches(3.9),
        design.body_size, design.text, design.body_font
    )


def _top_image(slide, page, design, image_path) -> None:
    _picture_cover(slide, image_path, 0, 0, Inches(13.333), Inches(4.25))
    _textbox(
        slide, page.title, Inches(0.85), Inches(4.55), Inches(4.4), Inches(1.0),
        design.title_size, design.primary, design.title_font, True
    )
    _textbox(
        slide, _content_text(page), Inches(5.3), Inches(4.55), Inches(7.1), Inches(2.1),
        max(15, design.body_size - 1), design.text, design.body_font
    )


def _text_page(slide, page, design) -> None:
    _textbox(
        slide, page.title, Inches(1.0), Inches(0.9), Inches(11.2), Inches(1.2),
        design.title_size + 4, design.primary, design.title_font, True
    )
    _textbox(
        slide, _content_text(page), Inches(1.35), Inches(2.35), Inches(10.6), Inches(3.9),
        design.body_size + 1, design.text, design.body_font
    )


def _data_cards(slide, page, design) -> None:
    _textbox(
        slide, page.title, Inches(0.85), Inches(0.65), Inches(11.8), Inches(1.0),
        design.title_size, design.text, design.title_font, True
    )
    items = page.content[:4]
    card_width = 2.75 if len(items) > 3 else 3.65
    for index, item in enumerate(items):
        left = Inches(0.85 + index * (card_width + 0.35))
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(2.2), Inches(card_width), Inches(3.5)
        )
        card.fill.solid()
        card.fill.fore_color.rgb = _rgb(design.secondary if index % 2 else design.primary)
        card.fill.transparency = 5
        card.line.fill.background()
        _textbox(
            slide, item, left + Inches(0.28), Inches(2.65), Inches(card_width - 0.56),
            Inches(2.5), design.body_size, "#FFFFFF", design.body_font, True,
            PP_ALIGN.CENTER
        )


def _page_number(slide, number: int, design: DesignSpec) -> None:
    _textbox(
        slide, f"{number:02d}", Inches(12.35), Inches(7.0), Inches(0.55), Inches(0.25),
        9, design.text, design.body_font, False, PP_ALIGN.RIGHT
    )
