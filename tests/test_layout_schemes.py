from pathlib import Path

from pptx import Presentation

from ppt_expert.config import AgentConfig
from ppt_expert.models import KPIItem, LayoutType, PageRole, RecipeId, SlideFamily, StoryPage
from ppt_expert.pptx import render_presentation
from ppt_expert.recipes import tokens_for
from ppt_expert.review import review_volume


def _overview_pages() -> list[StoryPage]:
    return [
        StoryPage(
            number=1,
            title="三条判断仍然成立",
            content=[
                "增长换挡而非失速：名义增长 4.8%–5.2%",
                "盈利底部渐明：非金融由 -2.1% 回升至 +6.5%",
                "风格再平衡：拥挤度 96%→71%",
            ],
            visual_direction="Overview",
            layout=LayoutType.DATA_CARDS,
            family=SlideFamily.EXECUTIVE_SUMMARY,
            role=PageRole.OVERVIEW,
            takeaway="以杠铃结构穿越再平衡。",
            speaker_notes="Overview",
            kpis=[
                KPIItem(value="4,150", label="沪深300"),
                KPIItem(value="+6.5%", label="盈利增速"),
            ],
        )
    ]


def _body_cross(slide) -> bool:
    vlines = []
    hlines = []
    for shape in slide.shapes:
        width = shape.width.inches
        height = shape.height.inches
        top = shape.top.inches
        if top < 1.32 or top > 6.2:
            continue
        if 0.006 <= width <= 0.03 and height > 1.0:
            vlines.append(shape)
        if 0.006 <= height <= 0.03 and width > 3.0:
            hlines.append(shape)
    return bool(vlines) and bool(hlines)


def _render(recipe: RecipeId, tmp_path: Path):
    tokens = tokens_for(recipe)
    path = tmp_path / f"{recipe.value}.pptx"
    render_presentation(
        _overview_pages(),
        tokens.to_design_spec(),
        {},
        path,
        AgentConfig(),
        tokens=tokens,
    )
    return Presentation(path).slides[0], path, tokens


def test_non_consulting_recipes_do_not_share_the_hairline_cross(tmp_path: Path) -> None:
    consulting, _, _ = _render(RecipeId.CONSULTING, tmp_path)
    assert _body_cross(consulting)
    for recipe in (
        RecipeId.WORK_REPORT,
        RecipeId.CIVIC,
        RecipeId.ART_MARKET,
        RecipeId.EDITORIAL,
        RecipeId.HISTORY,
        RecipeId.OPEN,
    ):
        slide, _, _ = _render(recipe, tmp_path)
        assert not _body_cross(slide), recipe.value


def test_filled_schemes_are_allowed_to_use_surfaces(tmp_path: Path) -> None:
    _, path, tokens = _render(RecipeId.WORK_REPORT, tmp_path)
    review = review_volume(
        path,
        _overview_pages(),
        tmp_path,
        layout_scheme=tokens.layout_scheme,
    )
    assert "card_soup" not in {issue.code for issue in review.issues}
