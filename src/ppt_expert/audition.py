from __future__ import annotations

import html
import logging
import math
from pathlib import Path

from ppt_expert.models import DesignSpec, OutlinePlan, SlideFamily, StoryPage, StyleOption

LOGGER = logging.getLogger(__name__)


def render_style_auditions(styles: list[StyleOption], outline: OutlinePlan, output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cover, analytical, close = _audition_pages(outline)
    paths: list[str] = []
    for style in styles:
        svg = _audition_svg(style, cover, analytical, close)
        paths.append(_write_preview(output_dir / f"style_{style.key}", svg, 1440, 540))
    return paths


def render_contact_sheet(pages: list[StoryPage], design: DesignSpec, output_dir: Path) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    svg = _contact_svg(pages, design)
    columns = min(3, max(1, len(pages)))
    rows = max(1, math.ceil(len(pages) / columns))
    width = 24 + columns * 480 + (columns - 1) * 16
    height = 72 + rows * 270 + (rows - 1) * 16
    return _write_preview(output_dir / "contact-sheet", svg, width, height)


def _write_preview(stem: Path, svg: str, width: int, height: int) -> str:
    svg_path = stem.with_suffix(".svg")
    png_path = stem.with_suffix(".png")
    svg_path.write_text(svg, encoding="utf-8")
    try:
        import cairosvg

        cairosvg.svg2png(
            bytestring=svg.encode("utf-8"),
            write_to=str(png_path),
            output_width=width,
            output_height=height,
        )
        return str(png_path.resolve())
    except Exception as exc:  # noqa: BLE001 - SVG remains the supported fallback
        LOGGER.warning("PNG preview unavailable; using SVG: %s", exc)
        return str(svg_path.resolve())


def _audition_pages(outline: OutlinePlan) -> tuple:
    pages = outline.pages
    cover = pages[0]
    close = pages[-1]
    analytical = cover
    if len(pages) > 2:
        analytical = max(pages[1:-1], key=lambda page: sum(len(item) for item in page.core_content))
    elif len(pages) == 2:
        analytical = pages[0]
    return cover, analytical, close


def _audition_svg(style: StyleOption, cover, analytical, close) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 540">
<rect width="1440" height="540" fill="#111111"/>
{_mini_cover(16, 48, 464, 476, style, cover.title, cover.core_content)}
{_mini_analytical(488, 48, 464, 476, style, analytical.title, analytical.core_content)}
{_mini_close(960, 48, 464, 476, style, close.title, close.core_content)}
<text x="16" y="32" font-size="14" fill="#FFFFFF" font-family="sans-serif">
{html.escape(style.key)} · {html.escape(style.name)} · cover / analytical / close</text>
</svg>"""


def _contact_svg(pages: list[StoryPage], design: DesignSpec) -> str:
    columns = min(3, max(1, len(pages)))
    rows = max(1, math.ceil(len(pages) / columns))
    width = 24 + columns * 480 + (columns - 1) * 16
    height = 72 + rows * 270 + (rows - 1) * 16
    tiles = []
    for index, page in enumerate(pages):
        column = index % columns
        row = index // columns
        left = 24 + column * 496
        top = 56 + row * 286
        tiles.append(_thumbnail(left, top, 480, 270, design, page))
    title = html.escape(design.style_name)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
<rect width="{width}" height="{height}" fill="{design.background}"/>
<text x="24" y="36" font-size="18" font-weight="700" fill="{design.text}"
 font-family="sans-serif">Contact sheet · {title}</text>
{''.join(tiles)}
</svg>"""


def _mini_cover(x, y, w, h, style: StyleOption, title: str, content: list[str]) -> str:
    line = html.escape(" · ".join(content[:2]) or title)
    return f"""<g>
{_frame(x, y, w, h, style.background, style.primary)}
<text x="{x + 28}" y="{y + 42}" font-size="11" fill="{style.accent}" font-family="sans-serif">COVER</text>
<text x="{x + 28}" y="{y + 92}" font-size="22" font-weight="700" fill="{style.text}"
 font-family="sans-serif">{html.escape(_clip(title, 36))}</text>
<text x="{x + 28}" y="{y + 128}" font-size="13" fill="{style.text}" opacity=".75"
 font-family="sans-serif">{line}</text>
{_kpi(x + 28, y + 280, style.primary, "01", "Focus")}
{_kpi(x + 168, y + 280, style.secondary, "02", "Evidence")}
{_kpi(x + 308, y + 280, style.accent, "03", "Action")}
</g>"""


def _mini_analytical(x, y, w, h, style: StyleOption, title: str, content: list[str]) -> str:
    bars = "".join(
        f'<rect x="{x + 28 + index * 42}" y="{y + 210 + (3 - index % 4) * 28}" width="28" '
        f'height="{80 + index * 18}" rx="4" fill="{style.accent if index == 3 else style.primary}"/>'
        for index in range(4)
    )
    body = html.escape(content[0] if content else title)
    return f"""<g>
{_frame(x, y, w, h, style.background, style.primary)}
<text x="{x + 28}" y="{y + 42}" font-size="11" fill="{style.accent}" font-family="sans-serif">ANALYTICAL</text>
<text x="{x + 28}" y="{y + 84}" font-size="18" font-weight="700" fill="{style.text}"
 font-family="sans-serif">{html.escape(_clip(title, 28))}</text>
<text x="{x + 28}" y="{y + 116}" font-size="12" fill="{style.text}" opacity=".75"
 font-family="sans-serif">{_clip(body, 42)}</text>
{bars}
<rect x="{x + 220}" y="{y + 180}" width="216" height="220" rx="12" fill="{style.secondary}" opacity=".35"/>
<text x="{x + 236}" y="{y + 220}" font-size="12" font-weight="700" fill="{style.text}"
 font-family="sans-serif">Interpretation</text>
<text x="{x + 236}" y="{y + 248}" font-size="12" fill="{style.text}" opacity=".8"
 font-family="sans-serif">{html.escape(_clip(content[1] if len(content) > 1 else body, 28))}</text>
</g>"""


def _mini_close(x, y, w, h, style: StyleOption, title: str, content: list[str]) -> str:
    return f"""<g>
{_frame(x, y, w, h, style.background, style.accent)}
<text x="{x + 28}" y="{y + 42}" font-size="11" fill="{style.accent}" font-family="sans-serif">CLOSE</text>
<text x="{x + 28}" y="{y + 110}" font-size="22" font-weight="700" fill="{style.text}"
 font-family="sans-serif">{html.escape(_clip(title, 32))}</text>
<text x="{x + 28}" y="{y + 160}" font-size="14" fill="{style.text}" opacity=".8"
 font-family="sans-serif">{html.escape(_clip(content[0] if content else title, 40))}</text>
</g>"""


def _thumbnail(x, y, w, h, design: DesignSpec, page: StoryPage) -> str:
    family = page.resolved_family()
    accent = design.accent if family == SlideFamily.CONCLUSION else design.primary
    kpis = ""
    if page.kpis:
        kpis = "".join(
            _kpi(x + 16 + index * 150, y + 150, design.primary, html.escape(item.value[:8]),
                 html.escape(item.label[:12]))
            for index, item in enumerate(page.kpis[:3])
        )
    chart = ""
    if page.chart is not None:
        chart = "".join(
            f'<rect x="{x + 20 + index * 36}" y="{y + 150}" width="24" height="80" rx="3" '
            f'fill="{design.accent if index == 0 else design.secondary}"/>'
            for index in range(min(6, len(page.chart.categories)))
        )
    body = html.escape(_clip(page.content[0] if page.content else page.title, 36))
    return f"""<g>
{_frame(x, y, w, h, design.background, accent)}
<text x="{x + 16}" y="{y + 28}" font-size="10" fill="{design.accent}" font-family="sans-serif">
{html.escape(family.value.replace('_', ' ').upper())} · {page.number:02d}</text>
<text x="{x + 16}" y="{y + 56}" font-size="16" font-weight="700" fill="{design.text}"
 font-family="sans-serif">{html.escape(_clip(page.title, 34))}</text>
<text x="{x + 16}" y="{y + 82}" font-size="11" fill="{design.text}" opacity=".75"
 font-family="sans-serif">{body}</text>
{kpis}{chart}
</g>"""


def _frame(x, y, w, h, fill: str, bar: str) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" '
        f'stroke="#000000" stroke-opacity=".08"/>'
        f'<rect x="{x}" y="{y}" width="8" height="{h}" rx="2" fill="{bar}"/>'
    )


def _kpi(x, y, color: str, value: str, label: str) -> str:
    return f"""<g>
<rect x="{x}" y="{y}" width="128" height="72" rx="8" fill="{color}"/>
<text x="{x + 12}" y="{y + 32}" font-size="18" font-weight="700" fill="#FFFFFF"
 font-family="sans-serif">{value}</text>
<text x="{x + 12}" y="{y + 54}" font-size="11" fill="#FFFFFF" opacity=".85"
 font-family="sans-serif">{label}</text>
</g>"""


def _clip(value: str, limit: int) -> str:
    value = value.replace("\n", " ")
    return value if len(value) <= limit else value[: limit - 1] + "…"
