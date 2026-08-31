from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal

from ppt_expert.tools import INSTALL_HINT, locate_pdftoppm, locate_soffice, require_preview_tools

PackageKind = Literal["libreoffice", "poppler"]


def doctor_report() -> dict[str, str]:
    python = f"{sys.executable} ({sys.version.split()[0]})"
    try:
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Pillow is required. Re-run ./scripts/bootstrap.sh") from exc
    soffice, pdftoppm = require_preview_tools()
    return {
        "python": python,
        "soffice": soffice,
        "pdftoppm": pdftoppm,
        "pillow": "ok",
    }


def ensure_preview_tools() -> tuple[str, str]:
    soffice = locate_soffice()
    pdftoppm = locate_pdftoppm()
    if soffice is None:
        _install_package("libreoffice")
        soffice = locate_soffice()
    if pdftoppm is None:
        _install_package("poppler")
        pdftoppm = locate_pdftoppm()
    if soffice is None or pdftoppm is None:
        raise RuntimeError("Could not install montage tools. " + INSTALL_HINT)
    return soffice, pdftoppm


def _install_package(kind: PackageKind) -> None:
    system = sys.platform
    if system == "darwin":
        brew = _brew()
        if brew is None:
            raise RuntimeError(
                "Homebrew is required on macOS. Install it from https://brew.sh then re-run."
            )
        if kind == "poppler":
            _run([brew, "install", "poppler"])
        else:
            _run([brew, "install", "--cask", "libreoffice"])
        return
    if shutil.which("apt-get"):
        apt = ["sudo", "apt-get"] if os.geteuid() != 0 else ["apt-get"]
        _run([*apt, "update"])
        package = "poppler-utils" if kind == "poppler" else "libreoffice-impress"
        _run([*apt, "install", "-y", package])
        return
    if shutil.which("dnf"):
        dnf = ["sudo", "dnf"] if os.geteuid() != 0 else ["dnf"]
        package = "poppler-utils" if kind == "poppler" else "libreoffice"
        _run([*dnf, "install", "-y", package])
        return
    raise RuntimeError(INSTALL_HINT)


def _brew() -> str | None:
    found = shutil.which("brew")
    if found:
        return found
    for path in (Path("/opt/homebrew/bin/brew"), Path("/usr/local/bin/brew")):
        if path.is_file():
            return str(path)
    return None


def _run(command: list[str]) -> None:
    env = os.environ.copy()
    env.setdefault("HOMEBREW_NO_AUTO_UPDATE", "1")
    env.setdefault("NONINTERACTIVE", "1")
    result = subprocess.run(command, check=False, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}")
