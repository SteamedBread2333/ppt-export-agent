from pathlib import Path

from ppt_expert.models import OutlinePage, OutlinePlan, StyleOption
from ppt_expert.typography import build_profiles, render_specimens, select_profile


def test_recommended_profile_uses_installed_fonts() -> None:
    profiles = build_profiles()
    ids = {item.id for item in profiles}
    assert "modern_consulting" in ids
    recommended = next(item for item in profiles if item.recommended)
    selected = select_profile(profiles, "recommended")
    assert selected.id == recommended.id
    assert recommended.latin_font
    assert recommended.east_asian_font


def test_specimens_are_written(tmp_path: Path) -> None:
    outline = OutlinePlan(
        title="Demo",
        pages=[OutlinePage(number=1, title="From Idea to Presentation", core_content=["Focus"])],
    )
    style = StyleOption(
        key="A",
        name="Warm Narrative",
        mood="Warm",
        primary="#E8603C",
        secondary="#F5C24B",
        background="#FFF8F0",
        text="#3D2B1F",
        accent="#3B8C88",
    )
    profiles = build_profiles()
    paths = render_specimens(profiles, style, outline, tmp_path)
    assert paths
    assert all(Path(path).exists() for path in paths)
    assert profiles[0].specimen_path
