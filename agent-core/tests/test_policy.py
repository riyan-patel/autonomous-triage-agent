from agent_core.policy import DecisionAction, decide
from agent_core.schema import IssueType, Severity, TriageOutput


def make_output(confidence: float, duplicate_of: int | None = None) -> TriageOutput:
    return TriageOutput(
        summary="x", type=IssueType.BUG, severity=Severity.MEDIUM,
        labels=["bug"], duplicate_of=duplicate_of, draft_reply="thanks", confidence=confidence,
    )


def test_low_confidence_escalates():
    decision = decide(make_output(0.5), confidence_threshold=0.85)
    assert decision.action == DecisionAction.ESCALATE


def test_high_confidence_acts():
    decision = decide(make_output(0.9), confidence_threshold=0.85)
    assert decision.action == DecisionAction.ACT


def test_confidence_exactly_at_threshold_acts():
    decision = decide(make_output(0.85), confidence_threshold=0.85)
    assert decision.action == DecisionAction.ACT


def test_duplicate_link_needs_extra_margin():
    # 0.87 clears the bare 0.85 threshold but not the +0.1 duplicate margin.
    decision = decide(make_output(0.87, duplicate_of=12), confidence_threshold=0.85)
    assert decision.action == DecisionAction.ESCALATE


def test_duplicate_link_acts_with_enough_margin():
    decision = decide(make_output(0.97, duplicate_of=12), confidence_threshold=0.85)
    assert decision.action == DecisionAction.ACT
