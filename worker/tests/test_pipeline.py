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


def noop_audit(delivery_id, repo, issue_number, output, decision, dry_run):
    pass


def test_run_triage_acts_on_high_confidence():
    llm = FakeLLMClient(make_output(0.95))
    acted_with = []

    result = run_triage(
        make_payload(),
        delivery_id="delivery-1",
        retrieval_fn=lambda repo, issue_number, title, body, state: [],
        llm_client=llm,
        act_fn=lambda repo, issue_number, output: acted_with.append((repo, issue_number, output)),
        audit_fn=noop_audit,
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
        delivery_id="delivery-2",
        retrieval_fn=lambda repo, issue_number, title, body, state: [],
        llm_client=llm,
        act_fn=lambda repo, issue_number, output: acted_with.append((repo, issue_number, output)),
        audit_fn=noop_audit,
    )

    assert result.status == "escalated"
    assert acted_with == []


def test_run_triage_passes_retrieval_results_into_prompt():
    from agent_core.types import SimilarIssueContext

    llm = FakeLLMClient(make_output(0.9))

    run_triage(
        make_payload(),
        delivery_id="delivery-3",
        retrieval_fn=lambda repo, issue_number, title, body, state: [
            SimilarIssueContext(issue_number=7, title="Near duplicate crash", state="open", distance=0.05)
        ],
        llm_client=llm,
        act_fn=lambda repo, issue_number, output: None,
        audit_fn=noop_audit,
    )

    assert "Near duplicate crash" in llm.last_prompt
    assert "#7" in llm.last_prompt


def test_run_triage_calls_audit_fn_with_decision():
    llm = FakeLLMClient(make_output(0.95))
    audit_calls = []

    def capture_audit(delivery_id, repo, issue_number, output, decision, dry_run):
        audit_calls.append((delivery_id, repo, issue_number, decision.action.value, dry_run))

    run_triage(
        make_payload(),
        delivery_id="delivery-4",
        retrieval_fn=lambda repo, issue_number, title, body, state: [],
        llm_client=llm,
        act_fn=lambda repo, issue_number, output: None,
        audit_fn=capture_audit,
    )

    assert audit_calls == [("delivery-4", "acme/widgets", 42, "act", True)]
