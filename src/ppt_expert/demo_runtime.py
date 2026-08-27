from __future__ import annotations

from typing import Any

from ppt_expert.models import (
    ChartSeries,
    ChartSpec,
    ChartType,
    DesignSpec,
    ImagePlan,
    KPIItem,
    LayoutType,
    OutlinePage,
    OutlinePlan,
    SlideFamily,
    StoryDesignBundle,
    StoryPage,
    StyleOption,
    StyleOptions,
)


def fake_structured_generate(prompt: str, schema: type) -> Any:
    """Deterministic offline host used only by tests and `ppt-expert demo`."""
    if schema is OutlinePlan:
        return OutlinePlan(
            title="PPT Expert Demo",
            audience="Demo users",
            purpose="Demonstrate the complete workflow",
            pages=[
                OutlinePage(
                    number=1,
                    title="From Idea to Presentation",
                    core_content=["Make every message more compelling"],
                ),
                OutlinePage(
                    number=2,
                    title="A Clear Narrative",
                    core_content=[
                        "Honor the source outline",
                        "Create a focal point on every slide",
                        "Control information density",
                    ],
                ),
                OutlinePage(
                    number=3,
                    title="Design and Content in Sync",
                    core_content=["Unified palette", "Visual rhythm", "Automated validation"],
                ),
                OutlinePage(
                    number=4,
                    title="Make Every Presentation Count",
                    core_content=["Complete, validate, and deliver"],
                ),
            ],
        )
    if schema is StyleOptions:
        return StyleOptions(
            options=[
                StyleOption(
                    key="A",
                    name="Warm Narrative",
                    mood="Warm, human, and approachable",
                    primary="#E8603C",
                    secondary="#F5C24B",
                    background="#FFF8F0",
                    text="#3D2B1F",
                    accent="#3B8C88",
                ),
                StyleOption(
                    key="B",
                    name="Deep Blue",
                    mood="Measured, confident, and trustworthy",
                    primary="#16324F",
                    secondary="#2E6F95",
                    background="#F4F8FB",
                    text="#102A43",
                    accent="#F29E4C",
                ),
                StyleOption(
                    key="C",
                    name="Fresh Botanical",
                    mood="Light, energetic, and minimal",
                    primary="#3A7D44",
                    secondary="#A4C3A2",
                    background="#F5FAF4",
                    text="#24352A",
                    accent="#E9A03B",
                ),
                StyleOption(
                    key="D",
                    name="Modern Violet",
                    mood="Creative, refined, and forward-looking",
                    primary="#5B4B8A",
                    secondary="#9B8FC4",
                    background="#F8F6FC",
                    text="#29243A",
                    accent="#E06C9F",
                ),
            ]
        )
    if schema is StoryDesignBundle:
        return StoryDesignBundle(
            pages=[
                StoryPage(
                    number=1,
                    title="From Idea to Presentation",
                    content=["Make every message more compelling"],
                    visual_direction="Consulting cover with KPIs, not a full-bleed illustration",
                    layout=LayoutType.HERO,
                    family=SlideFamily.COVER,
                    eyebrow="PPT EXPERT",
                    subtitle="A host-model workflow that designs before it decorates",
                    takeaway="Design the argument before decorating the slide.",
                    source_note="Demo fixture",
                    kpis=[
                        KPIItem(value="4", label="Slides", note="Outline fidelity"),
                        KPIItem(value="1", label="Assertion", note="Per slide"),
                        KPIItem(value="0", label="Decorative art", note="Cover is vector"),
                    ],
                ),
                StoryPage(
                    number=2,
                    title="A Clear Narrative",
                    content=[
                        "Honor the source outline",
                        "Create a focal point on every slide",
                        "Control information density",
                    ],
                    visual_direction="Line chart of narrative density across the deck",
                    layout=LayoutType.TEXT,
                    family=SlideFamily.CHART_INTERPRETATION,
                    eyebrow="STRUCTURE",
                    takeaway="Density should peak once, then resolve.",
                    source_note="Demo fixture",
                    chart=ChartSpec(
                        chart_type=ChartType.LINE,
                        title="",
                        categories=["Cover", "Narrative", "System", "Close"],
                        series=[
                            ChartSeries(name="Focus", values=[8, 12, 9, 6]),
                            ChartSeries(name="Support", values=[3, 5, 7, 4]),
                        ],
                    ),
                ),
                StoryPage(
                    number=3,
                    title="Design and Content in Sync",
                    content=["Unified palette", "Visual rhythm", "Automated validation"],
                    visual_direction="Three operating pillars as native cards",
                    layout=LayoutType.DATA_CARDS,
                    family=SlideFamily.PILLARS,
                    eyebrow="SYSTEM",
                    takeaway="Palette, rhythm, and validation stay in one system.",
                    source_note="Demo fixture",
                ),
                StoryPage(
                    number=4,
                    title="Make Every Presentation Count",
                    content=["Complete, validate, and deliver"],
                    visual_direction="Closing recommendation, not a second hero photograph",
                    layout=LayoutType.TEXT,
                    family=SlideFamily.CONCLUSION,
                    eyebrow="NEXT STEP",
                    takeaway="Deliver only after validation and a human pass.",
                    source_note="Demo fixture",
                ),
            ],
            design=DesignSpec(
                style_name="Warm Narrative",
                mood="Warm, human, and approachable",
                primary="#E8603C",
                secondary="#F5C24B",
                background="#FFF8F0",
                text="#3D2B1F",
                accent="#3B8C88",
                illustration_style="Contemporary warm flat illustration",
            ),
        )
    if schema is ImagePlan:
        return ImagePlan(images=[])
    raise ValueError(f"Unsupported demo schema: {schema.__name__}")
