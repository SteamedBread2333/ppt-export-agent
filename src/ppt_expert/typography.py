from __future__ import annotations

import functools
import html
import logging
import platform
import shutil
import subprocess
from pathlib import Path

from ppt_expert.models import OutlinePlan, ReferenceAnalysis, StyleOption, TypographyProfile

LOGGER = logging.getLogger(__name__)

LATIN_SANS = ["Inter", "Aptos Display", "Aptos", "Avenir Next", "Arial"]
LATIN_SERIF = ["Source Serif 4", "Iowan Old Style", "Georgia", "Times New Roman"]
LATIN_GEO = ["Avenir Next", "SF Pro Display", "Inter", "Aptos Display", "Arial"]
CJK_SANS = [
    "Source Han Sans SC",
    "Noto Sans CJK SC",
    "HarmonyOS Sans SC",
    "MiSans",
    "PingFang SC",
    "Microsoft YaHei",
]
CJK_SERIF = ["Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", "SimSun"]
NUMERIC = ["Inter", "Aptos", "Avenir Next", "Arial"]


def build_profiles(reference: ReferenceAnalysis | None = None) -> list[TypographyProfile]:
    latin_sans, latin_ok = _pick(LATIN_SANS)
    cjk_sans, cjk_ok = _pick(CJK_SANS)
    latin_serif, serif_ok = _pick(LATIN_SERIF)
    cjk_serif, cjk_serif_ok = _pick(CJK_SERIF)
    latin_geo, geo_ok = _pick(LATIN_GEO)
    numeric, numeric_ok = _pick(NUMERIC)

    profiles = [
        TypographyProfile(
            id="modern_consulting",
            name="Modern Consulting",
            mood="Neutral, precise, high-density, strong numerals",
            latin_font=latin_sans,
            east_asian_font=cjk_sans,
            numeric_font=numeric,
            fallbacks=_fallbacks(latin_sans, cjk_sans),
            recommended=True,
            installed=latin_ok and cjk_ok and numeric_ok,
        ),
        TypographyProfile(
            id="editorial_authority",
            name="Editorial Authority",
            mood="Serif-led headlines with a restrained sans-serif body",
            latin_font=latin_serif,
            east_asian_font=cjk_serif,
            numeric_font=numeric,
            fallbacks=_fallbacks(latin_serif, cjk_serif, cjk_sans),
            installed=serif_ok and cjk_serif_ok,
        ),
        TypographyProfile(
            id="executive_technology",
            name="Executive Technology",
            mood="Geometric display type with a highly legible body",
            latin_font=latin_geo,
            east_asian_font=cjk_sans,
            numeric_font=numeric,
            fallbacks=_fallbacks(latin_geo, cjk_sans),
            installed=geo_ok and cjk_ok,
        ),
    ]
    if reference and (reference.title_font or reference.body_font):
        title = reference.title_font or cjk_sans
        body = reference.body_font or title
        profiles.append(
            TypographyProfile(
                id="template_brand",
                name="Template / Brand",
                mood="Typography inherited from the approved source",
                latin_font=title,
                east_asian_font=body,
                numeric_font=title,
                fallbacks=_fallbacks(title, body, latin_sans, cjk_sans),
                recommended=True,
                installed=font_is_installed(title) and font_is_installed(body),
            )
        )
        profiles[0] = profiles[0].model_copy(update={"recommended": False})
    if not any(item.recommended for item in profiles):
        profiles[0] = profiles[0].model_copy(update={"recommended": True})
    return profiles


def select_profile(
    profiles: list[TypographyProfile], choice: object
) -> TypographyProfile:
    payload = choice if isinstance(choice, dict) else {"profile": str(choice)}
    action = str(payload.get("action", "use")).strip().lower()
    if action == "custom":
        latin = str(payload.get("latin_font") or "").strip()
        east_asian = str(payload.get("east_asian_font") or latin).strip()
        numeric = str(payload.get("numeric_font") or latin).strip()
        if not latin or not east_asian:
            raise ValueError("custom typography requires latin_font and east_asian_font")
        return TypographyProfile(
            id="custom",
            name="Custom",
            mood="User-specified type stack",
            latin_font=latin,
            east_asian_font=east_asian,
            numeric_font=numeric or latin,
            fallbacks=_fallbacks(latin, east_asian),
            installed=font_is_installed(latin) and font_is_installed(east_asian),
        )
    key = str(payload.get("profile") or payload.get("id") or "recommended").strip().lower()
    key = key.replace("-", "_").replace(" ", "_")
    if key in {"recommended", "use", "default", "a"}:
        return next((item for item in profiles if item.recommended), profiles[0])
    for item in profiles:
        if item.id == key or item.name.casefold().replace(" ", "_") == key:
            return item
    raise ValueError("typography choice must be a known profile id or recommended")


def render_specimens(
    profiles: list[TypographyProfile],
    style: StyleOption,
    outline: OutlinePlan,
    output_dir: Path,
) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    headline = outline.pages[0].title if outline.pages else "Strategy outlook"
    body = (
        outline.pages[0].core_content[0]
        if outline.pages and outline.pages[0].core_content
        else "One assertion, supported by evidence."
    )
    paths: list[str] = []
    rendered: list[TypographyProfile] = []
    for profile in profiles:
        svg_path = output_dir / f"type_{profile.id}.svg"
        png_path = output_dir / f"type_{profile.id}.png"
        svg_path.write_text(
            _specimen_svg(profile, style, headline, body), encoding="utf-8"
        )
        chosen = str(svg_path.resolve())
        try:
            import cairosvg

            cairosvg.svg2png(
                bytestring=svg_path.read_bytes(),
                write_to=str(png_path),
                output_width=960,
                output_height=540,
            )
            chosen = str(png_path.resolve())
        except Exception as exc:  # noqa: BLE001 - SVG remains the supported fallback
            LOGGER.warning("PNG typography preview unavailable; using SVG: %s", exc)
        paths.append(chosen)
        rendered.append(profile.model_copy(update={"specimen_path": chosen}))
    profiles[:] = rendered
    return paths


def font_is_installed(font_family: str) -> bool:
    return _font_key(font_family) in _installed_catalog()


def _pick(candidates: list[str]) -> tuple[str, bool]:
    for name in candidates:
        if font_is_installed(name):
            return name, True
    return candidates[-1], False


def _fallbacks(*families: str) -> list[str]:
    seen: list[str] = []
    for family in families:
        for item in (family, "Arial", "Microsoft YaHei"):
            if item not in seen:
                seen.append(item)
    return seen[1:] if len(seen) > 1 else seen


@functools.lru_cache(maxsize=1)
def _installed_catalog() -> set[str]:
    names: set[str] = set()
    fc_list = shutil.which("fc-list")
    if fc_list:
        result = subprocess.run(
            [fc_list, ":", "family"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                for family in line.split(","):
                    key = _font_key(family)
                    if key:
                        names.add(key)
    font_dirs = [
        Path.home() / "Library/Fonts",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
        Path("C:/Windows/Fonts"),
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
    ]
    for directory in font_dirs:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file():
                key = _font_key(path.stem)
                if key:
                    names.add(key)
    if platform.system() == "Darwin":
        names.update({"pingfang", "avenirnext", "arial", "songti", "stheitimedium"})
    return names


def _font_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum()).removesuffix(
        "sc"
    )


def _specimen_svg(
    profile: TypographyProfile, style: StyleOption, headline: str, body: str
) -> str:
    stack = html.escape(f"{profile.latin_font}, {profile.east_asian_font}, sans-serif")
    name = html.escape(profile.name)
    mood = html.escape(profile.mood)
    title = html.escape(headline)
    copy = html.escape(body)
    mark = "RECOMMENDED" if profile.recommended else ("INSTALLED" if profile.installed else "FALLBACK")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540">
<rect width="960" height="540" fill="{style.background}"/>
<rect x="0" y="0" width="18" height="540" fill="{style.primary}"/>
<text x="56" y="62" font-size="13" letter-spacing="3" fill="{style.accent}"
 font-family="{stack}">{html.escape(mark)}</text>
<text x="56" y="118" font-size="36" font-weight="700" fill="{style.text}"
 font-family="{stack}">{name}</text>
<text x="56" y="156" font-size="16" fill="{style.text}" opacity=".72"
 font-family="{stack}">{mood}</text>
<text x="56" y="250" font-size="28" font-weight="700" fill="{style.primary}"
 font-family="{stack}">{title}</text>
<text x="56" y="298" font-size="18" fill="{style.text}"
 font-family="{stack}">{copy}</text>
<text x="56" y="390" font-size="40" font-weight="700" fill="{style.primary}"
 font-family="{stack}">36.8%</text>
<text x="56" y="424" font-size="14" fill="{style.text}" opacity=".7"
 font-family="{stack}">Allocation · 配置权重 · 2026H2</text>
<text x="56" y="500" font-size="13" fill="{style.text}" opacity=".55"
 font-family="{stack}">{html.escape(profile.latin_font)} + {html.escape(profile.east_asian_font)}</text>
<rect x="720" y="360" width="88" height="88" rx="14" fill="{style.primary}"/>
<rect x="820" y="360" width="88" height="88" rx="14" fill="{style.accent}"/>
</svg>"""
