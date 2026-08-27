from __future__ import annotations

import html
import logging
from pathlib import Path

from ppt_expert.models import StyleOption

LOGGER = logging.getLogger(__name__)


def render_style_cards(styles: list[StyleOption], output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for style in styles:
        svg_path = output_dir / f"style_{style.key}.svg"
        png_path = output_dir / f"style_{style.key}.png"
        svg_path.write_text(_style_svg(style), encoding="utf-8")
        paths.append(str(svg_path.resolve()))
        try:
            import cairosvg

            cairosvg.svg2png(
                bytestring=svg_path.read_bytes(),
                write_to=str(png_path),
                output_width=960,
                output_height=540,
            )
            paths[-1] = str(png_path.resolve())
        except Exception as exc:  # noqa: BLE001 - SVG remains the supported fallback
            LOGGER.warning("PNG style preview unavailable; using SVG: %s", exc)
    return paths


def _style_svg(style: StyleOption) -> str:
    name = html.escape(style.name)
    mood = html.escape(style.mood)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">
<rect width="960" height="540" fill="{style.background}"/>
<rect x="0" width="350" height="540" fill="{style.primary}"/>
<circle cx="245" cy="165" r="120" fill="{style.secondary}" opacity=".92"/>
<circle cx="110" cy="370" r="86" fill="{style.accent}" opacity=".82"/>
<rect x="405" y="78" width="92" height="12" rx="6" fill="{style.accent}"/>
<text x="405" y="155" font-size="54" font-weight="700" fill="{style.text}"
 font-family="PingFang SC, sans-serif">{style.key} · {name}</text>
<text x="405" y="215" font-size="25" fill="{style.text}" opacity=".72"
 font-family="PingFang SC, sans-serif">{mood}</text>
<rect x="405" y="305" width="88" height="88" rx="14" fill="{style.primary}"/>
<rect x="510" y="305" width="88" height="88" rx="14" fill="{style.secondary}"/>
<rect x="615" y="305" width="88" height="88" rx="14" fill="{style.accent}"/>
<rect x="720" y="305" width="88" height="88" rx="14" fill="{style.text}"/>
<text x="405" y="455" font-size="20" fill="{style.text}" opacity=".65"
 font-family="PingFang SC, sans-serif">PPT VISUAL DIRECTION</text>
</svg>"""
