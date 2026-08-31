from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path

from PIL import Image

from ppt_expert.tools import require_preview_tools


def render_previews(
    pptx_path: str | Path,
    output_dir: str | Path,
    *,
    dpi: int = 110,
) -> list[str]:
    executable, _converter = require_preview_tools()
    source = Path(pptx_path).expanduser().resolve()
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    profile = destination / ".lo-profile"
    profile.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            executable,
            "--headless",
            "--norestore",
            "--nolockcheck",
            "--nodefault",
            "--nofirststartwizard",
            f"-env:UserInstallation={profile.resolve().as_uri()}",
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
        env=os.environ.copy(),
    )
    pdf = destination / f"{source.stem}.pdf"
    if result.returncode != 0 or not pdf.exists():
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"LibreOffice failed to convert {source.name} to PDF: {detail}")
    pngs = rasterize_pdf(pdf, destination, dpi=dpi, prefix="pg")
    return [str(pdf.resolve()), *pngs]


def rasterize_pdf(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    dpi: int,
    prefix: str,
    first_page: int | None = None,
    last_page: int | None = None,
) -> list[str]:
    _soffice, converter = require_preview_tools()
    pdf = Path(pdf_path).expanduser().resolve()
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if not pdf.exists():
        raise RuntimeError(f"PDF does not exist: {pdf}")
    command = [converter, "-png", "-r", str(dpi)]
    if first_page is not None:
        command.extend(["-f", str(first_page)])
    if last_page is not None:
        command.extend(["-l", str(last_page)])
    command.extend([str(pdf), str(destination / prefix)])
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=120)
    pngs = _pngs(destination, prefix)
    if result.returncode != 0 or not pngs:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"pdftoppm failed to rasterize {pdf.name}: {detail}")
    return pngs


def render_montage(
    pptx_path: str | Path,
    output_dir: str | Path,
    *,
    dpi: int = 70,
) -> tuple[str, str]:
    paths = render_previews(pptx_path, output_dir, dpi=dpi)
    pdf = next(path for path in paths if path.endswith(".pdf"))
    images = [path for path in paths if path.endswith(".png")]
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
    for path in images:
        Path(path).unlink(missing_ok=True)
    return str(out.resolve()), pdf


def render_representative_pages(
    pdf_path: str | Path,
    output_dir: str | Path,
    page_numbers: list[int],
    *,
    dpi: int = 130,
) -> list[str]:
    if not page_numbers:
        raise RuntimeError("Representative page numbers are required for montage review")
    destination = Path(output_dir).expanduser().resolve()
    written: list[str] = []
    for number in page_numbers:
        written.extend(
            rasterize_pdf(
                pdf_path,
                destination,
                dpi=dpi,
                prefix=f"hi-pg{number}",
                first_page=number,
                last_page=number,
            )
        )
    return written


def cleanup_render_intermediates(output_dir: str | Path) -> None:
    folder = Path(output_dir)
    for pattern in ("pg-*.png", "hi-pg*.png"):
        for path in folder.glob(pattern):
            path.unlink(missing_ok=True)


def _pngs(destination: Path, prefix: str) -> list[str]:
    exact = destination / f"{prefix}.png"
    matches = sorted(destination.glob(f"{prefix}-*.png"))
    if exact.exists():
        matches = [exact, *[path for path in matches if path != exact]]
    return [str(path.resolve()) for path in matches]
