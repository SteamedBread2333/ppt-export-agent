from __future__ import annotations

from ppt_expert.models import StoryPage


def merge_repaired_pages(
    current: list[StoryPage],
    proposed: list[StoryPage],
    page_numbers: list[int],
) -> list[StoryPage]:
    """Keep locked slides and replace only the pages named in the repair scope."""
    if not page_numbers:
        return proposed
    replacements = {page.number: page for page in proposed}
    merged: list[StoryPage] = []
    for page in current:
        replacement = replacements.get(page.number)
        if page.number in page_numbers and replacement is not None:
            merged.append(
                replacement.model_copy(
                    update={
                        "number": page.number,
                        "title": page.title,
                        "section": page.section,
                    }
                )
            )
        else:
            merged.append(page)
    return merged
