from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image


def render_previews(
    pptx_path: str | Path,
    output_dir: str | Path,
    *,
    dpi: int = 110,
) -> list[str]:
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
        prefix = destination / "pg"
        image_result = subprocess.run(
            [converter, "-png", "-r", str(dpi), str(pdf), str(prefix)],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if image_result.returncode == 0:
            previews.extend(str(path.resolve()) for path in sorted(destination.glob("pg-*.png")))
    return previews


def render_montage(
    pptx_path: str | Path,
    output_dir: str | Path,
    *,
    dpi: int = 70,
) -> tuple[str, str]:
    paths = render_previews(pptx_path, output_dir, dpi=dpi)
    pdf = next((path for path in paths if path.endswith(".pdf")), "")
    images = [path for path in paths if path.endswith(".png")]
    if not images:
        return "", pdf
    tiles = [Image.open(path).convert("RGB") for path in images]
    columns = min(3, len(tiles))
    rows = max(1, math.ceil(len(tiles) / columns))
    cell_w, cell_h = tiles[0].size
    montage = Image.new("RGB", (columns * cell_w, rows * cell_h), (255, 255, 255))
    for index, tile in enumerate(tiles):
        montage.paste(tile, ((index % columns) * cell_w, (index // columns) * cell_h))
        tile.close()
    out = Path(output_dir) / "montage.png"
    montage.save(out)
    return str(out.resolve()), pdf


def render_representative_pages(
    pdf_path: str | Path,
    output_dir: str | Path,
    page_numbers: list[int],
    *,
    dpi: int = 130,
) -> list[str]:
    converter = shutil.which("pdftoppm")
    if converter is None or not page_numbers:
        return []
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for number in page_numbers:
        prefix = destination / f"hi-pg{number}"
        result = subprocess.run(
            [
                converter,
                "-png",
                "-r",
                str(dpi),
                "-f",
                str(number),
                "-l",
                str(number),
                str(pdf_path),
                str(prefix),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            continue
        written.extend(str(path.resolve()) for path in sorted(destination.glob(f"hi-pg{number}*.png")))
    return written


def render_pdf_preview(pptx_path: str | Path, output_dir: str | Path) -> str | None:
    return next(
        (path for path in render_previews(pptx_path, output_dir) if path.endswith(".pdf")),
        None,
    )


def cleanup_render_intermediates(output_dir: str | Path) -> None:
    folder = Path(output_dir)
    for pattern in ("pg-*.png", "hi-pg*.png"):
        for path in folder.glob(pattern):
            path.unlink(missing_ok=True)
