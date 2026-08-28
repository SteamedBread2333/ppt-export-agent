from __future__ import annotations

from dataclasses import dataclass

from ppt_expert.models import KPIItem, LayoutScheme
from ppt_expert.pptx.primitives import (
    Canvas,
    hairline,
    mini_label,
    panel,
    rect,
    stat_card,
    token,
    vline,
)

_WHITE = "#FFFFFF"


@dataclass
class ChartRail:
    chart: tuple[float, float, float, float] | None
    rail: tuple[float, float, float, float]
    divider: str


def scheme_of(canvas: Canvas) -> LayoutScheme:
    return canvas.tokens.layout_scheme


def chart_rail(canvas: Canvas, top: float, *, has_chart: bool) -> ChartRail:
    page = canvas.p
    inner = page.w - 2 * page.mx
    band_h = page.implication_y - top - 0.22
    mx = page.mx
    if not has_chart:
        return ChartRail(None, (mx, top, inner, band_h), "none")
    scheme = scheme_of(canvas)
    if scheme == LayoutScheme.BANNER:
        chart_h = band_h * 0.58
        return ChartRail(
            (mx, top, inner, chart_h - 0.1),
            (mx, top + chart_h, inner, band_h - chart_h),
            "none",
        )
    if scheme == LayoutScheme.SPINE:
        rail_w = inner * 0.38
        gap = 0.28
        return ChartRail(
            (mx + rail_w + gap, top, inner - rail_w - gap, band_h),
            (mx, top, rail_w, band_h),
            "none",
        )
    if scheme == LayoutScheme.SPREAD:
        chart_w = inner * 0.52
        gap = 0.36
        return ChartRail(
            (mx, top, chart_w, band_h),
            (mx + chart_w + gap, top, inner - chart_w - gap, band_h),
            "none",
        )
    if scheme in {LayoutScheme.STACK, LayoutScheme.BLOCKS}:
        chart_w = inner * 0.58
        gap = 0.22
        return ChartRail(
            (mx, top, chart_w, band_h),
            (mx + chart_w + gap, top, inner - chart_w - gap, band_h),
            "none",
        )
    chart_w = inner * 0.6
    gap = 0.28
    return ChartRail(
        (mx, top, chart_w, band_h),
        (mx + chart_w + gap, top, inner - chart_w - gap, band_h),
        "vline",
    )


def fill_claims(canvas: Canvas, items: list[str], left, top, width, height, write_claim, *, grid: bool = False) -> None:
    items = items[:4] or [""]
    scheme = scheme_of(canvas)
    if scheme == LayoutScheme.STACK:
        _stack_claims(canvas, items, left, top, width, height, write_claim)
    elif scheme == LayoutScheme.BANNER:
        _banner_claims(canvas, items, left, top, width, height, write_claim)
    elif scheme == LayoutScheme.BLOCKS:
        _block_claims(canvas, items, left, top, width, height, write_claim, grid=grid)
    elif scheme == LayoutScheme.SPREAD:
        _spread_claims(canvas, items, left, top, width, height, write_claim, grid=grid)
    elif scheme == LayoutScheme.SPINE:
        _spine_claims(canvas, items, left, top, width, height, write_claim)
    else:
        _rules_claims(canvas, items, left, top, width, height, write_claim, grid=grid)


def fill_kpis(canvas: Canvas, kpis: list[KPIItem], left, top, width, height) -> None:
    if not kpis:
        return
    scheme = scheme_of(canvas)
    count = len(kpis)
    if scheme == LayoutScheme.STACK:
        gap = 0.12
        cell = (width - gap * (count - 1)) / count
        for index, item in enumerate(kpis):
            x = left + index * (cell + gap)
            panel(canvas, x, top, cell, height, accent_bar="top")
            stat_card(canvas, item, x + 0.1, top + 0.06, cell - 0.2, height - 0.1)
        return
    if scheme == LayoutScheme.BANNER:
        rect(canvas, left, top, width, height, canvas.surface)
        rect(canvas, left, top, 0.14, height, canvas.accent)
        cell = (width - 0.28) / count
        for index, item in enumerate(kpis):
            stat_card(canvas, item, left + 0.28 + index * cell, top + 0.08, cell - 0.1, height - 0.16)
        return
    if scheme == LayoutScheme.BLOCKS:
        gap = 0.14
        cell = (width - gap * (count - 1)) / count
        for index, item in enumerate(kpis):
            x = left + index * (cell + gap)
            fill = canvas.accent if index == 0 else canvas.surface
            rect(canvas, x, top, cell, height, fill)
            ink = _WHITE if index == 0 else canvas.ink
            muted = _WHITE if index == 0 else canvas.muted
            token(canvas, item.value, x + 0.1, top + 0.12, cell - 0.2, 0.5, 26, ink)
            mini_label(canvas, item.label, x + 0.1, top + 0.7, cell - 0.2, muted)
        return
    if scheme == LayoutScheme.SPINE:
        rect(canvas, left, top + 0.08, 0.05, height - 0.16, canvas.accent)
        cell = (width - 0.28) / count
        for index, item in enumerate(kpis):
            stat_card(canvas, item, left + 0.28 + index * cell, top, cell - 0.08, height)
        return
    if scheme == LayoutScheme.SPREAD:
        gap = 0.32
        cell = (width - gap * (count - 1)) / count
        for index, item in enumerate(kpis):
            stat_card(canvas, item, left + index * (cell + gap), top, cell, height)
        return
    hairline(canvas, left, top - 0.1, width)
    cell = width / count
    for index, item in enumerate(kpis):
        x = left + index * cell
        if index:
            vline(canvas, x, top + 0.08, height - 0.2)
        stat_card(canvas, item, x + 0.12, top, cell - 0.2, height)


def fill_scenarios(canvas: Canvas, columns, left, top, width, height) -> None:
    count = max(len(columns), 1)
    scheme = scheme_of(canvas)
    if scheme == LayoutScheme.SPINE:
        _spine_scenarios(canvas, columns, left, top, width, height)
        return
    if scheme in {LayoutScheme.STACK, LayoutScheme.BANNER}:
        gap = 0.1
        row_h = (height - gap * (count - 1)) / count
        for index, column in enumerate(columns):
            y = top + index * (row_h + gap)
            if scheme == LayoutScheme.BANNER:
                rect(canvas, left, y, width, row_h, canvas.surface)
                rect(canvas, left, y, 0.14, row_h, canvas.accent)
                inset = 0.28
            else:
                panel(canvas, left, y, width, row_h, accent_bar="left")
                inset = 0.2
            _scenario_body(canvas, column, left + inset, y + 0.1, width - inset - 0.16, row_h - 0.2)
        return
    gap = 0.16 if scheme in {LayoutScheme.BLOCKS, LayoutScheme.SPREAD} else 0.14
    col_w = (width - gap * (count - 1)) / count
    for index, column in enumerate(columns):
        x = left + index * (col_w + gap)
        featured = column.featured
        if scheme == LayoutScheme.BLOCKS:
            fill = canvas.accent if featured else canvas.surface
            rect(canvas, x, top, col_w, height, fill)
            ink = _WHITE if featured else canvas.ink
            muted = _WHITE if featured else canvas.muted
        elif scheme == LayoutScheme.SPREAD:
            if featured:
                rect(canvas, x, top, col_w, 0.08, canvas.accent)
            ink, muted = canvas.ink, canvas.muted
        else:
            if featured:
                rect(canvas, x, top, col_w, height, canvas.accent)
                ink, muted = _WHITE, canvas.c.dark_muted
            else:
                if index:
                    vline(canvas, x - gap / 2, top + 0.1, height - 0.2)
                ink, muted = canvas.ink, canvas.muted
        _scenario_body(canvas, column, x + 0.14, top + 0.16, col_w - 0.28, height - 0.28, ink=ink, muted=muted)


def _rules_claims(canvas, items, left, top, width, height, write_claim, *, grid: bool) -> None:
    if grid and len(items) == 4:
        col_w, row_h = width / 2, height / 2
        hairline(canvas, left, top + row_h, width)
        vline(canvas, left + col_w, top + 0.06, height - 0.12)
        cells = [(0, 0), (1, 0), (0, 1), (1, 1)]
        for index, item in enumerate(items):
            column, row = cells[index]
            x = left + column * col_w
            y = top + row * row_h
            mini_label(canvas, f"{index + 1:02d}", x + 0.18, y + 0.12, col_w - 0.36, canvas.muted)
            write_claim(item, x + 0.18, y + 0.4, col_w - 0.4, row_h - 0.58)
        return
    col_w = width / len(items)
    for index, item in enumerate(items):
        x = left + index * col_w
        if index:
            vline(canvas, x, top + 0.08, height - 0.2)
        mini_label(canvas, f"{index + 1:02d}", x + 0.18, top + 0.06, col_w - 0.36, canvas.muted)
        write_claim(item, x + 0.18, top + 0.36, col_w - 0.4, height - 0.5)


def _stack_claims(canvas, items, left, top, width, height, write_claim) -> None:
    gap = 0.08
    row_h = (height - gap * (len(items) - 1)) / len(items)
    for index, item in enumerate(items):
        y = top + index * (row_h + gap)
        panel(canvas, left, y, width, row_h, accent_bar="left")
        mini_label(canvas, f"{index + 1:02d}", left + 0.2, y + 0.08, 0.7, canvas.muted)
        write_claim(item, left + 0.2, y + 0.3, width - 0.4, row_h - 0.38)


def _banner_claims(canvas, items, left, top, width, height, write_claim) -> None:
    gap = 0.1
    row_h = (height - gap * (len(items) - 1)) / len(items)
    for index, item in enumerate(items):
        y = top + index * (row_h + gap)
        rect(canvas, left, y, width, row_h, canvas.surface)
        rect(canvas, left, y, 0.14, row_h, canvas.accent)
        rect(canvas, left + 0.28, y + 0.12, 0.36, 0.36, canvas.accent, rounded=True)
        mini_label(canvas, f"{index + 1:02d}", left + 0.28, y + 0.16, 0.36, _WHITE)
        write_claim(item, left + 0.78, y + 0.1, width - 0.96, row_h - 0.2)


def _block_claims(canvas, items, left, top, width, height, write_claim, *, grid: bool) -> None:
    gap = 0.16
    if grid and len(items) == 4:
        col_w, row_h = (width - gap) / 2, (height - gap) / 2
        cells = [(0, 0), (1, 0), (0, 1), (1, 1)]
        for index, item in enumerate(items):
            column, row = cells[index]
            x = left + column * (col_w + gap)
            y = top + row * (row_h + gap)
            _loud_block(canvas, item, x, y, col_w, row_h, index, write_claim)
        return
    col_w = (width - gap * (len(items) - 1)) / len(items)
    for index, item in enumerate(items):
        x = left + index * (col_w + gap)
        _loud_block(canvas, item, x, top, col_w, height, index, write_claim)


def _loud_block(canvas, item, left, top, width, height, index, write_claim) -> None:
    fill = canvas.accent if index == 0 else canvas.surface
    rect(canvas, left, top, width, height, fill)
    ink = _WHITE if index == 0 else canvas.ink
    muted = _WHITE if index == 0 else canvas.muted
    mini_label(canvas, f"{index + 1:02d}", left + 0.16, top + 0.12, width - 0.32, muted)
    write_claim(item, left + 0.16, top + 0.4, width - 0.32, height - 0.56, ink=ink, body=ink)


def _spread_claims(canvas, items, left, top, width, height, write_claim, *, grid: bool) -> None:
    gutter = 0.32
    if grid and len(items) == 4:
        col_w, row_h = (width - gutter) / 2, (height - gutter) / 2
        cells = [(0, 0), (1, 0), (0, 1), (1, 1)]
        for index, item in enumerate(items):
            column, row = cells[index]
            x = left + column * (col_w + gutter)
            y = top + row * (row_h + gutter)
            mini_label(canvas, f"{index + 1:02d}", x, y + 0.06, col_w, canvas.muted)
            write_claim(item, x, y + 0.32, col_w, row_h - 0.4)
        return
    if len(items) == 3:
        lead = (width - 2 * gutter) * 0.42
        rest = (width - 2 * gutter - lead) / 2
        widths = [lead, rest, rest]
    else:
        widths = [(width - gutter * (len(items) - 1)) / len(items)] * len(items)
    x = left
    for index, item in enumerate(items):
        col_w = widths[index]
        mini_label(canvas, f"{index + 1:02d}", x, top + 0.04, col_w, canvas.muted)
        write_claim(item, x, top + 0.32, col_w, height - 0.4)
        x += col_w + gutter


def _spine_claims(canvas, items, left, top, width, height, write_claim) -> None:
    rect(canvas, left + 0.08, top + 0.06, 0.05, height - 0.12, canvas.accent)
    row_h = height / len(items)
    for index, item in enumerate(items):
        y = top + index * row_h
        rect(canvas, left + 0.04, y + 0.12, 0.13, 0.13, canvas.accent, rounded=True)
        mini_label(canvas, f"{index + 1:02d}", left + 0.28, y + 0.08, 0.6, canvas.muted)
        write_claim(item, left + 0.28, y + 0.32, width - 0.4, row_h - 0.4)


def _spine_scenarios(canvas, columns, left, top, width, height) -> None:
    rect(canvas, left + 0.08, top + 0.06, 0.05, height - 0.12, canvas.accent)
    row_h = height / max(len(columns), 1)
    for index, column in enumerate(columns):
        y = top + index * row_h
        rect(canvas, left + 0.04, y + 0.1, 0.13, 0.13, canvas.accent, rounded=True)
        _scenario_body(canvas, column, left + 0.32, y + 0.08, width - 0.4, row_h - 0.16)


def _scenario_body(canvas, column, left, top, width, height, *, ink: str | None = None, muted: str | None = None) -> None:
    from ppt_expert.pptx.primitives import textbox

    ink = ink or canvas.ink
    muted = muted or canvas.muted
    textbox(canvas, column.name, left, top, width, 0.32, 16, ink, bold=True)
    token(canvas, column.probability, left, top + 0.34, width, 0.26, 13, muted)
    body = "\n".join(part for part in (column.trigger, column.outcome, column.implication) if part)
    textbox(canvas, body, left, top + 0.64, width, max(height - 0.7, 0.4), 13, ink)
