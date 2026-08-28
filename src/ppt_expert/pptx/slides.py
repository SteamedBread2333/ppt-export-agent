from __future__ import annotations

from pptx.util import Inches, Pt

from ppt_expert.models import PageRole, StoryPage
from ppt_expert.pptx.layout import chart_rail, fill_claims, fill_kpis, fill_scenarios
from ppt_expert.pptx.primitives import (
    Canvas,
    chart_base,
    footer,
    hairline,
    header,
    implication,
    mini_label,
    motif,
    panel,
    rect,
    textbox,
    token,
    vline,
)


def compose_slide(canvas: Canvas, page: StoryPage, image_path: str | None = None) -> None:
    role = page.resolved_role()
    if role == PageRole.COVER:
        cover(canvas, page, image_path)
    elif role == PageRole.OVERVIEW:
        overview(canvas, page)
    elif role == PageRole.CONTEXT:
        context(canvas, page)
    elif role == PageRole.EVIDENCE:
        evidence(canvas, page)
    elif role == PageRole.STRUCTURE:
        structure(canvas, page)
    elif role == PageRole.EXPANSION:
        expansion(canvas, page)
    elif role == PageRole.SCENARIO:
        scenario(canvas, page)
    else:
        close(canvas, page)
    footer(canvas, page)


def cover(canvas: Canvas, page: StoryPage, image_path: str | None = None) -> None:
    motif(canvas)
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    mini_label(
        canvas,
        page.eyebrow or "BRIEFING",
        page_metrics.mx,
        1.15,
        inner,
        canvas.accent,
    )
    textbox(
        canvas,
        page.title,
        page_metrics.mx,
        1.5,
        inner * 0.78,
        1.35,
        32,
        canvas.ink,
        bold=True,
    )
    y = 3.0
    if page.subtitle:
        textbox(canvas, page.subtitle, page_metrics.mx, y, inner * 0.72, 0.42, 16, canvas.ink2)
        y = 3.44
    textbox(canvas, " · ".join(page.content), page_metrics.mx, y, inner * 0.72, 0.55, 16, canvas.ink2)
    if image_path:
        canvas.slide.shapes.add_picture(
            image_path, Inches(9.35), Inches(1.55), Inches(3.15), Inches(2.15)
        )
    kpis = page.kpis[:3]
    if kpis:
        fill_kpis(canvas, kpis, page_metrics.mx, 4.12, inner, 1.45, page=page)
    implication(canvas, page.takeaway)


def overview(canvas: Canvas, page: StoryPage) -> None:
    top = header(canvas, page)
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    items = page.content[:4]
    height = 2.35 if page.kpis else 3.55
    fill_claims(canvas, items, page_metrics.mx, top, inner, height, _on_claim(canvas), page=page)
    if page.kpis:
        fill_kpis(
            canvas,
            page.kpis[:4],
            page_metrics.mx,
            top + height + 0.22,
            inner,
            1.28,
            page=page,
        )
    implication(canvas, page.takeaway)


def context(canvas: Canvas, page: StoryPage) -> None:
    top = header(canvas, page)
    split = chart_rail(canvas, top, has_chart=bool(page.chart), page=page)
    if page.chart and split.chart:
        chart_base(canvas, page.chart, *split.chart)
    if split.divider == "vline":
        rail_left, rail_top, _rail_w, rail_h = split.rail
        vline(canvas, rail_left - 0.16, rail_top + 0.06, rail_h - 0.12)
    rail_left, rail_top, rail_w, rail_h = split.rail
    y = rail_top
    if page.takeaway:
        take_h = min(1.05, rail_h * 0.28)
        textbox(
            canvas,
            page.takeaway,
            rail_left,
            y,
            rail_w,
            take_h - 0.08,
            16,
            canvas.ink,
            bold=True,
        )
        y += take_h
    remaining = list(page.content[:4])
    if remaining:
        fill_claims(
            canvas,
            remaining,
            rail_left,
            y,
            rail_w,
            max(rail_top + rail_h - y, 0.8),
            _on_claim(canvas),
            page=page,
        )


def evidence(canvas: Canvas, page: StoryPage) -> None:
    top = header(canvas, page)
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    table_h = 3.15 if page.chart else 4.2
    if page.table:
        _table(canvas, page, page_metrics.mx, top, inner, table_h)
    elif page.heatmap:
        _heatmap(canvas, page, page_metrics.mx, top, inner, table_h)
    elif page.waterfall:
        _waterfall(canvas, page, page_metrics.mx, top, inner)
    elif page.chart:
        chart_base(canvas, page.chart, page_metrics.mx, top, inner, 3.6)
    else:
        expansion(canvas, page)
        return
    if page.chart and page.table:
        chart_base(canvas, page.chart, page_metrics.mx, top + table_h + 0.12, inner * 0.48, 1.55)
        textbox(
            canvas,
            " · ".join(page.content),
            page_metrics.mx + inner * 0.5,
            top + table_h + 0.18,
            inner * 0.5,
            1.4,
            13,
            canvas.ink2,
        )
    else:
        _copy_band(canvas, page)
    implication(canvas, page.takeaway)


def structure(canvas: Canvas, page: StoryPage) -> None:
    top = header(canvas, page)
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    if page.allocation:
        items = page.allocation[:6]
        total = sum(item.percent for item in items) or 100
        cursor = page_metrics.mx
        palette = [canvas.c.accent, canvas.c.positive, canvas.c.caution, canvas.c.ink2]
        panel(canvas, page_metrics.mx, top, inner, 0.48, accent_bar=None)
        for index, item in enumerate(items):
            segment = inner * (item.percent / total)
            rect(canvas, cursor, top, max(segment, 0.04), 0.48, palette[index % len(palette)])
            cursor += segment
        for index, item in enumerate(items):
            y = top + 0.7 + index * 0.62
            rect(canvas, page_metrics.mx, y + 0.12, 0.2, 0.2, palette[index % len(palette)], rounded=True)
            textbox(
                canvas,
                f"{item.label}  {item.percent:.0f}%",
                page_metrics.mx + 0.36,
                y,
                7.4,
                0.3,
                16,
                canvas.ink,
                bold=True,
                numeric=True,
            )
            textbox(
                canvas,
                item.note or page.content[min(index, len(page.content) - 1)],
                page_metrics.mx + 0.36,
                y + 0.28,
                inner - 0.4,
                0.26,
                12,
                canvas.muted,
            )
    elif page.chart and page.chart_secondary:
        half = (inner - 0.16) / 2
        chart_base(canvas, page.chart, page_metrics.mx, top, half, 3.5)
        chart_base(canvas, page.chart_secondary, page_metrics.mx + half + 0.16, top, half, 3.5)
        textbox(
            canvas,
            " · ".join(page.content),
            page_metrics.mx,
            top + 3.65,
            inner,
            1.1,
            14,
            canvas.ink2,
        )
    else:
        expansion(canvas, page)
        return
    _copy_band(canvas, page)
    implication(canvas, page.takeaway)


def expansion(canvas: Canvas, page: StoryPage) -> None:
    top = header(canvas, page)
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    fill_claims(
        canvas,
        page.content[:4],
        page_metrics.mx,
        top,
        inner,
        page_metrics.implication_y - top - 0.18,
        _on_claim(canvas),
        page=page,
        grid=True,
    )
    implication(canvas, page.takeaway)


def scenario(canvas: Canvas, page: StoryPage) -> None:
    top = header(canvas, page)
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    columns = page.scenarios[:4] or []
    if not columns:
        expansion(canvas, page)
        return
    copy_h = 0.46 if page.content else 0.0
    height = page_metrics.implication_y - top - 0.18 - copy_h
    fill_scenarios(canvas, columns, page_metrics.mx, top, inner, height, page=page)
    if page.content:
        _copy_band(canvas, page, page_metrics.implication_y - 0.62)
    implication(canvas, page.takeaway)


def close(canvas: Canvas, page: StoryPage) -> None:
    motif(canvas)
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    mini_label(canvas, page.eyebrow or "NEXT STEP", page_metrics.mx, 1.35, inner, canvas.accent)
    textbox(canvas, page.title, page_metrics.mx, 1.75, inner, 1.15, 30, canvas.ink, bold=True)
    y = 3.15
    for item in page.content:
        textbox(canvas, item, page_metrics.mx, y, inner, 0.5, 18, canvas.ink)
        y += 0.62
    if page.milestones:
        hairline(canvas, page_metrics.mx, 5.08, inner)
        span = inner / max(len(page.milestones[:4]), 1)
        for index, item in enumerate(page.milestones[:4]):
            x = page_metrics.mx + index * span
            rect(canvas, x + span / 2 - 0.08, 5.0, 0.16, 0.16, canvas.accent, rounded=True)
            textbox(canvas, item.date or item.label, x, 5.22, span - 0.08, 0.24, 11, canvas.accent, bold=True)
            textbox(canvas, item.note or item.label, x, 5.46, span - 0.08, 0.42, 12, canvas.ink2)
    implication(canvas, page.takeaway)


def _copy_band(canvas: Canvas, page: StoryPage, top: float | None = None) -> None:
    if not page.content:
        return
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    y = page_metrics.implication_y - 0.62 if top is None else top
    textbox(
        canvas,
        " · ".join(page.content),
        page_metrics.mx,
        y,
        inner,
        0.5,
        13,
        canvas.ink2,
    )


def _on_claim(canvas: Canvas):
    def write(item, left, top, width, height, **colors):
        _claim(canvas, item, left, top, width, height, **colors)

    return write


def _claim(
    canvas: Canvas,
    item: str,
    left,
    top,
    width,
    height,
    *,
    ink: str | None = None,
    body: str | None = None,
) -> None:
    ink = ink or canvas.ink
    body = body or canvas.ink2
    colon = item.find("：")
    if colon < 0:
        colon = item.find(":")
    if colon < 1 or colon > 18:
        textbox(canvas, item, left, top, width, height, 15, ink)
        return
    label, rest = item[: colon + 1], item[colon + 1 :]
    textbox(canvas, label, left, top, width, 0.36, 16, ink, bold=True)
    risk_at = rest.find("风险")
    if risk_at < 0:
        textbox(canvas, rest, left, top + 0.4, width, height - 0.42, 14, body)
        return
    textbox(canvas, rest[:risk_at], left, top + 0.4, width, max(0.4, height - 0.88), 13, body)
    textbox(
        canvas,
        rest[risk_at:],
        left,
        top + height - 0.4,
        width,
        0.36,
        12,
        canvas.c.risk if not canvas.dark else canvas.accent,
    )


def _table(canvas: Canvas, page: StoryPage, left, top, width, height) -> None:
    spec = page.table
    rows = 1 + len(spec.rows)
    cols = len(spec.headers)
    table = canvas.slide.shapes.add_table(
        rows, cols, Inches(left), Inches(top), Inches(width), Inches(height)
    ).table
    for index, header_text in enumerate(spec.headers):
        _cell(canvas, table.cell(0, index), header_text, canvas.c.accent, "#FFFFFF", True)
    for row_index, row in enumerate(spec.rows, 1):
        fill = canvas.c.positive if spec.highlight_row == row_index - 1 else canvas.surface
        ink = "#FFFFFF" if spec.highlight_row == row_index - 1 else canvas.ink
        for col_index, value in enumerate(row):
            _cell(canvas, table.cell(row_index, col_index), value if col_index < len(row) else "", fill, ink, False)


def _cell(canvas: Canvas, cell, text: str, fill: str, color: str, bold: bool) -> None:
    from pptx.enum.text import MSO_ANCHOR

    from ppt_expert.pptx.primitives import _apply_fonts, _apply_paragraph_font, rgb

    cell.text = text
    cell.fill.solid()
    cell.fill.fore_color.rgb = rgb(fill)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    latin = canvas.f.num if any(ch.isdigit() for ch in text) else canvas.f.cn
    for paragraph in cell.text_frame.paragraphs:
        paragraph.font.size = Pt(12)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = rgb(color)
        _apply_paragraph_font(paragraph, latin, canvas.f.cn)
        for run in paragraph.runs:
            _apply_fonts(run, latin, canvas.f.cn)
            run.font.size = Pt(12)
            run.font.bold = bold
            run.font.color.rgb = rgb(color)


def _heatmap(canvas: Canvas, page: StoryPage, left, top, width, height) -> None:
    spec = page.heatmap
    rows = 1 + len(spec.rows)
    cols = 1 + len(spec.columns)
    table = canvas.slide.shapes.add_table(
        rows, cols, Inches(left), Inches(top), Inches(width), Inches(height)
    ).table
    _cell(canvas, table.cell(0, 0), "", canvas.surface, canvas.ink, False)
    for index, header_text in enumerate(spec.columns, 1):
        _cell(canvas, table.cell(0, index), header_text, canvas.c.accent, "#FFFFFF", True)
    for row_index, label in enumerate(spec.rows, 1):
        _cell(canvas, table.cell(row_index, 0), label, canvas.surface, canvas.ink, True)
        values = spec.values[row_index - 1] if row_index - 1 < len(spec.values) else []
        for col_index in range(1, cols):
            value = values[col_index - 1] if col_index - 1 < len(values) else 0
            fill = canvas.c.accent if value >= 0.66 else (canvas.c.caution if value >= 0.33 else canvas.surface)
            color = "#FFFFFF" if fill != canvas.surface else canvas.ink
            _cell(canvas, table.cell(row_index, col_index), f"{value:.1f}", fill, color, False)


def _waterfall(canvas: Canvas, page: StoryPage, left, top, width) -> None:
    items = page.waterfall[:7]
    span = max(width / max(len(items), 1) - 0.12, 0.4)
    peak = max((abs(item.value) for item in items), default=1) or 1
    running = 0.0
    for index, item in enumerate(items):
        x = left + index * (span + 0.12)
        if item.total:
            running = item.value
            bar_h = 2.8 * abs(item.value) / peak
            y = top + 3.0 - bar_h
            color = canvas.accent
        else:
            start = running
            running += item.value
            bar_h = 2.8 * abs(item.value) / peak
            baseline = top + 3.0 - 2.8 * max(start, 0) / peak if item.value >= 0 else top + 3.0 - 2.8 * running / peak
            y = max(top, min(baseline, top + 3.0 - bar_h))
            color = canvas.c.positive if item.value >= 0 else canvas.c.risk
        rect(canvas, x, y, span, max(bar_h, 0.12), color, rounded=True)
        textbox(canvas, item.label, x, top + 3.12, span, 0.28, 11, canvas.ink, bold=True)
        token(canvas, f"{item.value:+.1f}" if not item.total else f"{item.value:.1f}", x, top + 3.4, span, 0.26, 11, canvas.muted)
