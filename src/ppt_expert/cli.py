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
from ppt_expert.models import DesignSpec, OutlinePlan, StoryPage
from ppt_expert.pptx import render_presentation
from ppt_expert.runtime import HostRuntime
from ppt_expert.validation import validate_presentation, write_validation_report

app = typer.Typer(help="Host-model-powered LangGraph PPT Expert Agent")


@app.command()
def demo(
    output: Annotated[Path, typer.Option(help="Output directory")] = Path("outputs"),
    recipe: Annotated[
        str | None,
        typer.Option(help="Recipe id, or 'use' for the recommended match"),
    ] = None,
    delivery: Annotated[
        str | None, typer.Option(help="Delivery decision: approve or revise")
    ] = None,
    template: Annotated[
        Path | None, typer.Option(help="Optional PPTX template")
    ] = None,
    reference_image: Annotated[
        list[Path] | None,
        typer.Option("--reference-image", help="Repeatable style reference image"),
    ] = None,
) -> None:
    """Run a complete offline demo with the deterministic fake host."""

    async def run() -> None:
        runtime = HostRuntime(structured_generate=fake_structured_generate)
        config = AgentConfig(output_root=output, enable_libreoffice_preview=False)
        async with create_ppt_agent(runtime, config) as agent:
            result = await agent.start(
                "Create a presentation that demonstrates the PPT Expert workflow.",
                template_path=template,
                reference_images=reference_image or [],
            )
            while result["status"] == "interrupted":
                request = result["request"]
                if request["type"] == "intent_confirmation":
                    typer.echo("Intent needs confirmation:")
                    typer.echo(json.dumps(request["intent"], ensure_ascii=False, indent=2))
                    result = await agent.resume(result["thread_id"], {"action": "continue"})
                elif request["type"] == "recipe_confirmation":
                    recommended = request.get("recommended") or request.get("recipe_id")
                    typer.echo(f"Recommended: {recommended}")
                    if request.get("reason"):
                        typer.echo(request["reason"])
                    for option in request.get("options") or []:
                        mark = " [recommended]" if option.get("recommended") else ""
                        typer.echo(f"  {option['id']}{mark} — {option['label']}")
                    action = recipe or typer.prompt("Choose style", default=str(recommended))
                    result = await agent.resume(result["thread_id"], {"action": action})
                elif request["type"] == "delivery_confirmation":
                    typer.echo(
                        "Package valid"
                        if request["validation"]["valid"]
                        else "Package has issues"
                    )
                    if request.get("montage_path"):
                        typer.echo(f"  {request['montage_path']}")
                    action = delivery or typer.prompt(
                        "Approve delivery or revise", default="approve"
                    )
                    result = await agent.resume(
                        result["thread_id"], {"action": action}
                    )
                else:
                    raise RuntimeError(f"Unsupported interrupt: {request['type']}")
            typer.echo(json.dumps(result, ensure_ascii=False, indent=2))

    asyncio.run(run())


@app.command()
def benchmark(
    output: Annotated[Path, typer.Option(help="Output directory")] = Path(
        "outputs/strategy-benchmark"
    ),
) -> None:
    """Render the nine-slide strategy acceptance fixture and score it."""
    from ppt_expert.benchmarks import STRATEGY_DESIGN, strategy_benchmark_pages
    from ppt_expert.models import OutlinePage
    from ppt_expert.quality import score_deck, write_quality_report

    output.mkdir(parents=True, exist_ok=True)
    pages = strategy_benchmark_pages()
    path = output / "strategy-benchmark.pptx"
    render_presentation(pages, STRATEGY_DESIGN, {}, path, AgentConfig())
    outline = OutlinePlan(
        title="Strategy benchmark",
        pages=[
            OutlinePage(number=page.number, title=page.title, core_content=page.content)
            for page in pages
        ],
    )
    report = validate_presentation(path, outline, pages, STRATEGY_DESIGN, {})
    write_validation_report(report, output)
    quality = score_deck(pages, STRATEGY_DESIGN, vision_available=False)
    write_quality_report(quality, output)
    typer.echo(f"{'PASS' if report.valid and quality.score >= 90 else 'FAIL'}: {path}")
    typer.echo(f"Quality {quality.score} ({quality.delivery})")
    if not report.valid or quality.score < 90:
        raise typer.Exit(code=1)


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
    native_edit = _native_edit(project)
    report = validate_presentation(
        pptx_files[0], outline, story, design, image_paths, native_edit=native_edit
    )
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
    template_path = _template_path(project)
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


def _template_marker(project: Path) -> dict:
    marker = project / "template.json"
    if not marker.exists():
        return {}
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _native_edit(project: Path) -> bool:
    return _template_marker(project).get("mode") == "native_edit"


def _template_path(project: Path) -> str | None:
    path = _template_marker(project).get("path")
    return str(path) if path else None


def _is_build_input(project: Path, changed: Path) -> bool:
    return changed.name in {
        "story.json",
        "design.json",
        "template.json",
        "references.json",
        "reference-selection.json",
    } or (
        changed.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        and (project / "assets") in changed.parents
    )


if __name__ == "__main__":
    app()
