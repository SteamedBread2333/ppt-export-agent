from __future__ import annotations

from pathlib import Path

from ppt_expert.models import EnvironmentReport
from ppt_expert.tools import require_preview_tools


def survey_environment() -> EnvironmentReport:
    require_preview_tools()
    try:
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Montage review requires Pillow") from exc
    return EnvironmentReport(
        soffice=True,
        pdftoppm=True,
        pil=True,
        visual_review="full",
    )


def write_environment(report: EnvironmentReport, project_dir: str | Path) -> str:
    path = Path(project_dir) / "environment.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return str(path.resolve())
