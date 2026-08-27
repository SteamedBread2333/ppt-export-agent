from ppt_expert.composition import choose_compositions
from ppt_expert.models import (
    ChartSeries,
    ChartSpec,
    ChartType,
    DesignSpec,
    LayoutType,
    SlideFamily,
    StoryPage,
)
from ppt_expert.repair import merge_repaired_pages


def _page(number: int, title: str, **overrides) -> StoryPage:
    payload = {
        "number": number,
        "title": title,
        "content": [title],
        "visual_direction": title,
        "layout": LayoutType.TEXT,
        "family": SlideFamily.TEXT,
    }
    payload.update(overrides)
    return StoryPage(**payload)


def test_merge_repaired_pages_replaces_only_named_slides() -> None:
    current = [_page(1, "Cover"), _page(2, "Overflow")]
    proposed = [_page(1, "Cover rewritten"), _page(2, "Fixed")]
    merged = merge_repaired_pages(current, proposed, [2])
    assert merged[0].title == "Cover"
    assert merged[1].title == "Overflow"
    assert merged[1].content == ["Fixed"]


def test_composition_search_records_decisions(tmp_path) -> None:
    pages = [
        _page(
            1,
            "Cover",
            family=SlideFamily.COVER,
            layout=LayoutType.HERO,
            kpis=[],
        ),
        _page(
            2,
            "Path",
            family=SlideFamily.CHART_INTERPRETATION,
            chart=ChartSpec(
                chart_type=ChartType.LINE,
                categories=["A", "B"],
                series=[
                    ChartSeries(name="Focus", values=[1, 2]),
                    ChartSeries(name="Support", values=[2, 1]),
                ],
            ),
        ),
    ]
    design = DesignSpec(
        style_name="Deep Blue",
        mood="Measured",
        primary="#16324F",
        secondary="#2E6F95",
        background="#F4F8FB",
        text="#102A43",
        accent="#F29E4C",
        illustration_style="Flat",
        latin_font="Avenir Next",
        east_asian_font="PingFang SC",
    )
    chosen = choose_compositions(pages, design, tmp_path)
    assert (tmp_path / "composition.json").exists()
    assert chosen[0].number == 1
