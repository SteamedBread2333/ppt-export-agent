from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pptx import Presentation
from pptx.util import Inches

from ppt_expert import AgentConfig, HostRuntime, create_ppt_agent
from ppt_expert.demo_runtime import fake_structured_generate
from ppt_expert.models import StoryDesignBundle


@pytest.mark.asyncio
async def test_end_to_end_interrupt_and_resume(tmp_path: Path) -> None:
    config = AgentConfig(
        output_root=tmp_path / "outputs",
        checkpoint_path=tmp_path / "checkpoints.sqlite3",
        enable_libreoffice_preview=False,
    )
    runtime = HostRuntime(structured_generate=fake_structured_generate)

    async with create_ppt_agent(runtime, config) as agent:
        interrupted = await agent.start("制作 PPT 大师工作流介绍", project_name="demo")
        assert interrupted["status"] == "interrupted"
        assert interrupted["request"]["type"] == "style_confirmation"
        assert len(interrupted["request"]["preview_paths"]) == 4

        completed = await agent.resume(interrupted["thread_id"], "A")
        assert completed["status"] == "completed"
        assert completed["validation"]["valid"] is True

    artifacts = completed["artifacts"]
    assert Path(artifacts["story_path"]).exists()
    assert Path(artifacts["design_path"]).exists()
    assert Path(artifacts["report_path"]).exists()
    presentation = Presentation(artifacts["pptx_path"])
    assert len(presentation.slides) == 4


@pytest.mark.asyncio
async def test_runtime_uses_host_model_structured_output() -> None:
    class Runnable:
        async def ainvoke(self, prompt):
            return fake_structured_generate(prompt, self.schema)

    class HostModel:
        def with_structured_output(self, schema):
            runnable = Runnable()
            runnable.schema = schema
            return runnable

    from ppt_expert.models import OutlinePlan

    runtime = HostRuntime(model=HostModel())
    result = await runtime.generate_structured("test", OutlinePlan)
    assert result.title == "PPT 大师演示"


@pytest.mark.asyncio
async def test_validation_failure_routes_through_repair(tmp_path: Path) -> None:
    story_calls = 0

    def host_generate(prompt, schema):
        nonlocal story_calls
        result = fake_structured_generate(prompt, schema)
        if schema is StoryDesignBundle:
            story_calls += 1
            if story_calls == 1:
                result = result.model_copy(deep=True)
                result.pages[0].content = ["x" * 400]
        return result

    config = AgentConfig(
        output_root=tmp_path / "outputs",
        checkpoint_path=tmp_path / "checkpoints.sqlite3",
        enable_libreoffice_preview=False,
    )
    async with create_ppt_agent(HostRuntime(structured_generate=host_generate), config) as agent:
        interrupted = await agent.start("repair test")
        completed = await agent.resume(interrupted["thread_id"], "A")
        state = await agent.state(interrupted["thread_id"])

    assert completed["validation"]["valid"] is True
    assert state["repair_attempts"] == 1
    assert story_calls == 2


@pytest.mark.asyncio
async def test_reference_image_uses_human_confirmation(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    image = Image.new("RGB", (300, 200), "#F6F1E8")
    image.paste("#294C60", (0, 0, 180, 200))
    image.paste("#E6A15C", (180, 0, 300, 100))
    image.save(reference)
    config = AgentConfig(
        output_root=tmp_path / "outputs",
        checkpoint_path=tmp_path / "checkpoints.sqlite3",
        enable_libreoffice_preview=False,
    )

    async with create_ppt_agent(
        HostRuntime(structured_generate=fake_structured_generate), config
    ) as agent:
        pending = await agent.start("reference test", reference_images=[reference])
        assert pending["request"]["type"] == "reference_confirmation"
        completed = await agent.resume(pending["thread_id"], {"action": "use"})

    assert completed["status"] == "completed"
    project = Path(completed["artifacts"]["project_dir"])
    assert (project / "references.json").exists()
    assert (project / "reference-selection.json").exists()


@pytest.mark.asyncio
async def test_pptx_template_is_used_after_confirmation(tmp_path: Path) -> None:
    template = tmp_path / "template.pptx"
    source = Presentation()
    source.slide_width = Inches(10)
    source.slide_height = Inches(7.5)
    source.slides.add_slide(source.slide_layouts[6])
    source.save(template)
    config = AgentConfig(
        output_root=tmp_path / "outputs",
        checkpoint_path=tmp_path / "checkpoints.sqlite3",
        enable_libreoffice_preview=False,
    )

    async with create_ppt_agent(
        HostRuntime(structured_generate=fake_structured_generate), config
    ) as agent:
        pending = await agent.start("template test", template_path=template)
        assert pending["request"]["type"] == "reference_confirmation"
        completed = await agent.resume(pending["thread_id"], "use")

    presentation = Presentation(completed["artifacts"]["pptx_path"])
    assert len(presentation.slides) == 4
    assert presentation.slide_width == Inches(13.333)
    assert presentation.slide_height == Inches(7.5)


@pytest.mark.asyncio
async def test_ignoring_reference_returns_to_style_selection(tmp_path: Path) -> None:
    reference = tmp_path / "reference.png"
    Image.new("RGB", (100, 100), "#336699").save(reference)
    config = AgentConfig(
        output_root=tmp_path / "outputs",
        checkpoint_path=tmp_path / "checkpoints.sqlite3",
        enable_libreoffice_preview=False,
    )

    async with create_ppt_agent(
        HostRuntime(structured_generate=fake_structured_generate), config
    ) as agent:
        pending = await agent.start("ignore reference", reference_images=[reference])
        next_step = await agent.resume(pending["thread_id"], {"action": "ignore"})

    assert next_step["status"] == "interrupted"
    assert next_step["request"]["type"] == "style_confirmation"
