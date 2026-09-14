from agent_core.pipeline import run_triage
from agent_core.policy import DecisionAction
from agent_core.schema import IssueType, Severity, TriageOutput
from agent_core.types import IssueInput, LabelSpec

from .fakes import FakeLLMClient


def make_issue() -> IssueInput:
    return IssueInput(repo_full_name="acme/widgets", issue_number=1, title="Crash on launch", body="Stack trace...")


def test_run_triage_builds_prompt_and_applies_policy():
    output = TriageOutput(
        summary="Crash on launch", type=IssueType.BUG, severity=Severity.HIGH,
        labels=["bug"], draft_reply="Thanks, looking into it.", confidence=0.92,
    )
    llm = FakeLLMClient(output)

    run = run_triage(
        llm, make_issue(),
        label_taxonomy=[LabelSpec("bug")],
        similar_issues=[],
        confidence_threshold=0.85,
    )

    assert run.output == output
    assert run.decision.action == DecisionAction.ACT
    assert "Crash on launch" in llm.last_prompt


def test_run_triage_escalates_low_confidence():
    output = TriageOutput(
        summary="Unclear report", type=IssueType.QUESTION, severity=Severity.LOW,
        draft_reply="Could you share more details?", confidence=0.4,
    )
    llm = FakeLLMClient(output)

    run = run_triage(
        llm, make_issue(),
        label_taxonomy=[],
        similar_issues=[],
        confidence_threshold=0.85,
    )

    assert run.decision.action == DecisionAction.ESCALATE
