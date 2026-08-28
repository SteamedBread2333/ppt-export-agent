from __future__ import annotations

from dataclasses import dataclass, field

from lxml import etree
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_MARKER_STYLE, XL_TICK_MARK
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from ppt_expert.models import ChartSpec, ChartType, DesignTokens, KPIItem, LayoutScheme, StoryPage

CHART_TYPES = {
    ChartType.LINE: XL_CHART_TYPE.LINE,
    ChartType.COLUMN: XL_CHART_TYPE.COLUMN_CLUSTERED,
    ChartType.BAR: XL_CHART_TYPE.BAR_CLUSTERED,
    ChartType.AREA: XL_CHART_TYPE.AREA,
}


def rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value.lstrip("#"))


@dataclass
class Canvas:
    slide: object
    tokens: DesignTokens
    dark: bool = False
    boxes: list[dict] = field(default_factory=list)

    @property
    def c(self):
        return self.tokens.colors

    @property
    def f(self):
        return self.tokens.fonts

    @property
    def p(self):
        return self.tokens.page

    @property
    def scheme(self) -> LayoutScheme:
        return self.tokens.layout_scheme

    @property
    def ink(self) -> str:
        return self.c.dark_ink if self.dark else self.c.ink

    @property
    def ink2(self) -> str:
        return self.c.dark_muted if self.dark else self.c.ink2

    @property
    def muted(self) -> str:
        return self.c.dark_muted if self.dark else self.c.muted

    @property
    def bg(self) -> str:
        return self.c.dark_bg if self.dark else self.c.bg

    @property
    def surface(self) -> str:
        return self.c.dark_hairline if self.dark else self.c.surface

    @property
    def accent(self) -> str:
        return self.c.dark_accent if self.dark else self.c.accent

    @property
    def hairline_color(self) -> str:
        return self.c.dark_hairline if self.dark else self.c.hairline


def paint_background(slide, color: str, width, height) -> None:
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(color)
    shape.line.fill.background()


def _clamp(canvas: Canvas, left: float, top: float, width: float, height: float) -> tuple[float, float, float, float]:
    left = max(0.0, left)
    top = max(0.0, top)
    width = min(width, canvas.p.w - left)
    height = min(height, canvas.p.h - top)
    return left, top, max(width, 0.01), max(height, 0.01)


def rect(canvas: Canvas, left, top, width, height, color: str, rounded=False, stroke: str | None = None):
    left, top, width, height = _clamp(canvas, left, top, width, height)
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shape = canvas.slide.shapes.add_shape(
        kind, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(color)
    if stroke:
        shape.line.color.rgb = rgb(stroke)
        shape.line.width = Pt(0.75)
    else:
        shape.line.fill.background()
    return shape


def hairline(canvas: Canvas, left, top, width) -> None:
    shape = rect(canvas, left, top, width, 0.012, canvas.hairline_color)
    shape.line.fill.background()


def vline(canvas: Canvas, left, top, height) -> None:
    rect(canvas, left, top, 0.012, height, canvas.hairline_color)


def _apply_fonts(run, latin: str, east_asian: str) -> None:
    run.font.name = latin
    r_pr = run._r.get_or_add_rPr()
    for tag, typeface in (("a:latin", latin), ("a:ea", east_asian), ("a:cs", latin)):
        element = r_pr.find(qn(tag))
        if element is None:
            element = etree.SubElement(r_pr, qn(tag))
        element.set("typeface", typeface)


def _apply_paragraph_font(paragraph, latin: str, east_asian: str) -> None:
    # LibreOffice ignores run-level typefaces when choosing a CJK fallback and
    # resolves missing fonts per paragraph via a:pPr/a:defRPr; without a
    # typeface there it picks Traditional Chinese faces (LiHeiPro) whose
    # simplified-glyph gaps render as tofu boxes.
    def_rpr = paragraph._p.get_or_add_pPr().get_or_add_defRPr()
    _typeface(def_rpr, latin, east_asian)


def textbox(
    canvas: Canvas,
    text: str,
    left: float,
    top: float,
    width: float,
    height: float,
    size: int,
    color: str | None = None,
    *,
    bold: bool = False,
    align=PP_ALIGN.LEFT,
    numeric: bool = False,
    wrap: bool = True,
    anchor=MSO_ANCHOR.TOP,
):
    left, top, width, height = _clamp(canvas, left, top, width, height)
    box = canvas.slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = wrap
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.margin_left = frame.margin_right = Inches(0.04)
    frame.margin_top = frame.margin_bottom = Inches(0.02)
    frame.vertical_anchor = anchor
    paragraph = frame.paragraphs[0]
    paragraph.text = text
    paragraph.alignment = align
    paragraph.line_spacing = 1.15
    latin = canvas.f.num if numeric else canvas.f.display if bold else canvas.f.cn
    east = canvas.f.cn
    paragraph.font.size = Pt(size)
    paragraph.font.bold = bold
    paragraph.font.color.rgb = rgb(color or canvas.ink)
    _apply_paragraph_font(paragraph, latin, east)
    for run in paragraph.runs:
        _apply_fonts(run, latin, east)
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = rgb(color or canvas.ink)
    canvas.boxes.append({"text": text, "left": left, "top": top, "width": width, "height": height, "size": size, "wrap": wrap})
    return box


def token(
    canvas: Canvas,
    value: str,
    left: float,
    top: float,
    width: float,
    height: float,
    size: int = 12,
    color: str | None = None,
    bold: bool = True,
):
    """Single-line protection for short numeric tokens."""
    needed = max(0.42, len(value) * size * 0.012)
    box_w = min(max(width, needed), max(0.2, canvas.p.w - left))
    return textbox(
        canvas,
        value,
        left,
        top,
        box_w,
        height,
        size,
        color,
        bold=bold,
        numeric=True,
        wrap=False,
        anchor=MSO_ANCHOR.MIDDLE,
    )


def mini_label(canvas: Canvas, text: str, left, top, width, color: str | None = None) -> None:
    textbox(canvas, text, left, top, width, 0.22, 11, color or canvas.accent, bold=True)


def header(canvas: Canvas, page: StoryPage, volume_title: str = "") -> float:
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    nav = page.eyebrow or page.section or page.resolved_role().value.replace("_", " ").upper()
    if page.number:
        nav = f"{page.number:02d}  ·  {nav}"
    mini_label(canvas, nav, page_metrics.mx, page_metrics.header_nav_y, inner * 0.72)
    if volume_title:
        textbox(
            canvas,
            volume_title,
            page_metrics.mx + inner * 0.72,
            page_metrics.header_nav_y,
            inner * 0.28,
            0.22,
            10,
            canvas.muted,
            align=PP_ALIGN.RIGHT,
        )
    textbox(
        canvas,
        page.title,
        page_metrics.mx,
        page_metrics.header_title_y,
        inner,
        page_metrics.header_title_h,
        22 if len(page.title) > 22 else 26,
        canvas.ink,
        bold=True,
    )
    hairline(canvas, page_metrics.mx, page_metrics.header_rule_y, inner)
    return page_metrics.content_top


def footer(canvas: Canvas, page: StoryPage) -> None:
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    note = page.source_note or page.section or ""
    if note:
        textbox(canvas, note, page_metrics.mx, page_metrics.footer_y, inner - 0.9, 0.22, 10, canvas.muted)
    token(
        canvas,
        f"{page.number:02d}",
        page_metrics.w - page_metrics.mx - 0.55,
        page_metrics.footer_y,
        0.55,
        0.22,
        10,
        canvas.muted,
        bold=False,
    )


def panel(canvas: Canvas, left, top, width, height, *, accent_bar: str | None = None) -> None:
    rect(canvas, left, top, width, height, canvas.surface, stroke=canvas.hairline_color)
    if accent_bar == "left":
        rect(canvas, left, top, 0.045, height, canvas.accent)
    elif accent_bar == "top":
        rect(canvas, left, top, width, 0.03, canvas.accent)


def implication(canvas: Canvas, text: str) -> None:
    if not text:
        return
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    hairline(canvas, page_metrics.mx, page_metrics.implication_y, inner)
    textbox(
        canvas,
        text,
        page_metrics.mx,
        page_metrics.implication_y + 0.12,
        inner,
        0.4,
        15,
        canvas.ink,
        bold=True,
    )


def stat_card(canvas: Canvas, item: KPIItem, left, top, width, height) -> None:
    token(canvas, item.value, left + 0.04, top + 0.08, width - 0.1, 0.56, 28, canvas.accent)
    textbox(canvas, item.label, left + 0.04, top + 0.68, width - 0.1, 0.26, 12, canvas.ink, bold=True)
    if item.note:
        textbox(canvas, item.note, left + 0.04, top + 0.94, width - 0.1, 0.26, 11, canvas.muted)


def progress(canvas: Canvas, left, top, width, height, percent: float, color: str | None = None) -> None:
    rect(canvas, left, top, width, height, canvas.surface, rounded=True)
    fill = max(0.04, width * min(max(percent, 0), 100) / 100)
    rect(canvas, left, top, fill, height, color or canvas.accent, rounded=True)


def motif(canvas: Canvas) -> None:
    """Low-frequency identity layer for dark cover/close pages."""
    page_metrics = canvas.p
    rect(canvas, 0, 0, 0.16, page_metrics.h, canvas.accent)
    rect(
        canvas,
        page_metrics.w - 2.05,
        0.28,
        1.42,
        1.42,
        canvas.c.dark_hairline,
        rounded=True,
    )
    rect(
        canvas,
        page_metrics.w - 1.7,
        page_metrics.h - 1.55,
        1.08,
        1.08,
        canvas.c.dark_hairline,
        rounded=True,
    )


def chart_base(canvas: Canvas, spec: ChartSpec, left, top, width, height) -> None:
    title_band = 0.28 if spec.title else 0.04
    if spec.title:
        textbox(
            canvas,
            spec.title,
            left,
            top,
            width,
            0.24,
            11,
            canvas.muted,
            bold=True,
        )
    data = CategoryChartData()
    data.categories = spec.categories
    for series in spec.series:
        data.add_series(series.name, series.values)
    frame = canvas.slide.shapes.add_chart(
        CHART_TYPES[spec.chart_type],
        Inches(left),
        Inches(top + title_band),
        Inches(max(width, 0.8)),
        Inches(max(height - title_band, 0.8)),
        data,
    )
    chart = frame.chart
    chart.has_legend = len(spec.series) > 1
    if chart.has_legend:
        chart.legend.include_in_layout = False
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        try:
            chart.legend.font.size = Pt(9)
            chart.legend.font.color.rgb = rgb(canvas.muted)
        except (ValueError, AttributeError):
            pass
    chart.has_title = False
    palette = [canvas.c.accent, canvas.c.positive, canvas.c.caution, canvas.c.ink2]
    for index, series in enumerate(chart.series):
        color = palette[index % len(palette)]
        if spec.chart_type in {ChartType.COLUMN, ChartType.BAR, ChartType.AREA}:
            series.format.fill.solid()
            series.format.fill.fore_color.rgb = rgb(color)
            series.format.line.fill.background()
        else:
            try:
                series.format.line.color.rgb = rgb(color)
                series.format.line.width = Pt(2.0)
                series.smooth = False
                series.marker.style = XL_MARKER_STYLE.CIRCLE
                series.marker.size = 6
                series.marker.format.fill.solid()
                series.marker.format.fill.fore_color.rgb = rgb(color)
                series.marker.format.line.fill.background()
            except ValueError:
                series.format.fill.solid()
                series.format.fill.fore_color.rgb = rgb(color)
    try:
        if spec.chart_type in {ChartType.COLUMN, ChartType.BAR}:
            chart.plots[0].gap_width = 70
    except (IndexError, ValueError, AttributeError):
        pass
    try:
        _consulting_value_axis(chart.value_axis, canvas)
        _consulting_category_axis(chart.category_axis, canvas, len(spec.categories))
    except (ValueError, AttributeError):
        pass
    _strip_chart_chrome(chart)


def _consulting_value_axis(axis, canvas: Canvas) -> None:
    axis.has_minor_gridlines = False
    axis.has_major_gridlines = True
    try:
        axis.major_tick_mark = XL_TICK_MARK.NONE
        axis.minor_tick_mark = XL_TICK_MARK.NONE
    except (ValueError, AttributeError):
        pass
    _chart_ticks(axis, canvas)
    _axis_line(axis, None)
    _style_gridlines(axis, canvas.hairline_color)


def _consulting_category_axis(axis, canvas: Canvas, n_cats: int) -> None:
    axis.has_major_gridlines = False
    axis.has_minor_gridlines = False
    try:
        axis.major_tick_mark = XL_TICK_MARK.NONE
        axis.minor_tick_mark = XL_TICK_MARK.NONE
    except (ValueError, AttributeError):
        pass
    _chart_ticks(axis, canvas)
    _axis_line(axis, canvas.hairline_color)
    if n_cats > 8:
        skip = max(1, (n_cats + 7) // 8)
        node = axis._element.find(qn("c:tickLblSkip"))
        if node is None:
            node = etree.SubElement(axis._element, qn("c:tickLblSkip"))
        node.set("val", str(skip))


def _chart_ticks(axis, canvas: Canvas) -> None:
    labels = axis.tick_labels
    labels.font.size = Pt(9)
    labels.font.color.rgb = rgb(canvas.muted)
    labels.font.name = canvas.f.num
    tx_pr = axis._element.find(qn("c:txPr"))
    if tx_pr is None:
        return
    body_pr = tx_pr.find(qn("a:bodyPr"))
    if body_pr is None:
        body_pr = etree.Element(qn("a:bodyPr"))
        tx_pr.insert(0, body_pr)
    body_pr.set("rot", "0")
    body_pr.set("vert", "horz")
    for def_rpr in tx_pr.iter(qn("a:defRPr")):
        _typeface(def_rpr, canvas.f.num, canvas.f.cn)


def _typeface(r_pr, latin: str, east: str) -> None:
    for tag, typeface in (("a:latin", latin), ("a:ea", east), ("a:cs", latin)):
        element = r_pr.find(qn(tag))
        if element is None:
            element = etree.SubElement(r_pr, qn(tag))
        element.set("typeface", typeface)


def _axis_line(axis, color: str | None) -> None:
    sp_pr = axis._element.find(qn("c:spPr"))
    if sp_pr is None:
        sp_pr = etree.SubElement(axis._element, qn("c:spPr"))
    for line in sp_pr.findall(qn("a:ln")):
        sp_pr.remove(line)
    line = etree.SubElement(sp_pr, qn("a:ln"))
    if color is None:
        etree.SubElement(line, qn("a:noFill"))
        return
    line.set("w", "6350")
    fill = etree.SubElement(line, qn("a:solidFill"))
    srgb = etree.SubElement(fill, qn("a:srgbClr"))
    srgb.set("val", color.lstrip("#").upper())


def _style_gridlines(axis, color: str) -> None:
    grid = axis._element.find(qn("c:majorGridlines"))
    if grid is None:
        grid = etree.SubElement(axis._element, qn("c:majorGridlines"))
    _hairline_stroke(grid, color)


def _hairline_stroke(parent, color: str) -> None:
    sp_pr = parent.find(qn("c:spPr"))
    if sp_pr is None:
        sp_pr = etree.SubElement(parent, qn("c:spPr"))
    for line in sp_pr.findall(qn("a:ln")):
        sp_pr.remove(line)
    line = etree.SubElement(sp_pr, qn("a:ln"))
    line.set("w", "6350")
    fill = etree.SubElement(line, qn("a:solidFill"))
    srgb = etree.SubElement(fill, qn("a:srgbClr"))
    srgb.set("val", color.lstrip("#").upper())


def _strip_chart_chrome(chart) -> None:
    space = getattr(chart, "_chartSpace", None)
    if space is None:
        return
    _sp_pr_no_fill(space)
    style = space.find(qn("c:style"))
    if style is not None:
        style.set("val", "1")
    plot = space.find(qn("c:chart"))
    if plot is None:
        return
    area = plot.find(qn("c:plotArea"))
    if area is not None:
        _sp_pr_no_fill(area)


def _sp_pr_no_fill(parent) -> None:
    sp_pr = parent.find(qn("c:spPr"))
    if sp_pr is None:
        sp_pr = etree.SubElement(parent, qn("c:spPr"))
    for tag in ("a:solidFill", "a:noFill", "a:gradFill", "a:pattFill"):
        for node in sp_pr.findall(qn(tag)):
            sp_pr.remove(node)
    etree.SubElement(sp_pr, qn("a:noFill"))
    for line in sp_pr.findall(qn("a:ln")):
        sp_pr.remove(line)
    line = etree.SubElement(sp_pr, qn("a:ln"))
    etree.SubElement(line, qn("a:noFill"))


def speaker_notes(slide, page: StoryPage) -> None:
    notes = page.speaker_notes or page.takeaway or page.title
    frame = slide.notes_slide.notes_text_frame
    frame.text = notes
