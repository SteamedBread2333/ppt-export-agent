from ppt_expert.models import IntentOutline, OutlinePlan, StoryDraft
from ppt_expert.prompts import parse_prompt, repair_prompt, story_design_prompt


def test_parse_prompt_is_a_single_slot_and_outline_task() -> None:
    prompt = parse_prompt("Create a 10-slide CIO briefing on H2 allocation.")
    assert "User input:" in prompt
    assert "Never invent palette" not in prompt
    assert "Production foundations:" not in prompt
    assert "slide-by-slide outline" in prompt


def test_story_prompt_omits_empty_fields() -> None:
    prompt = story_design_prompt(
        {"title": "Deck", "audience": "", "pages": [{"number": 1, "title": "Cover", "core_content": ["Go"]}]},
        brief={"recipe_id": "consulting", "mixing_note": ""},
        evidence=[{"id": "p1.1", "kind": "claim", "statement": "Go", "unit": "", "source": None}],
    )
    assert '"audience"' not in prompt
    assert '"mixing_note"' not in prompt
    assert '"unit"' not in prompt
    assert "Do not invent colors" in prompt


def test_repair_prompt_sends_failing_pages_not_design() -> None:
    story = [
        {
            "number": 1,
            "title": "Cover",
            "role": "cover",
            "family": "cover",
            "takeaway": "Start",
            "chart": {"categories": ["A", "B"], "series": [{"name": "Focus", "values": [1, 2]}]},
        },
        {
            "number": 2,
            "title": "Overflow",
            "role": "context",
            "content": ["x" * 40],
            "takeaway": "Fix density",
        },
    ]
    prompt = repair_prompt(
        {"title": "Deck", "pages": [{"number": 1, "title": "Cover"}, {"number": 2, "title": "Overflow"}]},
        story,
        [{"code": "overflow", "page": 2, "severity": "error"}],
        pages=[2],
    )
    assert "Repair only slides [2]" in prompt
    assert '"repair"' in prompt
    assert '"locked"' in prompt
    assert "Focus" not in prompt
    assert "DESIGN" not in prompt
    assert "Fix density" in prompt


def test_generation_schemas_exclude_design_spec() -> None:
    assert "design" not in StoryDraft.model_fields
    assert "intent" in IntentOutline.model_fields
    assert "outline" in IntentOutline.model_fields
    assert "pages" in OutlinePlan.model_fields
