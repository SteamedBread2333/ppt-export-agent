from __future__ import annotations

from typing import Any

from ppt_expert.models import (
    ChartSeries,
    ChartSpec,
    ChartType,
    DesignSpec,
    IntentSlots,
    KPIItem,
    LayoutType,
    OutlinePage,
    OutlinePlan,
    PageRole,
    SlideFamily,
    StoryDesignBundle,
    StoryPage,
)


def fake_structured_generate(prompt: str, schema: type) -> Any:
    """Deterministic offline host used only by tests and `ppt-expert demo`."""
    if schema is IntentSlots:
        return IntentSlots(
            topic="PPT Expert workflow",
            audience="Demo users",
            objective="Demonstrate the six-phase production system",
            slide_count=4,
            density="medium",
        )
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
    if schema is StoryDesignBundle:
        return StoryDesignBundle(
            pages=[
                StoryPage(
                    number=1,
                    title="From Idea to Presentation",
                    content=["Make every message more compelling"],
                    visual_direction="Consulting cover with KPIs",
                    layout=LayoutType.HERO,
                    family=SlideFamily.COVER,
                    role=PageRole.COVER,
                    eyebrow="PPT EXPERT",
                    subtitle="A host-model workflow that designs before it decorates",
                    takeaway="Design the argument before decorating the slide.",
                    source_note="Demo fixture",
                    speaker_notes="Open on the production claim, not a photograph.",
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
                    visual_direction="Line chart of narrative density",
                    layout=LayoutType.TEXT,
                    family=SlideFamily.CHART_INTERPRETATION,
                    role=PageRole.CONTEXT,
                    eyebrow="STRUCTURE",
                    takeaway="Density should peak once, then resolve.",
                    source_note="Demo fixture",
                    speaker_notes="Walk the density curve; do not read every bullet.",
                    chart=ChartSpec(
                        chart_type=ChartType.LINE,
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
                    visual_direction="Three operating pillars",
                    layout=LayoutType.DATA_CARDS,
                    family=SlideFamily.PILLARS,
                    role=PageRole.EXPANSION,
                    eyebrow="SYSTEM",
                    takeaway="Palette, rhythm, and validation stay in one system.",
                    source_note="Demo fixture",
                    speaker_notes="Three modules, one operating system.",
                ),
                StoryPage(
                    number=4,
                    title="Make Every Presentation Count",
                    content=["Complete, validate, and deliver"],
                    visual_direction="Closing recommendation",
                    layout=LayoutType.TEXT,
                    family=SlideFamily.CONCLUSION,
                    role=PageRole.CLOSE,
                    eyebrow="NEXT STEP",
                    takeaway="Deliver only after validation and a human pass.",
                    source_note="Demo fixture",
                    speaker_notes="Close on the delivery gate.",
                ),
            ],
            design=DesignSpec(
                style_name="consulting",
                mood="Analytical, compressed, calm",
                primary="#1F4E79",
                secondary="#44505C",
                background="#F7F8FA",
                text="#1B242C",
                accent="#1F4E79",
                illustration_style="vector_first",
                typography_profile="consulting",
            ),
        )
    raise ValueError(f"Unsupported demo schema: {schema.__name__}")
