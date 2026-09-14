from worker.pipeline import run_triage

from agent_core.llm import LLMClient
from agent_core.schema import IssueType, Severity, TriageOutput


class FakeLLMClient(LLMClient):
    def __init__(self, output: TriageOutput) -> None:
        self.output = output
        self.last_prompt: str | None = None

    def generate_triage(self, user_prompt: str) -> TriageOutput:
        self.last_prompt = user_prompt
        return self.output


def make_payload() -> dict:
    return {
        "action": "opened",
        "issue": {"number": 42, "title": "Crash on launch", "body": "Stack trace...", "state": "open"},
        "repository": {"full_name": "acme/widgets"},
    }


def make_output(confidence: float, **overrides) -> TriageOutput:
    defaults = dict(
        summary="Crash on launch", type=IssueType.BUG, severity=Severity.HIGH,
        labels=["bug"], draft_reply="Thanks, looking into it.", confidence=confidence,
    )
    defaults.update(overrides)
    return TriageOutput(**defaults)


def test_run_triage_acts_on_high_confidence():
    llm = FakeLLMClient(make_output(0.95))
    acted_with = []

    result = run_triage(
        make_payload(),
        retrieval_fn=lambda repo, issue_number, title, body, state: [],
        llm_client=llm,
        act_fn=lambda repo, issue_number, output: acted_with.append((repo, issue_number, output)),
    )

    assert result.status == "acted"
    assert result.repo == "acme/widgets"
    assert result.issue_number == 42
    assert len(acted_with) == 1
    assert acted_with[0][2].labels == ["bug"]
    assert "Crash on launch" in llm.last_prompt


def test_run_triage_escalates_without_acting():
    llm = FakeLLMClient(make_output(0.4))
    acted_with = []

    result = run_triage(
        make_payload(),
        retrieval_fn=lambda repo, issue_number, title, body, state: [],
        llm_client=llm,
        act_fn=lambda repo, issue_number, output: acted_with.append((repo, issue_number, output)),
    )

    assert result.status == "escalated"
    assert acted_with == []


def test_run_triage_passes_retrieval_results_into_prompt():
    from agent_core.types import SimilarIssueContext

    llm = FakeLLMClient(make_output(0.9))

    run_triage(
        make_payload(),
        retrieval_fn=lambda repo, issue_number, title, body, state: [
            SimilarIssueContext(issue_number=7, title="Near duplicate crash", state="open", distance=0.05)
        ],
        llm_client=llm,
        act_fn=lambda repo, issue_number, output: None,
    )

    assert "Near duplicate crash" in llm.last_prompt
    assert "#7" in llm.last_prompt
