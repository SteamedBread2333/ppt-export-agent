from pathlib import Path

import pytest

from ppt_expert.environment import survey_environment
from ppt_expert.tools import locate_soffice, require_preview_tools


def test_survey_requires_soffice_and_pdftoppm() -> None:
    soffice, pdftoppm = require_preview_tools()
    report = survey_environment()
    assert soffice
    assert pdftoppm
    assert report.visual_review == "full"
    assert report.soffice is True
    assert report.pdftoppm is True


def test_missing_tools_fail_instead_of_degrading(monkeypatch) -> None:
    monkeypatch.setattr("ppt_expert.tools.shutil.which", lambda _name: None)
    monkeypatch.setattr("ppt_expert.tools._is_executable", lambda _path: False)
    with pytest.raises(RuntimeError, match="Montage review requires"):
        survey_environment()


def test_missing_tools_point_at_bootstrap(monkeypatch) -> None:
    monkeypatch.setattr("ppt_expert.tools.shutil.which", lambda _name: None)
    monkeypatch.setattr("ppt_expert.tools._is_executable", lambda _path: False)
    with pytest.raises(RuntimeError, match="bootstrap.sh"):
        require_preview_tools()


def test_locate_soffice_uses_standard_install_paths(monkeypatch, tmp_path: Path) -> None:
    binary = tmp_path / "soffice"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setattr("ppt_expert.tools.shutil.which", lambda _name: None)
    monkeypatch.setattr("ppt_expert.tools._SOFFICE_PATHS", (binary,))
    assert locate_soffice() == str(binary)
