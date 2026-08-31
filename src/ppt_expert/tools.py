from __future__ import annotations

import os
import shutil
from pathlib import Path

INSTALL_HINT = (
    "From a clone, run ./scripts/bootstrap.sh. "
    "After pip install, run: ppt-expert setup. "
    "macOS: brew install poppler && brew install --cask libreoffice. "
    "Debian/Ubuntu: sudo apt-get install -y libreoffice-impress poppler-utils. "
    "Fedora: sudo dnf install -y libreoffice poppler-utils."
)

_SOFFICE_NAMES = ("soffice", "libreoffice")
_SOFFICE_PATHS = (
    Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
    Path("/opt/homebrew/bin/soffice"),
    Path("/usr/local/bin/soffice"),
    Path("/usr/bin/soffice"),
    Path("/usr/bin/libreoffice"),
)
_PDFTOPPM_PATHS = (
    Path("/opt/homebrew/bin/pdftoppm"),
    Path("/usr/local/bin/pdftoppm"),
    Path("/usr/bin/pdftoppm"),
)


def locate_soffice() -> str | None:
    for name in _SOFFICE_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return _first_executable(_SOFFICE_PATHS)


def locate_pdftoppm() -> str | None:
    found = shutil.which("pdftoppm")
    if found:
        return found
    return _first_executable(_PDFTOPPM_PATHS)


def require_preview_tools() -> tuple[str, str]:
    """LibreOffice + pdftoppm are mandatory for montage review."""
    soffice = locate_soffice()
    pdftoppm = locate_pdftoppm()
    missing: list[str] = []
    if soffice is None:
        missing.append("LibreOffice (soffice)")
    if pdftoppm is None:
        missing.append("pdftoppm (poppler)")
    if missing:
        raise RuntimeError(
            "Montage review requires " + " and ".join(missing) + ". " + INSTALL_HINT
        )
    return soffice, pdftoppm


def _first_executable(candidates: tuple[Path, ...]) -> str | None:
    for path in candidates:
        if _is_executable(path):
            return str(path)
    return None


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)
