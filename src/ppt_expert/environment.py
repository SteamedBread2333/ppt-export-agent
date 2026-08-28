from __future__ import annotations

import shutil
from pathlib import Path

from ppt_expert.models import EnvironmentReport


def survey_environment(*, enable_visual: bool = True) -> EnvironmentReport:
    soffice = shutil.which("soffice") is not None or shutil.which("libreoffice") is not None
    pdftoppm = shutil.which("pdftoppm") is not None
    magick = shutil.which("magick") is not None or shutil.which("convert") is not None
    try:
        from PIL import Image  # noqa: F401

        pil = True
    except ImportError:
        pil = False
    visual = "full" if enable_visual and soffice and pdftoppm and pil else "degraded"
    return EnvironmentReport(
        soffice=soffice,
        pdftoppm=pdftoppm,
        magick=magick,
        pil=pil,
        visual_review=visual,
    )


def write_environment(report: EnvironmentReport, project_dir: str | Path) -> str:
    path = Path(project_dir) / "environment.json"
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return str(path.resolve())
