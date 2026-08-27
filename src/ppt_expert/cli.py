from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Annotated

import typer
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from ppt_expert.agent import create_ppt_agent
from ppt_expert.config import AgentConfig
from ppt_expert.demo_runtime import fake_structured_generate
from ppt_expert.models import DesignSpec, OutlinePlan, ReferenceAnalysis, StoryPage
from ppt_expert.pptx import render_presentation
from ppt_expert.runtime import HostRuntime
from ppt_expert.validation import validate_presentation, write_validation_report

app = typer.Typer(help="Host-model-powered LangGraph PPT Expert Agent")


@app.command()
def demo(
    output: Annotated[Path, typer.Option(help="Output directory")] = Path("outputs"),
    style: Annotated[
        str | None, typer.Option(help="Choose A/B/C/D without prompting")
    ] = None,
    template: Annotated[
        Path | None, typer.Option(help="Optional PPTX template")
    ] = None,
    reference_image: Annotated[
        list[Path] | None,
        typer.Option("--reference-image", help="Repeatable style reference image"),
    ] = None,
    reference_action: Annotated[
        str, typer.Option(help="Reference decision: use or ignore")
    ] = "use",
) -> None:
    """Run a complete offline demo with the deterministic fake host."""

    async def run() -> None:
        runtime = HostRuntime(structured_generate=fake_structured_generate)
        config = AgentConfig(output_root=output, enable_libreoffice_preview=False)
        async with create_ppt_agent(runtime, config) as agent:
            result = await agent.start(
                "制作一份展示 PPT 大师工作流的演示文稿",
                template_path=template,
                reference_images=reference_image or [],
            )
            request = result["request"]
            if request["type"] == "reference_confirmation":
                typer.echo("参考内容与提取风格：")
                for path in request["reference"]["preview_paths"]:
                    typer.echo(f"  {path}")
                result = await agent.resume(
                    result["thread_id"], {"action": reference_action}
                )
                if result["status"] == "completed":
                    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
                    return
                request = result["request"]
            typer.echo("风格预览：")
            for path in request["preview_paths"]:
                typer.echo(f"  {path}")
            choice = (style or typer.prompt("请选择风格 A/B/C/D", default="A")).upper()
            completed = await agent.resume(result["thread_id"], choice)
            typer.echo(json.dumps(completed, ensure_ascii=False, indent=2))

    asyncio.run(run())


@app.command()
def rebuild(project_dir: Path) -> None:
    """Rebuild the PPTX once from story.json/design.json and assets, then validate."""

    try:
        report_path, valid = _rebuild_project(project_dir)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"{'PASS' if valid else 'FAIL'}: {report_path}")
    if not valid:
        raise typer.Exit(code=1)


@app.command("validate")
def validate_command(project_dir: Path) -> None:
    """Validate an already generated project directory."""
    report_path, valid = _validate_project(project_dir)
    typer.echo(f"{'PASS' if valid else 'FAIL'}: {report_path}")
    if not valid:
        raise typer.Exit(code=1)


@app.command()
def watch(project_dir: Path) -> None:
    """Rebuild and revalidate when STORY, DESIGN, or assets change."""
    project = project_dir.expanduser().resolve()

    class Handler(FileSystemEventHandler):
        def on_modified(self, event: FileSystemEvent) -> None:
            changed = Path(event.src_path)
            if event.is_directory or not _is_build_input(project, changed):
                return
            try:
                report_path, valid = _rebuild_project(project)
                typer.echo(f"{'PASS' if valid else 'FAIL'}: {report_path}")
            except (OSError, ValueError) as exc:
                typer.echo(f"Waiting for a complete rebuild: {exc}")

        on_created = on_modified

    observer = Observer()
    observer.schedule(Handler(), str(project), recursive=True)
    observer.start()
    typer.echo(f"Watching and rebuilding {project}; press Ctrl-C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def _validate_project(project_dir: Path) -> tuple[str, bool]:
    project = project_dir.expanduser().resolve()
    outline = OutlinePlan.model_validate_json((project / "outline.json").read_text("utf-8"))
    story = [
        StoryPage.model_validate(item)
        for item in json.loads((project / "story.json").read_text("utf-8"))
    ]
    design = DesignSpec.model_validate_json((project / "design.json").read_text("utf-8"))
    pptx_files = list(project.glob("*.pptx"))
    if not pptx_files:
        raise typer.BadParameter(f"No PPTX found in {project}")
    image_paths = _image_paths(project, story)
    report = validate_presentation(pptx_files[0], outline, story, design, image_paths)
    report_path = write_validation_report(report, project)
    return report_path, report.valid


def _rebuild_project(project_dir: Path) -> tuple[str, bool]:
    project = project_dir.expanduser().resolve()
    story = [
        StoryPage.model_validate(item)
        for item in json.loads((project / "story.json").read_text("utf-8"))
    ]
    design = DesignSpec.model_validate_json((project / "design.json").read_text("utf-8"))
    pptx_files = list(project.glob("*.pptx"))
    output_path = pptx_files[0] if pptx_files else project / f"{project.name}.pptx"
    image_paths = _image_paths(project, story)
    template_path = None
    selection_path = project / "reference-selection.json"
    references_path = project / "references.json"
    if selection_path.exists() and references_path.exists():
        selection = json.loads(selection_path.read_text("utf-8"))
        if selection.get("decision") == "use":
            template_path = ReferenceAnalysis.model_validate_json(
                references_path.read_text("utf-8")
            ).template_path
    render_presentation(
        story,
        design,
        image_paths,
        output_path,
        AgentConfig(),
        template_path=template_path,
    )
    return _validate_project(project)


def _image_paths(project: Path, story: list[StoryPage]) -> dict[str, str]:
    image_paths: dict[str, str] = {}
    assets = project / "assets"
    for page in story:
        if page.image_id and page.image_id not in image_paths:
            matches = sorted(
                path
                for path in assets.glob(f"{page.image_id}_*")
                if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
            )
            if matches:
                preferred = next(
                    (path for path in matches if path.suffix.lower() == ".png"),
                    matches[0],
                )
                image_paths[page.image_id] = str(preferred.resolve())
    return image_paths


def _is_build_input(project: Path, changed: Path) -> bool:
    return changed.name in {
        "story.json",
        "design.json",
        "references.json",
        "reference-selection.json",
    } or (
        changed.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        and (project / "assets") in changed.parents
    )


if __name__ == "__main__":
    app()
