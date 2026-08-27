from pathlib import Path

import pytest
from PIL import Image
from pptx import Presentation

from ppt_expert.assets import generate_assets
from ppt_expert.config import AgentConfig
from ppt_expert.models import (
    DesignSpec,
    ImageRequest,
    LayoutType,
    OutlinePage,
    OutlinePlan,
    StoryPage,
)
from ppt_expert.pptx import render_presentation
from ppt_expert.runtime import HostRuntime
from ppt_expert.validation import validate_presentation


def _design() -> DesignSpec:
    return DesignSpec(
        style_name="测试风格",
        mood="清晰",
        primary="#16324F",
        secondary="#2E6F95",
        background="#F4F8FB",
        text="#102A43",
        accent="#F29E4C",
        illustration_style="现代扁平插画",
    )


def test_every_layout_renders_and_validates(tmp_path: Path) -> None:
    layouts = list(LayoutType)
    pages = [
        StoryPage(
            number=index,
            title=f"页面 {index}",
            content=[f"核心内容 {index}"],
            visual_direction="抽象视觉",
            layout=layout,
        )
        for index, layout in enumerate(layouts, 1)
    ]
    outline = OutlinePlan(
        title="版式测试",
        pages=[
            OutlinePage(number=page.number, title=page.title, core_content=page.content)
            for page in pages
        ],
    )
    path = tmp_path / "layouts.pptx"
    render_presentation(pages, _design(), {}, path, AgentConfig())
    report = validate_presentation(path, outline, pages, _design(), {})

    assert report.valid is True
    assert len(Presentation(path).slides) == len(layouts)


@pytest.mark.asyncio
async def test_missing_host_image_tool_uses_palette_placeholder(tmp_path: Path) -> None:
    request = ImageRequest(image_id="hero", page_numbers=[1], prompt="test")
    paths = await generate_assets(HostRuntime(), [request], _design(), tmp_path)

    generated = Path(paths["hero"])
    assert generated.exists()
    with Image.open(generated) as image:
        assert image.size == (1536, 1024)
