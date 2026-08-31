import pytest

from ppt_expert.models import (
    DesignSpec,
    KPIItem,
    LayoutType,
    QualityIssue,
    SlideFamily,
    StoryPage,
    VisionCritique,
)
from ppt_expert.quality import score_deck
from ppt_expert.runtime import HostRuntime
from ppt_expert.vision import apply_vision_review, critique_montage


def _pages() -> list[StoryPage]:
    return [
        StoryPage(
            number=1,
            title="Cover",
            content=["Decide now"],
            visual_direction="Cover",
            layout=LayoutType.HERO,
            family=SlideFamily.COVER,
            takeaway="Decide now",
            kpis=[KPIItem(value="1", label="Call")],
        )
    ]


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


@pytest.mark.asyncio
async def test_vision_review_merges_conservative_score(tmp_path) -> None:
    contact = tmp_path / "contact.png"
    contact.write_bytes(b"png")
    report = score_deck(_pages(), _design(), str(contact), vision_available=True)
    host = HostRuntime(
        critique_images=lambda prompt, paths, schema: VisionCritique(
            score=70,
            issues=[
                QualityIssue(
                    code="weak_whitespace",
                    message="The cover KPI row collides with the thesis",
                    page=1,
                    cause="Components share one band",
                    repair_scope="component",
                    acceptance="KPI row sits on its own baseline",
                )
            ],
        )
    )
    merged = await apply_vision_review(report, host, [str(contact)])
    assert merged.score <= 70
    assert merged.vision_review == "completed"
    assert any(issue.code == "weak_whitespace" for issue in merged.warnings)
    assert "rendered_visual" in merged.dimensions


@pytest.mark.asyncio
async def test_montage_critique_keeps_error_severity(tmp_path) -> None:
    sheet = tmp_path / "montage.png"
    sheet.write_bytes(b"png")
    host = HostRuntime(
        critique_images=lambda prompt, paths, schema: VisionCritique(
            score=40,
            issues=[
                QualityIssue(
                    code="card_soup",
                    message="Gray tiles",
                    page=2,
                    severity="error",
                    cause="Filled modules",
                    repair_scope="slide",
                    acceptance="Type and hairlines",
                )
            ],
        )
    )
    issues = await critique_montage(host, [str(sheet)])
    assert issues
    assert issues[0].code == "card_soup"
    assert issues[0].severity == "error"


class _VisionRunner:
    def invoke(self, _messages):
        return VisionCritique(
            score=80,
            issues=[
                QualityIssue(
                    code="topic_title",
                    message="The title names a subject",
                    page=1,
                    severity="warning",
                )
            ],
        )


class _VisionModel:
    def with_structured_output(self, _schema):
        return _VisionRunner()


@pytest.mark.asyncio
async def test_model_critiques_montage_when_critique_images_is_missing(tmp_path) -> None:
    sheet = tmp_path / "montage.png"
    sheet.write_bytes(b"png")
    issues = await critique_montage(HostRuntime(model=_VisionModel()), [str(sheet)])
    assert issues
    assert issues[0].code == "topic_title"
    assert issues[0].severity == "warning"


@pytest.mark.asyncio
async def test_missing_vision_host_fails(tmp_path) -> None:
    sheet = tmp_path / "montage.png"
    sheet.write_bytes(b"png")
    with pytest.raises(RuntimeError, match="critique_images"):
        await critique_montage(HostRuntime(), [str(sheet)])
