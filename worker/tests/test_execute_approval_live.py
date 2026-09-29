"""Integration test for the dashboard-approve execution path (worker.pipeline
.execute_approval), proving the real DB read/write wiring - reviews ->
actions -> issues joins, and the idempotent second "approved_execute" audit
row - works against real Postgres. mcp-server's act call is faked (no
GitHub token needed), same posture as test_pipeline_live.py.
"""

import uuid

import pytest
from sqlalchemy import text

from worker.pipeline import execute_approval, get_engine, get_session_factory

from agent_core.schema import IssueType, Severity, TriageOutput
from retrieval.models import Action, Issue, Review


@pytest.fixture
def live_review():
    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM reviews LIMIT 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres with the 0002_add_reviews.sql schema isn't reachable: {exc}")

    repo = f"acme/execute-approval-live-{uuid.uuid4().hex[:8]}"
    session = get_session_factory(engine)()
    output = TriageOutput(
        summary="Crash on launch", type=IssueType.BUG, severity=Severity.HIGH,
        labels=["bug"], draft_reply="Thanks, looking into it.", confidence=0.6,
    )
    issue = Issue(repo_full_name=repo, issue_number=1, title="Crash on launch", body="...")
    session.add(issue)
    session.flush()
    action = Action(
        issue_id=issue.id, delivery_id="live-escalate-1", action_type="escalate",
        payload=output.model_dump(mode="json"), confidence=0.6, dry_run=True,
    )
    session.add(action)
    session.flush()
    action_id = action.id
    session.commit()
    session.close()

    yield repo, action_id

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM reviews WHERE action_id IN "
                 "(SELECT id FROM actions WHERE issue_id IN (SELECT id FROM issues WHERE repo_full_name = :repo))"),
            {"repo": repo},
        )
        conn.execute(
            text("DELETE FROM actions WHERE issue_id IN (SELECT id FROM issues WHERE repo_full_name = :repo)"),
            {"repo": repo},
        )
        conn.execute(text("DELETE FROM issues WHERE repo_full_name = :repo"), {"repo": repo})


def _set_review_decision(action_id: int, decision: str) -> None:
    session = get_session_factory(get_engine())()
    session.add(Review(action_id=action_id, decision=decision))
    session.commit()
    session.close()


def test_execute_approval_calls_act_fn_and_records_audit_row(live_review):
    repo, action_id = live_review
    _set_review_decision(action_id, "approved")
    acted_with = []

    result = execute_approval(action_id, act_fn=lambda r, n, output: acted_with.append((r, n, output)))

    assert result["status"] == "executed"
    assert acted_with == [(repo, 1, acted_with[0][2])]
    assert acted_with[0][2].labels == ["bug"]

    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT delivery_id, action_type FROM actions WHERE issue_id IN "
                 "(SELECT id FROM issues WHERE repo_full_name = :repo) AND action_type = 'approved_execute'"),
            {"repo": repo},
        ).one()
    assert row.delivery_id == f"approval-{action_id}"


def test_execute_approval_is_idempotent(live_review):
    _, action_id = live_review
    _set_review_decision(action_id, "approved")

    first = execute_approval(action_id, act_fn=lambda r, n, output: None)
    acted_with = []
    second = execute_approval(action_id, act_fn=lambda r, n, output: acted_with.append((r, n)))

    assert first["status"] == "executed"
    assert second["status"] == "already_executed"
    assert acted_with == []  # act_fn was not called the second time


def test_execute_approval_skips_rejected_decision(live_review):
    _, action_id = live_review
    _set_review_decision(action_id, "rejected")
    acted_with = []

    result = execute_approval(action_id, act_fn=lambda r, n, output: acted_with.append((r, n)))

    assert result["status"] == "not_approved"
    assert acted_with == []


def test_execute_approval_no_review_yet(live_review):
    _, action_id = live_review
    acted_with = []

    result = execute_approval(action_id, act_fn=lambda r, n, output: acted_with.append((r, n)))

    assert result["status"] == "not_approved"
    assert acted_with == []
