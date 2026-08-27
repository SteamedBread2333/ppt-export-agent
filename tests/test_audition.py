from pathlib import Path

from ppt_expert.audition import render_contact_sheet, render_style_auditions
from ppt_expert.models import (
    DesignSpec,
    KPIItem,
    LayoutType,
    OutlinePage,
    OutlinePlan,
    SlideFamily,
    StoryPage,
    StyleOption,
)


def test_style_audition_writes_four_previews(tmp_path: Path) -> None:
    outline = OutlinePlan(
        title="Demo",
        pages=[
            OutlinePage(number=1, title="Open", core_content=["Start"]),
            OutlinePage(number=2, title="Evidence", core_content=["Measure twice"]),
            OutlinePage(number=3, title="Close", core_content=["Decide"]),
        ],
    )
    styles = [
        StyleOption(
            key=key,
            name=f"Style {key}",
            mood="Clear",
            primary="#16324F",
            secondary="#2E6F95",
            background="#F4F8FB",
            text="#102A43",
            accent="#F29E4C",
        )
        for key in ("A", "B", "C", "D")
    ]
    paths = render_style_auditions(styles, outline, tmp_path)
    assert len(paths) == 4
    assert all(Path(path).exists() for path in paths)


def test_contact_sheet_is_written(tmp_path: Path) -> None:
    pages = [
        StoryPage(
            number=1,
            title="Cover",
            content=["One assertion"],
            visual_direction="Cover",
            layout=LayoutType.HERO,
            family=SlideFamily.COVER,
            kpis=[KPIItem(value="4", label="Slides")],
        )
    ]
    design = DesignSpec(
        style_name="Test",
        mood="Clear",
        primary="#16324F",
        secondary="#2E6F95",
        background="#F4F8FB",
        text="#102A43",
        accent="#F29E4C",
        illustration_style="Flat",
    )
    path = render_contact_sheet(pages, design, tmp_path)
    assert Path(path).exists()
