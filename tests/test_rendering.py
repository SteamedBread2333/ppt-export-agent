from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from pptx import Presentation

from ppt_expert.assets import generate_assets
from ppt_expert.config import AgentConfig
from ppt_expert.models import (
    ChartSeries,
    ChartSpec,
    ChartType,
    DesignSpec,
    ImageRequest,
    KPIItem,
    LayoutType,
    OutlinePage,
    OutlinePlan,
    SlideFamily,
    StoryPage,
    TableSpec,
)
from ppt_expert.pptx import render_presentation
from ppt_expert.runtime import HostRuntime
from ppt_expert.validation import validate_presentation


def _design() -> DesignSpec:
    return DesignSpec(
        style_name="Test Direction",
        mood="Clear and composed",
        primary="#16324F",
        secondary="#2E6F95",
        background="#F4F8FB",
        text="#102A43",
        accent="#F29E4C",
        illustration_style="Contemporary flat illustration",
    )


def test_every_layout_renders_and_validates(tmp_path: Path) -> None:
    layouts = list(LayoutType)
    pages = [
        StoryPage(
            number=index,
            title=f"Slide {index}",
            content=[f"Core message {index}"],
            visual_direction="Abstract visual composition",
            layout=layout,
        )
        for index, layout in enumerate(layouts, 1)
    ]
    outline = OutlinePlan(
        title="Layout Test",
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


def test_native_chart_table_and_kpis_validate(tmp_path: Path) -> None:
    pages = [
        StoryPage(
            number=1,
            title="Cover with evidence",
            content=["Strategy remains overweight cyclical earnings"],
            visual_direction="KPI cover",
            layout=LayoutType.HERO,
            family=SlideFamily.COVER,
            eyebrow="2026H2",
            kpis=[
                KPIItem(value="36.8%", label="Consensus upside", note="CSI 300"),
                KPIItem(value="3", label="Scenarios", note="Base / bull / bear"),
            ],
        ),
        StoryPage(
            number=2,
            title="Earnings revision path",
            content=["Revisions inflect before price", "Follow the slope, not the level"],
            visual_direction="Line chart of revisions",
            layout=LayoutType.TEXT,
            family=SlideFamily.CHART_INTERPRETATION,
            takeaway="The turn is already in the data.",
            chart=ChartSpec(
                chart_type=ChartType.LINE,
                categories=["Q1", "Q2", "Q3", "Q4"],
                series=[ChartSeries(name="Revisions", values=[-1.2, -0.4, 0.6, 1.1])],
            ),
        ),
        StoryPage(
            number=3,
            title="Allocation",
            content=["Keep a barbell until breadth expands"],
            visual_direction="Allocation strip",
            layout=LayoutType.TEXT,
            family=SlideFamily.TABLE_COMPARISON,
            table=TableSpec(
                headers=["Sleeve", "Weight", "Bias"],
                rows=[["Cyclicals", "40%", "Overweight"], ["Quality", "35%", "Neutral"]],
                highlight_row=0,
            ),
        ),
    ]
    outline = OutlinePlan(
        title="Analytics",
        pages=[
            OutlinePage(number=page.number, title=page.title, core_content=page.content)
            for page in pages
        ],
    )
    path = tmp_path / "analytics.pptx"
    design = _design()
    render_presentation(pages, design, {}, path, AgentConfig())
    report = validate_presentation(path, outline, pages, design, {})
    presentation = Presentation(path)

    assert report.valid is True, report.model_dump()
    assert any(shape.has_chart for shape in presentation.slides[1].shapes)
    assert any(shape.has_table for shape in presentation.slides[2].shapes)



@pytest.mark.asyncio
async def test_missing_host_image_tool_uses_palette_placeholder(tmp_path: Path) -> None:
    request = ImageRequest(image_id="hero", page_numbers=[1], prompt="test")
    paths = await generate_assets(HostRuntime(), [request], _design(), tmp_path)

    generated = Path(paths["hero"])
    assert generated.exists()
    with Image.open(generated) as image:
        assert image.size == (1536, 1024)


@pytest.mark.asyncio
async def test_jpeg_written_to_png_path_is_normalized(tmp_path: Path) -> None:
    def write_disguised_jpeg(request, output_path):
        image = Image.new("RGB", (64, 48), (220, 20, 30))
        image.save(output_path, format="JPEG")
        return output_path

    request = ImageRequest(image_id="hero", page_numbers=[1], prompt="jpeg bytes")
    runtime = HostRuntime(image_generate=write_disguised_jpeg)
    paths = await generate_assets(runtime, [request], _design(), tmp_path)

    generated = Path(paths["hero"])
    assert generated.suffix == ".png"
    with Image.open(generated) as image:
        assert image.format == "PNG"
        assert image.getpixel((32, 24))[0] > 180


@pytest.mark.asyncio
async def test_jpg_sibling_written_by_host_is_discovered_and_converted(tmp_path: Path) -> None:
    def write_jpg_sibling(request, output_path):
        jpeg_path = output_path.with_suffix(".jpg")
        buffer = BytesIO()
        Image.new("RGB", (80, 60), (15, 180, 60)).save(buffer, format="JPEG")
        jpeg_path.write_bytes(buffer.getvalue())

    request = ImageRequest(image_id="hero", page_numbers=[1], prompt="jpg sibling")
    runtime = HostRuntime(image_generate=write_jpg_sibling)
    paths = await generate_assets(runtime, [request], _design(), tmp_path)

    generated = Path(paths["hero"])
    assert generated.suffix == ".png"
    with Image.open(generated) as image:
        assert image.format == "PNG"
        assert image.getpixel((40, 30))[1] > 140
