from ppt_expert.environment import survey_environment


def test_missing_soffice_marks_visual_review_degraded(monkeypatch) -> None:
    monkeypatch.setattr("ppt_expert.environment.shutil.which", lambda _name: None)
    report = survey_environment(enable_visual=True)
    assert report.visual_review == "degraded"
    assert report.soffice is False


def test_disabled_preview_is_degraded_even_if_tools_exist() -> None:
    report = survey_environment(enable_visual=False)
    assert report.visual_review == "degraded"
