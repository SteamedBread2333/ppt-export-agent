from ppt_expert.models import OutlinePage, OutlinePlan
from ppt_expert.planning import extract_evidence


def test_evidence_comes_from_outline() -> None:
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
    evidence = extract_evidence(outline)
    assert evidence.items[0].kind == "metric"
    assert evidence.items[0].value == 36.8
