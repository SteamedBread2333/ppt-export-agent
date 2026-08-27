from __future__ import annotations

from pathlib import Path

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from ppt_expert.config import AgentConfig
from ppt_expert.models import ChartType, DesignSpec, SlideFamily, StoryPage

SLIDE_W = 13.333
SLIDE_H = 7.5
MARGIN = 0.62
GUTTER = 0.16
COLUMNS = 12
CHART_TYPES = {
    ChartType.LINE: XL_CHART_TYPE.LINE,
    ChartType.COLUMN: XL_CHART_TYPE.COLUMN_CLUSTERED,
    ChartType.BAR: XL_CHART_TYPE.BAR_CLUSTERED,
    ChartType.AREA: XL_CHART_TYPE.AREA,
}


def _rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value.lstrip("#"))


def _col(start: int, span: int) -> tuple[float, float]:
    inner = SLIDE_W - 2 * MARGIN
    width = (inner - (COLUMNS - 1) * GUTTER) / COLUMNS
    left = MARGIN + start * (width + GUTTER)
    return left, span * width + (span - 1) * GUTTER


def _surface(design: DesignSpec) -> str:
    return design.surface or design.background


def _muted(design: DesignSpec) -> str:
    return design.muted or design.text


def _latin(design: DesignSpec) -> str:
    return design.latin_font or design.title_font


def _east_asian(design: DesignSpec) -> str:
    return design.east_asian_font or design.body_font


def _numeric(design: DesignSpec) -> str:
    return design.numeric_font or _latin(design)


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
        layout = (
            _layout_for_family(prs, page, blank_layout) if template_path else blank_layout
        )
        slide = prs.slides.add_slide(layout)
        for placeholder in list(slide.placeholders):
            placeholder._element.getparent().remove(placeholder._element)
        if not template_path:
            _background(slide, design.background, prs.slide_width, prs.slide_height)
        image_path = image_paths.get(page.image_id or "")
        _compose(slide, page, design, image_path, prs.slide_width, prs.slide_height)
        _footer(slide, page, design)
    prs.save(output_path)
    return str(output_path.resolve())


def _compose(slide, page: StoryPage, design: DesignSpec, image_path, width, height) -> None:
    family = page.resolved_family()
    if page.chart is not None and page.chart_secondary is not None:
        _dual_chart(slide, page, design)
    elif page.waterfall:
        _waterfall_page(slide, page, design)
    elif page.heatmap is not None:
        _heatmap_page(slide, page, design)
    elif page.chart is not None:
        _chart_page(slide, page, design)
    elif page.table is not None:
        _table_page(slide, page, design)
    elif page.scenarios:
        _scenario_page(slide, page, design)
    elif page.allocation:
        _allocation_page(slide, page, design)
    elif page.milestones and family in {SlideFamily.TIMELINE, SlideFamily.CONCLUSION}:
        if family == SlideFamily.CONCLUSION:
            _conclusion(slide, page, design)
            _timeline_band(slide, page, design, top=5.6)
        else:
            _timeline_page(slide, page, design)
    elif family == SlideFamily.SECTION:
        _section_page(slide, page, design)
    elif family == SlideFamily.QUOTE or page.quote:
        _quote_page(slide, page, design)
    elif family == SlideFamily.COVER:
        _cover(slide, page, design, image_path, width, height)
    elif family in {SlideFamily.KPI_STRIP, SlideFamily.EXECUTIVE_SUMMARY} or (
        family == SlideFamily.DATA_CARDS and page.kpis
    ):
        _kpi_page(slide, page, design)
    elif family in {SlideFamily.PILLARS, SlideFamily.DATA_CARDS}:
        _data_cards(slide, page, design)
    elif family == SlideFamily.CONCLUSION:
        _conclusion(slide, page, design)
    elif family == SlideFamily.HERO:
        _hero(slide, page, design, image_path, width, height)
    elif family == SlideFamily.LEFT_IMAGE:
        _split(slide, page, design, image_path, image_left=True)
    elif family == SlideFamily.RIGHT_IMAGE:
        _split(slide, page, design, image_path, image_left=False)
    elif family == SlideFamily.TOP_IMAGE:
        _top_image(slide, page, design, image_path)
    else:
        _text_page(slide, page, design)


_FAMILY_LAYOUT_ALIASES: dict[SlideFamily, tuple[str, ...]] = {
    SlideFamily.COVER: ("title slide", "cover", "title"),
    SlideFamily.SECTION: ("section header", "section"),
    SlideFamily.EXECUTIVE_SUMMARY: ("title and content", "comparison"),
    SlideFamily.CONCLUSION: ("title and content", "blank"),
    SlideFamily.QUOTE: ("quote", "title only"),
    SlideFamily.APPENDIX: ("blank", "title and content"),
}


def _layout_for_family(presentation: Presentation, page: StoryPage, fallback):
    family = page.resolved_family()
    wanted = (
        family.value.replace("_", " "),
        family.value.replace("_", "-"),
        *_FAMILY_LAYOUT_ALIASES.get(family, ()),
    )
    best = None
    best_score = 0
    for layout in presentation.slide_layouts:
        name = (layout.name or "").casefold()
        if not name:
            continue
        for rank, alias in enumerate(wanted):
            if alias == name or (len(alias) > 4 and alias in name):
                score = 100 - rank
                if score > best_score:
                    best = layout
                    best_score = score
                break
    return best or fallback


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


def _rect(slide, left: float, top: float, width: float, height: float, color: str, rounded=False):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(left), Inches(top), Inches(width), Inches(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = _rgb(color)
    shape.line.fill.background()
    return shape


def _apply_run_fonts(run, latin: str, east_asian: str) -> None:
    run.font.name = latin
    rPr = run._r.get_or_add_rPr()
    for tag, typeface in (("a:latin", latin), ("a:ea", east_asian), ("a:cs", latin)):
        element = rPr.find(qn(tag))
        if element is None:
            element = etree.SubElement(rPr, qn(tag))
        element.set("typeface", typeface)


def _textbox(
    slide,
    text: str,
    left: float,
    top: float,
    width: float,
    height: float,
    size: int,
    color: str,
    design: DesignSpec,
    bold: bool = False,
    align=PP_ALIGN.LEFT,
    role: str = "body",
):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.margin_left = frame.margin_right = Inches(0.04)
    frame.margin_top = frame.margin_bottom = Inches(0.02)
    frame.vertical_anchor = MSO_ANCHOR.TOP
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    paragraph.alignment = align
    latin = _numeric(design) if role == "numeric" else _latin(design)
    if role in {"display", "headline"}:
        latin = _latin(design)
    east_asian = _east_asian(design)
    paragraph.font.name = latin
    paragraph.font.size = Pt(size)
    paragraph.font.bold = bold
    paragraph.font.color.rgb = _rgb(color)
    for run in paragraph.runs:
        _apply_run_fonts(run, latin, east_asian)
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = _rgb(color)
    return box


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


def _content_text(page: StoryPage) -> str:
    return "\n".join(f"•  {item}" for item in page.content)


def _header(slide, page: StoryPage, design: DesignSpec, title_size: int | None = None) -> None:
    left, width = _col(0, 12)
    eyebrow = page.eyebrow or page.section or page.resolved_family().value.replace("_", " ").upper()
    _textbox(
        slide, eyebrow, left, 0.38, width, 0.28, 11, design.accent, design, bold=True, role="label"
    )
    _textbox(
        slide,
        page.title,
        left,
        0.64,
        width,
        0.72,
        title_size or min(28, design.title_size),
        design.text,
        design,
        bold=True,
        role="headline",
    )
    if page.subtitle:
        _textbox(
            slide, page.subtitle, left, 1.32, width, 0.36, 14, _muted(design), design, role="body"
        )


def _footer(slide, page: StoryPage, design: DesignSpec) -> None:
    left, width = _col(0, 10)
    note = page.source_note or page.section or ""
    if note:
        _textbox(slide, note, left, 7.12, width, 0.22, 10, _muted(design), design, role="label")
    _textbox(
        slide,
        f"{page.number:02d}",
        12.2,
        7.12,
        0.7,
        0.22,
        10,
        _muted(design),
        design,
        False,
        PP_ALIGN.RIGHT,
        "label",
    )


def _cover(slide, page, design, image_path, width, height) -> None:
    _rect(slide, 0, 0, 0.18, SLIDE_H, design.primary)
    left, text_w = _col(0, 8 if image_path else 12)
    eyebrow = page.eyebrow or page.section or "BRIEFING"
    _textbox(
        slide, eyebrow, left, 1.05, text_w, 0.32, 12, design.accent, design, bold=True, role="label"
    )
    _textbox(
        slide, page.title, left, 1.42, text_w, 1.35, 32, design.text, design, True, role="display"
    )
    y = 2.9
    if page.subtitle:
        _textbox(slide, page.subtitle, left, y, text_w, 0.4, 16, _muted(design), design, role="body")
        y = 3.32
    _textbox(
        slide, " · ".join(page.content), left, y, text_w, 0.7, 16, _muted(design), design, role="body"
    )
    kpis = page.kpis[:3]
    if kpis:
        _kpi_row(slide, kpis, design, top=4.35)
    if image_path:
        img_left, img_w = _col(8, 4)
        picture = _picture_cover(
            slide, image_path, Inches(img_left), Inches(1.1), Inches(img_w), Inches(5.5)
        )
        if picture is None:
            _rect(slide, img_left, 1.1, img_w, 5.5, _surface(design), rounded=True)
    elif not kpis:
        _sparkline(slide, design, *_col(8, 4), 4.35, 1.7)


def _kpi_row(slide, kpis, design: DesignSpec, top: float) -> None:
    count = max(1, min(4, len(kpis)))
    span = 12 // count
    for index, item in enumerate(kpis[:count]):
        left, width = _col(index * span, span)
        _rect(slide, left, top, width, 1.7, _surface(design), rounded=True)
        _rect(slide, left, top, 0.08, 1.7, design.accent if index == 0 else design.primary)
        _textbox(
            slide,
            item.value,
            left + 0.22,
            top + 0.22,
            width - 0.36,
            0.62,
            26,
            design.primary,
            design,
            True,
            role="numeric",
        )
        _textbox(
            slide,
            item.label,
            left + 0.22,
            top + 0.86,
            width - 0.36,
            0.36,
            13,
            design.text,
            design,
            True,
            role="label",
        )
        if item.note:
            _textbox(
                slide,
                item.note,
                left + 0.22,
                top + 1.22,
                width - 0.36,
                0.32,
                11,
                _muted(design),
                design,
                role="label",
            )


def _sparkline(slide, design, left, width, top, height) -> None:
    values = [3, 4, 3, 6, 5, 8, 7, 9]
    gap = 0.08
    bar_w = (width - gap * (len(values) - 1)) / len(values)
    peak = max(values)
    for index, value in enumerate(values):
        bar_h = height * (0.28 + 0.72 * value / peak)
        _rect(
            slide,
            left + index * (bar_w + gap),
            top + height - bar_h,
            bar_w,
            bar_h,
            design.accent if index == len(values) - 1 else design.secondary,
            rounded=True,
        )


def _kpi_page(slide, page, design) -> None:
    _header(slide, page, design)
    if page.kpis:
        _kpi_row(slide, page.kpis, design, top=1.7)
        body_top = 3.6
    else:
        body_top = 1.7
    left, width = _col(0, 12)
    _textbox(
        slide,
        _content_text(page),
        left,
        body_top,
        width,
        3.2,
        design.body_size,
        design.text,
        design,
    )
    if page.takeaway:
        left, width = _col(0, 12)
        _rect(slide, left, 6.35, width, 0.55, _surface(design), rounded=True)
        _textbox(
            slide, page.takeaway, left + 0.2, 6.42, width - 0.4, 0.4, 13, design.text, design, True
        )


def _chart_page(slide, page, design) -> None:
    _header(slide, page, design)
    left, width = _col(0, 8)
    _add_chart(slide, page.chart, design, left, 1.55, width, 4.7)
    rail_left, rail_w = _col(8, 4)
    _rect(slide, rail_left, 1.55, rail_w, 4.7, _surface(design), rounded=True)
    _textbox(
        slide,
        page.takeaway or "Interpretation",
        rail_left + 0.18,
        1.72,
        rail_w - 0.36,
        0.5,
        14,
        design.primary,
        design,
        True,
        role="headline",
    )
    _textbox(
        slide,
        _content_text(page),
        rail_left + 0.18,
        2.3,
        rail_w - 0.36,
        3.7,
        max(13, design.body_size - 3),
        design.text,
        design,
    )


def _add_chart(slide, spec, design, left, top, width, height) -> None:
    data = CategoryChartData()
    data.categories = spec.categories
    for series in spec.series:
        data.add_series(series.name, series.values)
    frame = slide.shapes.add_chart(
        CHART_TYPES[spec.chart_type],
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
        data,
    )
    chart = frame.chart
    chart.has_legend = len(spec.series) > 1
    if chart.has_legend:
        chart.legend.include_in_layout = False
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    if spec.title:
        chart.has_title = True
        chart.chart_title.text_frame.text = spec.title
    colors = [design.primary, design.accent, design.secondary, design.text]
    for index, series in enumerate(chart.series):
        color = colors[index % len(colors)]
        if spec.chart_type in {ChartType.COLUMN, ChartType.BAR, ChartType.AREA}:
            series.format.fill.solid()
            series.format.fill.fore_color.rgb = _rgb(color)
            series.format.line.fill.background()
        else:
            try:
                series.format.line.color.rgb = _rgb(color)
            except ValueError:
                series.format.fill.solid()
                series.format.fill.fore_color.rgb = _rgb(color)
    try:
        chart.value_axis.has_major_gridlines = False
        chart.value_axis.has_minor_gridlines = False
    except ValueError:
        pass


def _dual_chart(slide, page, design) -> None:
    _header(slide, page, design)
    left, width = _col(0, 6)
    _add_chart(slide, page.chart, design, left, 1.55, width, 3.6)
    right, right_w = _col(6, 6)
    _add_chart(slide, page.chart_secondary, design, right, 1.55, right_w, 3.6)
    body_left, body_w = _col(0, 12)
    _textbox(
        slide, _content_text(page), body_left, 5.35, body_w, 1.5, design.body_size, design.text, design
    )


def _waterfall_page(slide, page, design) -> None:
    _header(slide, page, design)
    items = page.waterfall[:7]
    left, width = _col(0, 12)
    span = max(width / max(len(items), 1) - 0.12, 0.4)
    peak = max((abs(item.value) for item in items), default=1) or 1
    running = 0.0
    for index, item in enumerate(items):
        x = left + index * (span + 0.12)
        if item.total:
            running = item.value
            bar_h = 3.2 * abs(item.value) / peak
            y = 5.2 - bar_h
            color = design.accent
        else:
            start = running
            running += item.value
            bar_h = 3.2 * abs(item.value) / peak
            baseline = 5.2 - 3.2 * max(start, 0) / peak if item.value >= 0 else 5.2 - 3.2 * running / peak
            y = max(1.7, min(baseline, 5.2 - bar_h))
            color = design.secondary if item.value >= 0 else design.primary
        _rect(slide, x, y, span, max(bar_h, 0.12), color, rounded=True)
        _textbox(
            slide, item.label, x, 5.35, span, 0.32, 11, design.text, design, True, role="label"
        )
        _textbox(
            slide, f"{item.value:+.1f}" if not item.total else f"{item.value:.1f}",
            x, 5.64, span, 0.28, 11, _muted(design), design, role="numeric",
        )
    _textbox(
        slide, _content_text(page), left, 6.15, width, 0.8, 13, design.text, design
    )


def _heatmap_page(slide, page, design) -> None:
    _header(slide, page, design)
    spec = page.heatmap
    rows = 1 + len(spec.rows)
    cols = 1 + len(spec.columns)
    left, width = _col(0, 12)
    table = slide.shapes.add_table(
        rows, cols, Inches(left), Inches(1.55), Inches(width), Inches(4.2)
    ).table
    _fill_cell(table.cell(0, 0), "", design, fill=_surface(design), color=design.text)
    for index, header in enumerate(spec.columns, 1):
        _fill_cell(table.cell(0, index), header, design, fill=design.primary, color="#FFFFFF", bold=True)
    for row_index, label in enumerate(spec.rows, 1):
        _fill_cell(table.cell(row_index, 0), label, design, fill=_surface(design), color=design.text, bold=True)
        values = spec.values[row_index - 1] if row_index - 1 < len(spec.values) else []
        for col_index in range(1, cols):
            value = values[col_index - 1] if col_index - 1 < len(values) else 0
            fill = design.primary if value >= 0.66 else (design.secondary if value >= 0.33 else _surface(design))
            color = "#FFFFFF" if fill != _surface(design) else design.text
            _fill_cell(table.cell(row_index, col_index), f"{value:.1f}", design, fill=fill, color=color)
    _textbox(
        slide, _content_text(page), left, 6.0, width, 0.9, 13, design.text, design
    )


def _timeline_page(slide, page, design) -> None:
    _header(slide, page, design)
    _timeline_band(slide, page, design, top=2.4)
    left, width = _col(0, 12)
    _textbox(
        slide, _content_text(page), left, 5.4, width, 1.5, design.body_size, design.text, design
    )


def _timeline_band(slide, page, design, top: float) -> None:
    items = page.milestones[:5]
    if not items:
        return
    left, width = _col(0, 12)
    _rect(slide, left, top + 0.42, width, 0.06, design.secondary)
    span = width / max(len(items), 1)
    for index, item in enumerate(items):
        x = left + index * span + span / 2 - 0.12
        _rect(slide, x, top + 0.28, 0.24, 0.24, design.accent, rounded=True)
        _textbox(
            slide, item.date or item.label, left + index * span, top, span - 0.08, 0.28, 11,
            design.accent, design, True, role="label",
        )
        _textbox(
            slide, item.note or item.label, left + index * span, top + 0.62, span - 0.08, 0.7, 12,
            design.text, design, role="body",
        )


def _section_page(slide, page, design) -> None:
    left, width = _col(0, 12)
    _textbox(
        slide, page.eyebrow or f"{page.number:02d}", left, 2.2, width, 0.4, 14, design.accent, design,
        True, PP_ALIGN.CENTER, "label",
    )
    _textbox(
        slide, page.title, left, 2.7, width, 1.4, 36, design.text, design, True, PP_ALIGN.CENTER, "display"
    )
    _textbox(
        slide, " · ".join(page.content), left, 4.3, width, 1.0, 16, _muted(design), design,
        False, PP_ALIGN.CENTER, "body",
    )


def _quote_page(slide, page, design) -> None:
    left, width = _col(1, 10)
    _rect(slide, left, 1.8, 0.12, 3.6, design.accent)
    quote = page.quote or page.content[0]
    _textbox(
        slide, quote, left + 0.4, 2.0, width - 0.4, 2.4, 28, design.text, design, True, role="display"
    )
    _textbox(
        slide, _content_text(page), left + 0.4, 4.6, width - 0.4, 1.8, 16, _muted(design), design
    )


def _table_page(slide, page, design) -> None:
    _header(slide, page, design)
    spec = page.table
    rows = 1 + len(spec.rows)
    cols = len(spec.headers)
    left, width = _col(0, 12)
    table = slide.shapes.add_table(
        rows, cols, Inches(left), Inches(1.55), Inches(width), Inches(min(4.4, 0.42 * rows + 0.5))
    ).table
    for index, header in enumerate(spec.headers):
        _fill_cell(table.cell(0, index), header, design, fill=design.primary, color="#FFFFFF", bold=True)
    for row_index, row in enumerate(spec.rows, 1):
        highlight = spec.highlight_row == row_index - 1
        fill = design.secondary if highlight else _surface(design)
        text = design.text
        for col_index, value in enumerate(row):
            cell_text = value if col_index < len(row) else ""
            _fill_cell(table.cell(row_index, col_index), cell_text, design, fill=fill, color=text)
    _textbox(
        slide,
        _content_text(page),
        left,
        6.15,
        width,
        0.8,
        max(12, design.body_size - 4),
        design.text,
        design,
    )


def _fill_cell(cell, text: str, design: DesignSpec, *, fill: str, color: str, bold: bool = False) -> None:
    cell.text = text
    cell.fill.solid()
    cell.fill.fore_color.rgb = _rgb(fill)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    for paragraph in cell.text_frame.paragraphs:
        paragraph.font.size = Pt(12)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = _rgb(color)
        paragraph.font.name = _latin(design)
        for run in paragraph.runs:
            _apply_run_fonts(run, _latin(design), _east_asian(design))
            run.font.size = Pt(12)
            run.font.bold = bold
            run.font.color.rgb = _rgb(color)


def _scenario_page(slide, page, design) -> None:
    _header(slide, page, design)
    columns = page.scenarios[:4]
    span = 12 // max(len(columns), 1)
    for index, column in enumerate(columns):
        left, width = _col(index * span, span)
        fill = design.primary if column.featured else _surface(design)
        text = "#FFFFFF" if column.featured else design.text
        muted = "#FFFFFF" if column.featured else _muted(design)
        _rect(slide, left, 1.55, width, 5.25, fill, rounded=True)
        _textbox(
            slide, column.name, left + 0.16, 1.72, width - 0.32, 0.4, 16, text, design, True,
            role="headline",
        )
        _textbox(
            slide, column.probability, left + 0.16, 2.16, width - 0.32, 0.32, 13, muted, design,
            role="label",
        )
        body = "\n".join(item for item in [column.trigger, column.outcome, column.implication] if item)
        _textbox(slide, body, left + 0.16, 2.6, width - 0.32, 3.9, 13, text, design)
    left, width = _col(0, 12)
    _textbox(
        slide, _content_text(page), left, 6.9, width, 0.18, 11, _muted(design), design, role="label"
    )


def _allocation_page(slide, page, design) -> None:
    _header(slide, page, design)
    items = page.allocation[:6]
    total = sum(item.percent for item in items) or 100
    left, width = _col(0, 12)
    cursor = left
    palette = [design.primary, design.accent, design.secondary, design.text]
    _rect(slide, left, 1.7, width, 0.55, _surface(design), rounded=True)
    for index, item in enumerate(items):
        segment = width * (item.percent / total)
        _rect(slide, cursor, 1.7, max(segment, 0.04), 0.55, palette[index % len(palette)])
        cursor += segment
    for index, item in enumerate(items):
        row_top = 2.55 + index * 0.7
        _rect(slide, left, row_top + 0.12, 0.22, 0.22, palette[index % len(palette)], rounded=True)
        _textbox(
            slide,
            f"{item.label}  {item.percent:.0f}%",
            left + 0.4,
            row_top,
            7.5,
            0.35,
            16,
            design.text,
            design,
            True,
            role="numeric",
        )
        _textbox(
            slide, item.note or page.content[min(index, len(page.content) - 1)],
            left + 0.4, row_top + 0.32, 11.2, 0.3, 12, _muted(design), design, role="label",
        )
    # Ensure every content bullet is present as its own substring.
    leftover = [item for item in page.content if item not in " ".join(entry.note for entry in items)]
    if leftover:
        _textbox(
            slide, _content_text(page), left, 6.4, width, 0.55, 12, design.text, design
        )


def _conclusion(slide, page, design) -> None:
    _rect(slide, 0, 0, 0.18, SLIDE_H, design.accent)
    left, width = _col(0, 12)
    _textbox(
        slide, page.eyebrow or "NEXT STEP", left, 1.35, width, 0.3, 12, design.accent, design,
        True, role="label",
    )
    _textbox(
        slide, page.title, left, 1.75, width, 1.2, 32, design.text, design, True, role="display"
    )
    _textbox(
        slide, _content_text(page), left, 3.2, width, 2.6, design.body_size + 1, design.text, design
    )


def _hero(slide, page, design, image_path, width, height) -> None:
    picture = _picture_cover(slide, image_path, 0, 0, width, height)
    if picture is None:
        _cover(slide, page, design, None, width, height)
        return
    overlay = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, Inches(4.45), width, Inches(3.05)
    )
    overlay.fill.solid()
    overlay.fill.fore_color.rgb = _rgb(design.primary)
    overlay.line.fill.background()
    _textbox(
        slide, page.title, 0.95, 4.78, 11.4, 1.05, min(36, design.title_size + 8), "#FFFFFF",
        design, True, PP_ALIGN.CENTER, "display",
    )
    if page.content:
        _textbox(
            slide, " · ".join(page.content[:3]), 1.3, 5.92, 10.7, 0.8, min(18, design.body_size),
            "#FFFFFF", design, False, PP_ALIGN.CENTER, "body",
        )


def _split(slide, page, design, image_path, image_left: bool) -> None:
    image_x = 0.0 if image_left else 6.25
    text_x = 7.0 if image_left else 0.75
    picture = _picture_cover(
        slide, image_path, Inches(image_x), 0, Inches(7.08), Inches(7.5)
    )
    if picture is None:
        _rect(slide, image_x, 0, 7.08, 7.5, _surface(design))
    _rect(slide, text_x, 0.82, 0.75, 0.1, design.accent)
    _textbox(
        slide, page.title, text_x, 1.08, 5.45, 1.25, design.title_size, design.text, design, True,
        role="headline",
    )
    _textbox(
        slide, _content_text(page), text_x, 2.55, 5.25, 3.9, design.body_size, design.text, design
    )


def _top_image(slide, page, design, image_path) -> None:
    picture = _picture_cover(slide, image_path, 0, 0, Inches(13.333), Inches(4.25))
    if picture is None:
        _rect(slide, 0, 0, SLIDE_W, 4.25, _surface(design))
    _textbox(
        slide, page.title, 0.85, 4.55, 4.4, 1.0, design.title_size, design.primary, design, True,
        role="headline",
    )
    _textbox(
        slide, _content_text(page), 5.3, 4.55, 7.1, 2.1, max(15, design.body_size - 1),
        design.text, design,
    )


def _text_page(slide, page, design) -> None:
    _header(slide, page, design, title_size=design.title_size + 2)
    left, width = _col(0, 12)
    _textbox(
        slide, _content_text(page), left, 1.7, width, 4.9, design.body_size + 1, design.text, design
    )


def _data_cards(slide, page, design) -> None:
    _header(slide, page, design)
    items = page.content[:4]
    count = max(1, len(items))
    span = 12 // count
    for index, item in enumerate(items):
        left, width = _col(index * span, span)
        fill = design.secondary if index % 2 else design.primary
        _rect(slide, left, 1.7, width, 4.6, fill, rounded=True)
        _textbox(
            slide, item, left + 0.22, 2.15, width - 0.44, 3.6, design.body_size, "#FFFFFF",
            design, True, PP_ALIGN.CENTER, "body",
        )
