from __future__ import annotations

from typing import Any

from ppt_expert.models import (
    DesignSpec,
    ImagePlan,
    ImageRequest,
    LayoutType,
    OutlinePage,
    OutlinePlan,
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
                    visual_direction="Abstract beams converging into a presentation canvas",
                    layout=LayoutType.HERO,
                    image_id="hero_open",
                ),
                StoryPage(
                    number=2,
                    title="A Clear Narrative",
                    content=[
                        "Honor the source outline",
                        "Create a focal point on every slide",
                        "Control information density",
                    ],
                    visual_direction="A figure arranging cards along a narrative path",
                    layout=LayoutType.LEFT_IMAGE,
                    image_id="story_flow",
                ),
                StoryPage(
                    number=3,
                    title="Design and Content in Sync",
                    content=["Unified palette", "Visual rhythm", "Automated validation"],
                    visual_direction="Color, imagery, and typography working as one system",
                    layout=LayoutType.DATA_CARDS,
                ),
                StoryPage(
                    number=4,
                    title="Make Every Presentation Count",
                    content=["Complete, validate, and deliver"],
                    visual_direction="A distant stage with an ascending beam of light",
                    layout=LayoutType.HERO,
                    image_id="hero_close",
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
        return ImagePlan(
            images=[
                ImageRequest(
                    image_id="hero_open",
                    page_numbers=[1],
                    prompt=(
                        "Contemporary warm flat illustration, abstract beams converging, "
                        "no text or watermarks"
                    ),
                ),
                ImageRequest(
                    image_id="story_flow",
                    page_numbers=[2],
                    prompt=(
                        "Contemporary warm flat illustration, rear-view figure arranging "
                        "story cards, no text or watermarks"
                    ),
                ),
                ImageRequest(
                    image_id="hero_close",
                    page_numbers=[4],
                    prompt=(
                        "Contemporary warm flat illustration, distant stage, "
                        "no text or watermarks"
                    ),
                ),
            ]
        )
    raise ValueError(f"Unsupported demo schema: {schema.__name__}")
