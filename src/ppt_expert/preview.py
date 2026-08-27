from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def render_previews(pptx_path: str | Path, output_dir: str | Path) -> list[str]:
    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if executable is None:
        return []
    source = Path(pptx_path).expanduser().resolve()
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            executable,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(destination),
            str(source),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    pdf = destination / f"{source.stem}.pdf"
    if result.returncode != 0 or not pdf.exists():
        return []

    previews = [str(pdf.resolve())]
    converter = shutil.which("pdftoppm")
    if converter:
        prefix = destination / source.stem
        image_result = subprocess.run(
            [converter, "-png", "-r", "110", str(pdf), str(prefix)],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if image_result.returncode == 0:
            previews.extend(str(path.resolve()) for path in sorted(destination.glob(f"{source.stem}-*.png")))
    return previews


def render_pdf_preview(pptx_path: str | Path, output_dir: str | Path) -> str | None:
    """Backward-compatible helper returning only the generated PDF."""
    return next(
        (path for path in render_previews(pptx_path, output_dir) if path.endswith(".pdf")),
        None,
    )
