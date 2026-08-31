from ppt_expert.setup_tools import doctor_report


def test_doctor_report_lists_preview_tools() -> None:
    report = doctor_report()
    assert report["python"]
    assert "(3." in report["python"]
    assert report["soffice"]
    assert report["pdftoppm"]
    assert report["pillow"] == "ok"
