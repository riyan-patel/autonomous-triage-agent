"""Integration test proving the cross-package wiring (worker -> retrieval ->
agent-core -> mcp-server, across sibling hyphenated directories via the
sys.path bootstrap in pipeline.py) actually works, not just that each
package's own unit tests pass in isolation.

Uses the real retrieval layer (real Postgres + real local embedder) and
the real mcp-server tool layer (dry-run by default, so safe with no
GitHub token) - only the LLM call is faked, since there's no
ANTHROPIC_API_KEY in this environment. Skips cleanly if Postgres isn't
reachable, matching retrieval/tests/conftest.py's pattern.
"""

import uuid

import pytest
from sqlalchemy import text

from worker.pipeline import _default_retrieval, get_engine, run_triage

from agent_core.llm import LLMClient
from agent_core.schema import IssueType, Severity, TriageOutput


class FakeLLMClient(LLMClient):
    def __init__(self, output: TriageOutput) -> None:
        self.output = output

    def generate_triage(self, user_prompt: str) -> TriageOutput:
        return self.output


@pytest.fixture
def live_repo():
    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM issues LIMIT 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres with the 0001_init.sql schema isn't reachable: {exc}")

    repo = f"acme/pipeline-live-{uuid.uuid4().hex[:8]}"
    yield repo
    with engine.begin() as conn:
        # actions.issue_id has no ON DELETE CASCADE, so audit rows go first.
        conn.execute(
            text("DELETE FROM actions WHERE issue_id IN (SELECT id FROM issues WHERE repo_full_name = :repo)"),
            {"repo": repo},
        )
        conn.execute(text("DELETE FROM issues WHERE repo_full_name = :repo"), {"repo": repo})


def test_full_pipeline_acts_through_real_retrieval_and_mcp_tools(live_repo):
    payload = {
        "issue": {"number": 1, "title": "Crash on launch", "body": "Stack trace shows a null pointer.", "state": "open"},
        "repository": {"full_name": live_repo},
    }
    llm = FakeLLMClient(
        TriageOutput(
            summary="Crash on launch", type=IssueType.BUG, severity=Severity.HIGH,
            labels=["bug"], draft_reply="Thanks for the report, looking into it.", confidence=0.95,
        )
    )

    result = run_triage(payload, delivery_id="live-test-delivery-1", retrieval_fn=_default_retrieval, llm_client=llm)

    assert result.status == "acted"
    assert result.repo == live_repo
    assert result.confidence == 0.95

    # the default audit_fn should have written a real row to actions.
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT delivery_id, action_type, confidence, dry_run FROM actions "
                 "WHERE issue_id IN (SELECT id FROM issues WHERE repo_full_name = :repo)"),
            {"repo": live_repo},
        ).one()
    assert row.delivery_id == "live-test-delivery-1"
    assert row.action_type == "act"
    assert row.confidence == pytest.approx(0.95)
    assert row.dry_run is True
