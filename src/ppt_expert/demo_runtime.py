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
            title="PPT 大师演示",
            audience="演示用户",
            purpose="展示完整工作流",
            pages=[
                OutlinePage(number=1, title="从想法到演示", core_content=["让表达更有力量"]),
                OutlinePage(
                    number=2,
                    title="清晰的叙事结构",
                    core_content=["忠于提纲", "逐页建立视觉重点", "控制信息密度"],
                ),
                OutlinePage(
                    number=3,
                    title="设计与内容协同",
                    core_content=["统一色板", "图文节奏", "自动校验"],
                ),
                OutlinePage(number=4, title="让每次分享更精彩", core_content=["完成并交付"]),
            ],
        )
    if schema is StyleOptions:
        return StyleOptions(
            options=[
                StyleOption(
                    key="A", name="暖阳叙事", mood="温暖、人文、亲和",
                    primary="#E8603C", secondary="#F5C24B", background="#FFF8F0",
                    text="#3D2B1F", accent="#3B8C88",
                ),
                StyleOption(
                    key="B", name="深海商务", mood="理性、沉稳、可信",
                    primary="#16324F", secondary="#2E6F95", background="#F4F8FB",
                    text="#102A43", accent="#F29E4C",
                ),
                StyleOption(
                    key="C", name="清新自然", mood="轻盈、生机、简洁",
                    primary="#3A7D44", secondary="#A4C3A2", background="#F5FAF4",
                    text="#24352A", accent="#E9A03B",
                ),
                StyleOption(
                    key="D", name="现代紫调", mood="创意、精致、未来",
                    primary="#5B4B8A", secondary="#9B8FC4", background="#F8F6FC",
                    text="#29243A", accent="#E06C9F",
                ),
            ]
        )
    if schema is StoryDesignBundle:
        return StoryDesignBundle(
            pages=[
                StoryPage(
                    number=1, title="从想法到演示", content=["让表达更有力量"],
                    visual_direction="抽象光束汇聚成演示画面", layout=LayoutType.HERO,
                    image_id="hero_open",
                ),
                StoryPage(
                    number=2, title="清晰的叙事结构",
                    content=["忠于提纲", "逐页建立视觉重点", "控制信息密度"],
                    visual_direction="人物整理卡片和故事线", layout=LayoutType.LEFT_IMAGE,
                    image_id="story_flow",
                ),
                StoryPage(
                    number=3, title="设计与内容协同",
                    content=["统一色板", "图文节奏", "自动校验"],
                    visual_direction="色彩、图片与文字模块协同", layout=LayoutType.DATA_CARDS,
                ),
                StoryPage(
                    number=4, title="让每次分享更精彩", content=["完成并交付"],
                    visual_direction="舞台远景和向上的光", layout=LayoutType.HERO,
                    image_id="hero_close",
                ),
            ],
            design=DesignSpec(
                style_name="暖阳叙事", mood="温暖、人文、亲和",
                primary="#E8603C", secondary="#F5C24B", background="#FFF8F0",
                text="#3D2B1F", accent="#3B8C88", illustration_style="现代温暖扁平插画",
            ),
        )
    if schema is ImagePlan:
        return ImagePlan(
            images=[
                ImageRequest(
                    image_id="hero_open", page_numbers=[1],
                    prompt="现代温暖扁平插画，抽象光束汇聚，无文字水印",
                ),
                ImageRequest(
                    image_id="story_flow", page_numbers=[2],
                    prompt="现代温暖扁平插画，人物背影整理故事卡片，无文字水印",
                ),
                ImageRequest(
                    image_id="hero_close", page_numbers=[4],
                    prompt="现代温暖扁平插画，舞台远景，无文字水印",
                ),
            ]
        )
    raise ValueError(f"Unsupported demo schema: {schema.__name__}")
