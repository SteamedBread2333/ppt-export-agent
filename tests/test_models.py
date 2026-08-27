import pytest
from pydantic import ValidationError

from ppt_expert.models import OutlinePage, OutlinePlan, StyleOption


def test_outline_requires_contiguous_pages() -> None:
    with pytest.raises(ValidationError):
        OutlinePlan(
            title="bad",
            pages=[
                OutlinePage(number=1, title="one", core_content=["a"]),
                OutlinePage(number=3, title="three", core_content=["b"]),
            ],
        )


def test_style_normalizes_hex_colors() -> None:
    style = StyleOption(
        key="A",
        name="test",
        mood="test",
        primary="#abcdef",
        secondary="#123456",
        background="#ffffff",
        text="#111111",
        accent="#fedcba",
    )
    assert style.primary == "#ABCDEF"
