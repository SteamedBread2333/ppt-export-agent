from ppt_expert.models import LayoutType, SlideFamily, StoryPage
from ppt_expert.repair import merge_repaired_pages


def _page(number: int, title: str, **overrides) -> StoryPage:
    payload = {
        "number": number,
        "title": title,
        "content": [title],
        "visual_direction": title,
        "layout": LayoutType.TEXT,
        "family": SlideFamily.TEXT,
    }
    payload.update(overrides)
    return StoryPage(**payload)


def test_merge_repaired_pages_replaces_only_named_slides() -> None:
    current = [_page(1, "Cover"), _page(2, "Overflow")]
    proposed = [_page(1, "Cover rewritten"), _page(2, "Fixed")]
    merged = merge_repaired_pages(current, proposed, [2])
    assert merged[0].title == "Cover"
    assert merged[1].title == "Overflow"
    assert merged[1].content == ["Fixed"]
