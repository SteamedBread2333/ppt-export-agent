import pytest
from pydantic import ValidationError

from ppt_expert.models import DesignSpec, OutlinePage, OutlinePlan


def test_outline_requires_contiguous_pages() -> None:
    with pytest.raises(ValidationError):
        OutlinePlan(
            title="bad",
            pages=[
                OutlinePage(number=1, title="one", core_content=["a"]),
                OutlinePage(number=3, title="three", core_content=["b"]),
            ],
        )


def test_design_normalizes_optional_hex_colors() -> None:
    design = DesignSpec(
        style_name="Deep Blue",
        mood="Measured",
        primary="#16324F",
        secondary="#2E6F95",
        background="#F4F8FB",
        text="#102A43",
        accent="#F29E4C",
        illustration_style="Flat",
        muted="#abcdef",
    )
    assert design.muted == "#ABCDEF"
