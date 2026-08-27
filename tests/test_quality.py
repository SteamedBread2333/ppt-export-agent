from ppt_expert.enrichment import enrich_story
from ppt_expert.models import (
    ChartSeries,
    ChartSpec,
    ChartType,
    DesignSpec,
    KPIItem,
    LayoutType,
    SlideFamily,
    StoryPage,
)
from ppt_expert.quality import score_deck


def _page(**overrides) -> StoryPage:
    payload = {
        "number": 1,
        "title": "Cover",
        "content": ["Make the decision now"],
        "visual_direction": "Cover",
        "layout": LayoutType.HERO,
        "family": SlideFamily.COVER,
        "kpis": [KPIItem(value="3", label="Options")],
    }
    payload.update(overrides)
    return StoryPage(**payload)


def _design() -> DesignSpec:
    return DesignSpec(
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


def test_enrichment_adds_cover_kpis_and_takeaway() -> None:
    page = StoryPage(
        number=1,
        title="From Idea to Presentation",
        content=["Make every message more compelling"],
        visual_direction="Cover",
        layout=LayoutType.HERO,
        family=SlideFamily.HERO,
    )
    enriched = enrich_story([page])[0]
    assert enriched.family == SlideFamily.COVER
    assert enriched.kpis
    assert enriched.takeaway


def test_quality_rewards_native_visuals() -> None:
    pages = [
        _page(),
        _page(
            number=2,
            title="Path",
            family=SlideFamily.CHART_INTERPRETATION,
            layout=LayoutType.TEXT,
            content=["Revisions inflect"],
            takeaway="Follow the slope",
            eyebrow="EVIDENCE",
            kpis=[],
            chart=ChartSpec(
                chart_type=ChartType.LINE,
                categories=["Q1", "Q2", "Q3"],
                series=[ChartSeries(name="Revisions", values=[-1.0, 0.2, 1.1])],
            ),
        ),
        _page(
            number=3,
            title="Close",
            family=SlideFamily.CONCLUSION,
            layout=LayoutType.TEXT,
            content=["Act this quarter"],
            eyebrow="NEXT",
            kpis=[],
        ),
    ]
    report = score_deck(pages, _design())
    assert report.score >= 80
    assert not report.blocking_issues
