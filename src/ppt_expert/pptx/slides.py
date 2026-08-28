from __future__ import annotations

from pptx.util import Inches, Pt

from ppt_expert.models import PageRole, StoryPage
from ppt_expert.pptx.primitives import (
    Canvas,
    chart_base,
    footer,
    header,
    implication,
    mini_label,
    motif,
    panel,
    rect,
    stat_card,
    textbox,
    token,
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
        width = (inner - 0.24 * (len(kpis) - 1)) / len(kpis)
        for index, item in enumerate(kpis):
            stat_card(
                canvas,
                item,
                page_metrics.mx + index * (width + 0.24),
                4.15,
                width,
                1.55,
            )
    implication(canvas, page.takeaway)


def overview(canvas: Canvas, page: StoryPage) -> None:
    top = header(canvas, page)
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    items = page.content[:4]
    count = max(1, len(items))
    gap = 0.16
    width = (inner - gap * (count - 1)) / count
    height = 2.6 if page.kpis else 3.4
    for index, item in enumerate(items):
        left = page_metrics.mx + index * (width + gap)
        panel(canvas, left, top, width, height)
        mini_label(canvas, f"{index + 1:02d}", left + 0.16, top + 0.12, width - 0.28)
        _claim(canvas, item, left + 0.16, top + 0.38, width - 0.28, height - 0.5)
    if page.kpis:
        k_w = (inner - 0.16 * (len(page.kpis[:4]) - 1)) / len(page.kpis[:4])
        for index, item in enumerate(page.kpis[:4]):
            stat_card(
                canvas,
                item,
                page_metrics.mx + index * (k_w + 0.16),
                top + height + 0.18,
                k_w,
                1.45,
            )
    implication(canvas, page.takeaway)


def context(canvas: Canvas, page: StoryPage) -> None:
    top = header(canvas, page)
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    chart_w = inner * 0.62
    if page.chart:
        chart_base(canvas, page.chart, page_metrics.mx, top, chart_w, 4.35)
    rail_left = page_metrics.mx + chart_w + 0.18
    rail_w = inner - chart_w - 0.18
    y = top
    if page.takeaway:
        panel(canvas, rail_left, y, rail_w, 1.25, accent_bar="top")
        textbox(
            canvas,
            page.takeaway,
            rail_left + 0.14,
            y + 0.16,
            rail_w - 0.28,
            0.95,
            14,
            canvas.ink,
            bold=True,
        )
        y += 1.37
    remaining = list(page.content[:4])
    for index, item in enumerate(remaining):
        h = min(1.05, page_metrics.content_bottom - y)
        if h < 0.7:
            textbox(
                canvas,
                " · ".join(remaining[index:]),
                rail_left + 0.08,
                min(y, page_metrics.content_bottom - 0.4),
                rail_w - 0.16,
                0.38,
                12,
                canvas.ink2,
            )
            break
        panel(canvas, rail_left, y, rail_w, h)
        _claim(canvas, item, rail_left + 0.14, y + 0.1, rail_w - 0.28, h - 0.16)
        y += h + 0.1


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
    items = page.content[:4]
    count = max(1, len(items))
    if count == 4:
        cells = [(0, 0), (1, 0), (0, 1), (1, 1)]
        cols, rows = 2, 2
    else:
        cells = [(index, 0) for index in range(count)]
        cols, rows = count, 1
    gap = 0.16
    col_w = (inner - gap * (cols - 1)) / cols
    row_h = min(2.45 if rows == 2 else 3.35, (page_metrics.implication_y - top - 0.2 - gap * (rows - 1)) / rows)
    for index, item in enumerate(items):
        column, row = cells[index]
        left = page_metrics.mx + column * (col_w + gap)
        card_top = top + row * (row_h + gap)
        panel(canvas, left, card_top, col_w, row_h)
        mini_label(canvas, f"{index + 1:02d}", left + 0.16, card_top + 0.1, col_w - 0.28)
        _claim(canvas, item, left + 0.16, card_top + 0.34, col_w - 0.28, row_h - 0.46)
    implication(canvas, page.takeaway)


def scenario(canvas: Canvas, page: StoryPage) -> None:
    top = header(canvas, page)
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    columns = page.scenarios[:4] or []
    if not columns:
        expansion(canvas, page)
        return
    gap = 0.14
    width = (inner - gap * (len(columns) - 1)) / len(columns)
    copy_h = 0.46 if page.content else 0.0
    height = page_metrics.implication_y - top - 0.18 - copy_h
    for index, column in enumerate(columns):
        left = page_metrics.mx + index * (width + gap)
        fill = canvas.c.accent if column.featured else canvas.surface
        ink = "#FFFFFF" if column.featured else canvas.ink
        muted = canvas.c.dark_muted if column.featured else canvas.muted
        rect(canvas, left, top, width, height, fill, rounded=True)
        textbox(canvas, column.name, left + 0.14, top + 0.16, width - 0.28, 0.36, 16, ink, bold=True)
        token(canvas, column.probability, left + 0.14, top + 0.54, width - 0.28, 0.3, 13, muted)
        body = "\n".join(part for part in (column.trigger, column.outcome, column.implication) if part)
        textbox(canvas, body, left + 0.14, top + 0.96, width - 0.28, height - 1.15, 13, ink)
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
        panel(canvas, page_metrics.mx, y, inner, 0.7)
        textbox(canvas, item, page_metrics.mx + 0.2, y + 0.16, inner - 0.4, 0.42, 16, canvas.ink)
        y += 0.82
    if page.milestones:
        from ppt_expert.pptx.primitives import hairline

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


def _claim(canvas: Canvas, item: str, left, top, width, height) -> None:
    colon = item.find("：")
    if colon < 0:
        colon = item.find(":")
    if colon < 1 or colon > 18:
        textbox(canvas, item, left, top, width, height, 13, canvas.ink)
        return
    label, rest = item[: colon + 1], item[colon + 1 :]
    textbox(canvas, label, left, top, width, 0.32, 15, canvas.ink, bold=True)
    risk_at = rest.find("风险")
    if risk_at < 0:
        textbox(canvas, rest, left, top + 0.34, width, height - 0.36, 13, canvas.ink2)
        return
    textbox(canvas, rest[:risk_at], left, top + 0.34, width, max(0.4, height - 0.82), 13, canvas.ink2)
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

    from ppt_expert.pptx.primitives import _apply_fonts, rgb

    cell.text = text
    cell.fill.solid()
    cell.fill.fore_color.rgb = rgb(fill)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    for paragraph in cell.text_frame.paragraphs:
        paragraph.font.size = Pt(12)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = rgb(color)
        for run in paragraph.runs:
            _apply_fonts(run, canvas.f.num if any(ch.isdigit() for ch in text) else canvas.f.cn, canvas.f.cn)
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
