from ppt_expert.models import OutlinePage, OutlinePlan
from ppt_expert.planning import build_brief, extract_evidence


def test_brief_and_evidence_come_from_outline() -> None:
    outline = OutlinePlan(
        title="2026H2 strategy outlook",
        audience="CIO",
        purpose="Decide H2 allocation",
        pages=[
            OutlinePage(
                number=1,
                title="Cover",
                core_content=["Consensus upside 36.8%"],
            )
        ],
    )
    brief = build_brief(outline, "Create a strategy deck")
    evidence = extract_evidence(outline)
    assert brief.primary_archetype.value == "strategy"
    assert not brief.needs_confirmation()
    assert evidence.items[0].kind == "metric"
    assert evidence.items[0].value == 36.8
