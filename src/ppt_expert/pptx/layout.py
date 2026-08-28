from __future__ import annotations

from dataclasses import dataclass

from ppt_expert.models import KPIItem, LayoutScheme, StoryPage
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
_VLINE_FIGURES = {"_column_claims", "_plus_claims", "_lead_claims"}
_HLINE_FIGURES = {"_plus_claims", "_rule_rows", "_timeline_h"}


@dataclass
class ChartRail:
    chart: tuple[float, float, float, float] | None
    rail: tuple[float, float, float, float]
    divider: str


def scheme_of(canvas: Canvas) -> LayoutScheme:
    return canvas.tokens.layout_scheme


def _pick(drawers: list, page: StoryPage | None, salt: int):
    if not drawers:
        raise ValueError("no layout drawers")
    number = page.number if page is not None else 1
    extra = len(page.content) if page is not None else 0
    chosen = drawers[(number * 5 + extra + salt) % len(drawers)]
    return chosen


def chart_rail(canvas: Canvas, top: float, *, has_chart: bool, page: StoryPage | None = None) -> ChartRail:
    page_metrics = canvas.p
    inner = page_metrics.w - 2 * page_metrics.mx
    band_h = page_metrics.implication_y - top - 0.22
    mx = page_metrics.mx
    if not has_chart:
        return ChartRail(None, (mx, top, inner, band_h), "none")
    kinds = _chart_kinds(scheme_of(canvas))
    kind = _pick(kinds, page, 11)
    canvas.figure = kind
    if kind == "stack":
        chart_h = band_h * 0.56
        return ChartRail(
            (mx, top, inner, chart_h - 0.1),
            (mx, top + chart_h, inner, band_h - chart_h),
            "none",
        )
    if kind == "rail_right":
        rail_w = inner * 0.38
        gap = 0.28
        return ChartRail(
            (mx + rail_w + gap, top, inner - rail_w - gap, band_h),
            (mx, top, rail_w, band_h),
            "none",
        )
    chart_w = inner * 0.58
    gap = 0.24 if scheme_of(canvas) != LayoutScheme.RULES else 0.28
    divider = "vline" if scheme_of(canvas) == LayoutScheme.RULES else "none"
    return ChartRail(
        (mx, top, chart_w, band_h),
        (mx + chart_w + gap, top, inner - chart_w - gap, band_h),
        divider,
    )


def _chart_kinds(scheme: LayoutScheme) -> list[str]:
    if scheme == LayoutScheme.BANNER:
        return ["stack", "rail_left"]
    if scheme == LayoutScheme.SPINE:
        return ["rail_right", "stack", "rail_left"]
    if scheme == LayoutScheme.SPREAD:
        return ["rail_left", "rail_right"]
    return ["rail_left", "stack", "rail_right"]


def fill_claims(
    canvas: Canvas,
    items: list[str],
    left,
    top,
    width,
    height,
    write_claim,
    *,
    page: StoryPage | None = None,
    grid: bool = False,
) -> None:
    items = items[:4] or [""]
    drawers = _claim_drawers(scheme_of(canvas), len(items), width, grid)
    drawer = _pick(drawers, page, 7 if grid else 0)
    canvas.figure = drawer.__name__
    drawer(canvas, items, left, top, width, height, write_claim)


def fill_kpis(
    canvas: Canvas,
    kpis: list[KPIItem],
    left,
    top,
    width,
    height,
    *,
    page: StoryPage | None = None,
) -> None:
    if not kpis:
        return
    drawers = _kpi_drawers(scheme_of(canvas), len(kpis))
    if canvas.figure in _VLINE_FIGURES or canvas.figure in _HLINE_FIGURES:
        quiet = [item for item in drawers if item.__name__ not in {"_kpi_split", "_kpi_hairline"}]
        drawers = quiet or drawers[:1]
    drawer = _pick(drawers, page, 13)
    drawer(canvas, kpis, left, top, width, height)


def fill_scenarios(canvas: Canvas, columns, left, top, width, height, *, page: StoryPage | None = None) -> None:
    drawers = _scenario_drawers(scheme_of(canvas), len(columns))
    drawer = _pick(drawers, page, 17)
    canvas.figure = drawer.__name__
    drawer(canvas, columns, left, top, width, height)


def _claim_drawers(scheme: LayoutScheme, n: int, width: float, grid: bool) -> list:
    if width < 5.0:
        return {
            LayoutScheme.STACK: [_stack_claims],
            LayoutScheme.BANNER: [_banner_claims],
            LayoutScheme.SPINE: [_spine_claims],
            LayoutScheme.BLOCKS: [_stack_blocks],
        }.get(scheme, [_rule_rows])
    if scheme == LayoutScheme.RULES:
        options = [_column_claims, _rule_rows]
        if n >= 3:
            options.append(_lead_claims)
        if n == 4:
            options = [_plus_claims, *options] if grid else [*options, _plus_claims]
        return options
    if scheme == LayoutScheme.STACK:
        options = [_stack_claims]
        if n >= 2:
            options.extend([_pair_panels, _featured_stack])
        if n >= 3:
            options.append(_mosaic_panels)
        return options
    if scheme == LayoutScheme.BANNER:
        options = [_banner_claims]
        if n >= 2:
            options.extend([_pair_banners, _hero_banner])
        if n >= 3:
            options.append(_stamp_row)
        return options
    if scheme == LayoutScheme.BLOCKS:
        options = [_block_row]
        if n >= 2:
            options.append(_hero_block)
        if n >= 3:
            options.append(_mosaic_blocks)
        if n == 4:
            options.append(_block_grid)
        return options
    if scheme == LayoutScheme.SPREAD:
        options = [_spread_asym, _spread_quote]
        if n >= 2:
            options.append(_spread_two)
        if n == 4:
            options.append(_spread_grid)
        return options
    options = [_spine_claims]
    if n >= 2:
        options.extend([_timeline_h, _spine_split])
    if n >= 3:
        options.append(_spine_pair)
    return options


def _kpi_drawers(scheme: LayoutScheme, _count: int) -> list:
    if scheme == LayoutScheme.STACK:
        return [_kpi_tiles, _kpi_band]
    if scheme == LayoutScheme.BANNER:
        return [_kpi_band, _kpi_type]
    if scheme == LayoutScheme.BLOCKS:
        return [_kpi_loud, _kpi_tiles]
    if scheme == LayoutScheme.SPINE:
        return [_kpi_nodes, _kpi_type]
    if scheme == LayoutScheme.SPREAD:
        return [_kpi_type, _kpi_hairline]
    return [_kpi_type, _kpi_hairline, _kpi_split]


def _scenario_drawers(scheme: LayoutScheme, n: int) -> list:
    if scheme == LayoutScheme.SPINE:
        return [_spine_scenarios, _timeline_scenarios]
    if scheme in {LayoutScheme.STACK, LayoutScheme.BANNER}:
        return [_row_scenarios, _pair_scenarios] if n >= 2 else [_row_scenarios]
    if scheme == LayoutScheme.BLOCKS:
        return [_block_scenarios, _hero_scenarios]
    return [_rule_scenarios, _row_scenarios]


def _column_claims(canvas, items, left, top, width, height, write_claim) -> None:
    col_w = width / len(items)
    for index, item in enumerate(items):
        x = left + index * col_w
        if index:
            vline(canvas, x, top + 0.08, height - 0.2)
        mini_label(canvas, f"{index + 1:02d}", x + 0.18, top + 0.06, col_w - 0.36, canvas.muted)
        write_claim(item, x + 0.18, top + 0.36, col_w - 0.4, height - 0.5)


def _plus_claims(canvas, items, left, top, width, height, write_claim) -> None:
    col_w, row_h = width / 2, height / 2
    hairline(canvas, left, top + row_h, width)
    vline(canvas, left + col_w, top + 0.06, height - 0.12)
    cells = [(0, 0), (1, 0), (0, 1), (1, 1)]
    for index, item in enumerate(items[:4]):
        column, row = cells[index]
        x = left + column * col_w
        y = top + row * row_h
        mini_label(canvas, f"{index + 1:02d}", x + 0.18, y + 0.12, col_w - 0.36, canvas.muted)
        write_claim(item, x + 0.18, y + 0.4, col_w - 0.4, row_h - 0.58)


def _rule_rows(canvas, items, left, top, width, height, write_claim) -> None:
    row_h = height / len(items)
    for index, item in enumerate(items):
        y = top + index * row_h
        if index:
            hairline(canvas, left, y, width)
        mini_label(canvas, f"{index + 1:02d}", left, y + 0.08, 0.7, canvas.muted)
        write_claim(item, left + 0.8, y + 0.08, width - 0.9, row_h - 0.16)


def _lead_claims(canvas, items, left, top, width, height, write_claim) -> None:
    lead_w = width * 0.56
    gap = 0.18
    rail_x = left + lead_w + gap
    rail_w = width - lead_w - gap
    mini_label(canvas, "01", left, top + 0.06, lead_w, canvas.muted)
    write_claim(items[0], left, top + 0.36, lead_w - 0.1, height - 0.44)
    vline(canvas, left + lead_w + gap / 2, top + 0.08, height - 0.16)
    rest = items[1:]
    row_h = height / max(len(rest), 1)
    for index, item in enumerate(rest):
        y = top + index * row_h
        mini_label(canvas, f"{index + 2:02d}", rail_x, y + 0.06, 0.6, canvas.muted)
        write_claim(item, rail_x, y + 0.32, rail_w, row_h - 0.36)


def _stack_claims(canvas, items, left, top, width, height, write_claim) -> None:
    gap = 0.08
    row_h = (height - gap * (len(items) - 1)) / len(items)
    for index, item in enumerate(items):
        y = top + index * (row_h + gap)
        panel(canvas, left, y, width, row_h, accent_bar="left")
        mini_label(canvas, f"{index + 1:02d}", left + 0.2, y + 0.08, 0.7, canvas.muted)
        write_claim(item, left + 0.2, y + 0.3, width - 0.4, row_h - 0.38)


def _pair_panels(canvas, items, left, top, width, height, write_claim) -> None:
    gap = 0.12
    cols = 2
    rows = 2 if len(items) > 2 else 1
    col_w = (width - gap) / cols
    row_h = (height - gap * (rows - 1)) / rows
    for index, item in enumerate(items):
        column, row = index % cols, index // cols
        x = left + column * (col_w + gap)
        y = top + row * (row_h + gap)
        panel(canvas, x, y, col_w, row_h, accent_bar="left")
        mini_label(canvas, f"{index + 1:02d}", x + 0.14, y + 0.08, 0.6, canvas.muted)
        write_claim(item, x + 0.14, y + 0.32, col_w - 0.28, row_h - 0.42)


def _featured_stack(canvas, items, left, top, width, height, write_claim) -> None:
    hero_h = height * 0.38
    rect(canvas, left, top, width, hero_h, canvas.accent)
    mini_label(canvas, "01", left + 0.2, top + 0.1, 0.6, _WHITE)
    write_claim(items[0], left + 0.2, top + 0.36, width - 0.4, hero_h - 0.44, ink=_WHITE, body=_WHITE)
    rest_h = height - hero_h - 0.12
    if items[1:]:
        _stack_claims(canvas, items[1:], left, top + hero_h + 0.12, width, rest_h, write_claim)


def _mosaic_panels(canvas, items, left, top, width, height, write_claim) -> None:
    lead_w = width * 0.42
    gap = 0.14
    panel(canvas, left, top, lead_w, height, accent_bar="top")
    mini_label(canvas, "01", left + 0.16, top + 0.12, lead_w - 0.3, canvas.muted)
    write_claim(items[0], left + 0.16, top + 0.4, lead_w - 0.32, height - 0.56)
    _stack_claims(
        canvas,
        items[1:],
        left + lead_w + gap,
        top,
        width - lead_w - gap,
        height,
        write_claim,
    )


def _banner_claims(canvas, items, left, top, width, height, write_claim) -> None:
    gap = 0.1
    row_h = (height - gap * (len(items) - 1)) / len(items)
    for index, item in enumerate(items):
        y = top + index * (row_h + gap)
        _one_banner(canvas, item, left, y, width, row_h, index, write_claim)


def _one_banner(canvas, item, left, top, width, height, index, write_claim) -> None:
    rect(canvas, left, top, width, height, canvas.surface)
    rect(canvas, left, top, 0.14, height, canvas.accent)
    rect(canvas, left + 0.28, top + 0.12, 0.36, 0.36, canvas.accent, rounded=True)
    mini_label(canvas, f"{index + 1:02d}", left + 0.28, top + 0.16, 0.36, _WHITE)
    write_claim(item, left + 0.78, top + 0.1, width - 0.96, height - 0.2)


def _pair_banners(canvas, items, left, top, width, height, write_claim) -> None:
    gap = 0.14
    col_w = (width - gap) / 2
    rows = (len(items) + 1) // 2
    row_h = (height - gap * (rows - 1)) / rows
    for index, item in enumerate(items):
        x = left + (index % 2) * (col_w + gap)
        y = top + (index // 2) * (row_h + gap)
        _one_banner(canvas, item, x, y, col_w, row_h, index, write_claim)


def _hero_banner(canvas, items, left, top, width, height, write_claim) -> None:
    hero_h = height * 0.4
    rect(canvas, left, top, width, hero_h, canvas.accent)
    mini_label(canvas, "01", left + 0.22, top + 0.12, 0.6, _WHITE)
    write_claim(items[0], left + 0.22, top + 0.4, width - 0.44, hero_h - 0.5, ink=_WHITE, body=_WHITE)
    rest_h = height - hero_h - 0.12
    if items[1:]:
        _banner_claims(canvas, items[1:], left, top + hero_h + 0.12, width, rest_h, write_claim)


def _stamp_row(canvas, items, left, top, width, height, write_claim) -> None:
    col_w = width / len(items)
    hairline(canvas, left, top + 0.55, width)
    for index, item in enumerate(items):
        x = left + index * col_w
        rect(canvas, x + col_w / 2 - 0.22, top + 0.08, 0.44, 0.44, canvas.accent, rounded=True)
        mini_label(canvas, f"{index + 1:02d}", x + col_w / 2 - 0.22, top + 0.16, 0.44, _WHITE)
        write_claim(item, x + 0.08, top + 0.7, col_w - 0.16, height - 0.8)


def _block_row(canvas, items, left, top, width, height, write_claim) -> None:
    gap = 0.16
    col_w = (width - gap * (len(items) - 1)) / len(items)
    for index, item in enumerate(items):
        _loud_block(canvas, item, left + index * (col_w + gap), top, col_w, height, index, write_claim)


def _block_grid(canvas, items, left, top, width, height, write_claim) -> None:
    gap = 0.16
    col_w, row_h = (width - gap) / 2, (height - gap) / 2
    cells = [(0, 0), (1, 0), (0, 1), (1, 1)]
    for index, item in enumerate(items[:4]):
        column, row = cells[index]
        _loud_block(
            canvas,
            item,
            left + column * (col_w + gap),
            top + row * (row_h + gap),
            col_w,
            row_h,
            index,
            write_claim,
        )


def _loud_block(canvas, item, left, top, width, height, index, write_claim) -> None:
    fill = canvas.accent if index == 0 else canvas.surface
    rect(canvas, left, top, width, height, fill)
    ink = _WHITE if index == 0 else canvas.ink
    muted = _WHITE if index == 0 else canvas.muted
    mini_label(canvas, f"{index + 1:02d}", left + 0.16, top + 0.12, width - 0.32, muted)
    write_claim(item, left + 0.16, top + 0.4, width - 0.32, height - 0.56, ink=ink, body=ink)


def _hero_block(canvas, items, left, top, width, height, write_claim) -> None:
    lead_w = width * 0.55
    gap = 0.16
    _loud_block(canvas, items[0], left, top, lead_w, height, 0, write_claim)
    rest_x = left + lead_w + gap
    rest_w = width - lead_w - gap
    rest = items[1:]
    row_h = (height - 0.12 * (len(rest) - 1)) / max(len(rest), 1)
    for index, item in enumerate(rest):
        _loud_block(canvas, item, rest_x, top + index * (row_h + 0.12), rest_w, row_h, index + 1, write_claim)


def _mosaic_blocks(canvas, items, left, top, width, height, write_claim) -> None:
    lead_w = width * 0.38
    gap = 0.16
    _loud_block(canvas, items[0], left, top, lead_w, height, 0, write_claim)
    _block_row(
        canvas,
        items[1:],
        left + lead_w + gap,
        top,
        width - lead_w - gap,
        height,
        write_claim,
    )


def _stack_blocks(canvas, items, left, top, width, height, write_claim) -> None:
    gap = 0.1
    row_h = (height - gap * (len(items) - 1)) / len(items)
    for index, item in enumerate(items):
        _loud_block(canvas, item, left, top + index * (row_h + gap), width, row_h, index, write_claim)


def _spread_asym(canvas, items, left, top, width, height, write_claim) -> None:
    gutter = 0.32
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


def _spread_two(canvas, items, left, top, width, height, write_claim) -> None:
    gutter = 0.36
    col_w = (width - gutter) / 2
    left_items = items[::2]
    right_items = items[1::2]
    _rule_rows(canvas, left_items, left, top, col_w, height, write_claim)
    _rule_rows(canvas, right_items or [items[-1]], left + col_w + gutter, top, col_w, height, write_claim)


def _spread_quote(canvas, items, left, top, width, height, write_claim) -> None:
    quote_h = height * 0.42
    mini_label(canvas, "01", left, top, width, canvas.muted)
    write_claim(items[0], left, top + 0.28, width, quote_h - 0.36)
    hairline(canvas, left, top + quote_h, width)
    if items[1:]:
        _spread_asym(canvas, items[1:], left, top + quote_h + 0.16, width, height - quote_h - 0.16, write_claim)


def _spread_grid(canvas, items, left, top, width, height, write_claim) -> None:
    gutter = 0.32
    col_w, row_h = (width - gutter) / 2, (height - gutter) / 2
    cells = [(0, 0), (1, 0), (0, 1), (1, 1)]
    for index, item in enumerate(items[:4]):
        column, row = cells[index]
        x = left + column * (col_w + gutter)
        y = top + row * (row_h + gutter)
        mini_label(canvas, f"{index + 1:02d}", x, y + 0.06, col_w, canvas.muted)
        write_claim(item, x, y + 0.32, col_w, row_h - 0.4)


def _spine_claims(canvas, items, left, top, width, height, write_claim) -> None:
    rect(canvas, left + 0.08, top + 0.06, 0.05, height - 0.12, canvas.accent)
    row_h = height / len(items)
    for index, item in enumerate(items):
        y = top + index * row_h
        rect(canvas, left + 0.04, y + 0.12, 0.13, 0.13, canvas.accent, rounded=True)
        mini_label(canvas, f"{index + 1:02d}", left + 0.28, y + 0.08, 0.6, canvas.muted)
        write_claim(item, left + 0.28, y + 0.32, width - 0.4, row_h - 0.4)


def _timeline_h(canvas, items, left, top, width, height, write_claim) -> None:
    hairline(canvas, left, top + 0.42, width)
    col_w = width / len(items)
    for index, item in enumerate(items):
        x = left + index * col_w
        rect(canvas, x + col_w / 2 - 0.08, top + 0.34, 0.16, 0.16, canvas.accent, rounded=True)
        mini_label(canvas, f"{index + 1:02d}", x + 0.08, top + 0.58, col_w - 0.16, canvas.muted)
        write_claim(item, x + 0.08, top + 0.86, col_w - 0.16, height - 0.94)


def _spine_split(canvas, items, left, top, width, height, write_claim) -> None:
    half = width * 0.5
    _spine_claims(canvas, items[:-1] or items[:1], left, top, half - 0.16, height, write_claim)
    mini_label(canvas, f"{len(items):02d}", left + half, top + 0.1, width - half, canvas.muted)
    write_claim(items[-1], left + half, top + 0.4, width - half, height - 0.5)


def _spine_pair(canvas, items, left, top, width, height, write_claim) -> None:
    rect(canvas, left + width / 2 - 0.025, top + 0.06, 0.05, height - 0.12, canvas.accent)
    gap = 0.4
    col_w = (width - gap) / 2
    left_items = items[::2]
    right_items = items[1::2]
    _rule_rows(canvas, left_items, left, top, col_w, height, write_claim)
    _rule_rows(canvas, right_items or [items[-1]], left + col_w + gap, top, col_w, height, write_claim)


def _kpi_split(canvas, kpis, left, top, width, height) -> None:
    hairline(canvas, left, top - 0.1, width)
    cell = width / len(kpis)
    for index, item in enumerate(kpis):
        x = left + index * cell
        if index:
            vline(canvas, x, top + 0.08, height - 0.2)
        stat_card(canvas, item, x + 0.12, top, cell - 0.2, height)


def _kpi_hairline(canvas, kpis, left, top, width, height) -> None:
    hairline(canvas, left, top - 0.08, width)
    _kpi_type(canvas, kpis, left, top, width, height)


def _kpi_type(canvas, kpis, left, top, width, height) -> None:
    gap = 0.28
    cell = (width - gap * (len(kpis) - 1)) / len(kpis)
    for index, item in enumerate(kpis):
        stat_card(canvas, item, left + index * (cell + gap), top, cell, height)


def _kpi_tiles(canvas, kpis, left, top, width, height) -> None:
    gap = 0.12
    cell = (width - gap * (len(kpis) - 1)) / len(kpis)
    for index, item in enumerate(kpis):
        x = left + index * (cell + gap)
        panel(canvas, x, top, cell, height, accent_bar="top")
        stat_card(canvas, item, x + 0.1, top + 0.06, cell - 0.2, height - 0.1)


def _kpi_band(canvas, kpis, left, top, width, height) -> None:
    rect(canvas, left, top, width, height, canvas.surface)
    rect(canvas, left, top, 0.14, height, canvas.accent)
    cell = (width - 0.28) / len(kpis)
    for index, item in enumerate(kpis):
        stat_card(canvas, item, left + 0.28 + index * cell, top + 0.08, cell - 0.1, height - 0.16)


def _kpi_loud(canvas, kpis, left, top, width, height) -> None:
    gap = 0.14
    cell = (width - gap * (len(kpis) - 1)) / len(kpis)
    for index, item in enumerate(kpis):
        x = left + index * (cell + gap)
        fill = canvas.accent if index == 0 else canvas.surface
        rect(canvas, x, top, cell, height, fill)
        ink = _WHITE if index == 0 else canvas.ink
        muted = _WHITE if index == 0 else canvas.muted
        token(canvas, item.value, x + 0.1, top + 0.12, cell - 0.2, 0.5, 26, ink)
        mini_label(canvas, item.label, x + 0.1, top + 0.7, cell - 0.2, muted)


def _kpi_nodes(canvas, kpis, left, top, width, height) -> None:
    rect(canvas, left, top + 0.08, 0.05, height - 0.16, canvas.accent)
    cell = (width - 0.28) / len(kpis)
    for index, item in enumerate(kpis):
        stat_card(canvas, item, left + 0.28 + index * cell, top, cell - 0.08, height)


def _rule_scenarios(canvas, columns, left, top, width, height) -> None:
    gap = 0.14
    col_w = (width - gap * (len(columns) - 1)) / max(len(columns), 1)
    for index, column in enumerate(columns):
        x = left + index * (col_w + gap)
        if column.featured:
            rect(canvas, x, top, col_w, height, canvas.accent)
            ink, muted = _WHITE, canvas.c.dark_muted
        else:
            if index:
                vline(canvas, x - gap / 2, top + 0.1, height - 0.2)
            ink, muted = canvas.ink, canvas.muted
        _scenario_body(canvas, column, x + 0.14, top + 0.16, col_w - 0.28, height - 0.28, ink=ink, muted=muted)


def _row_scenarios(canvas, columns, left, top, width, height) -> None:
    gap = 0.1
    row_h = (height - gap * (len(columns) - 1)) / max(len(columns), 1)
    scheme = scheme_of(canvas)
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


def _pair_scenarios(canvas, columns, left, top, width, height) -> None:
    gap = 0.14
    col_w = (width - gap) / 2
    rows = (len(columns) + 1) // 2
    row_h = (height - gap * (rows - 1)) / rows
    for index, column in enumerate(columns):
        x = left + (index % 2) * (col_w + gap)
        y = top + (index // 2) * (row_h + gap)
        panel(canvas, x, y, col_w, row_h, accent_bar="left")
        _scenario_body(canvas, column, x + 0.16, y + 0.12, col_w - 0.32, row_h - 0.24)


def _block_scenarios(canvas, columns, left, top, width, height) -> None:
    gap = 0.16
    col_w = (width - gap * (len(columns) - 1)) / max(len(columns), 1)
    for index, column in enumerate(columns):
        x = left + index * (col_w + gap)
        fill = canvas.accent if column.featured or index == 0 else canvas.surface
        rect(canvas, x, top, col_w, height, fill)
        ink = _WHITE if fill == canvas.accent else canvas.ink
        muted = _WHITE if fill == canvas.accent else canvas.muted
        _scenario_body(canvas, column, x + 0.14, top + 0.16, col_w - 0.28, height - 0.28, ink=ink, muted=muted)


def _hero_scenarios(canvas, columns, left, top, width, height) -> None:
    lead = next((item for item in columns if item.featured), columns[0])
    rest = [item for item in columns if item is not lead]
    lead_w = width * 0.42
    rect(canvas, left, top, lead_w, height, canvas.accent)
    _scenario_body(canvas, lead, left + 0.16, top + 0.16, lead_w - 0.32, height - 0.28, ink=_WHITE, muted=_WHITE)
    if rest:
        _block_scenarios(canvas, rest, left + lead_w + 0.16, top, width - lead_w - 0.16, height)


def _spine_scenarios(canvas, columns, left, top, width, height) -> None:
    rect(canvas, left + 0.08, top + 0.06, 0.05, height - 0.12, canvas.accent)
    row_h = height / max(len(columns), 1)
    for index, column in enumerate(columns):
        y = top + index * row_h
        rect(canvas, left + 0.04, y + 0.1, 0.13, 0.13, canvas.accent, rounded=True)
        _scenario_body(canvas, column, left + 0.32, y + 0.08, width - 0.4, row_h - 0.16)


def _timeline_scenarios(canvas, columns, left, top, width, height) -> None:
    hairline(canvas, left, top + 0.4, width)
    col_w = width / max(len(columns), 1)
    for index, column in enumerate(columns):
        x = left + index * col_w
        rect(canvas, x + col_w / 2 - 0.08, top + 0.32, 0.16, 0.16, canvas.accent, rounded=True)
        _scenario_body(canvas, column, x + 0.1, top + 0.58, col_w - 0.2, height - 0.66)


def _scenario_body(canvas, column, left, top, width, height, *, ink: str | None = None, muted: str | None = None) -> None:
    from ppt_expert.pptx.primitives import textbox

    ink = ink or canvas.ink
    muted = muted or canvas.muted
    textbox(canvas, column.name, left, top, width, 0.32, 16, ink, bold=True)
    token(canvas, column.probability, left, top + 0.34, width, 0.26, 13, muted)
    body = "\n".join(part for part in (column.trigger, column.outcome, column.implication) if part)
    textbox(canvas, body, left, top + 0.64, width, max(height - 0.7, 0.4), 13, ink)
