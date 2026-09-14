from unittest.mock import patch

from worker.jobs import process_issue_event
from worker.pipeline import TriageResult


def make_payload(action: str = "opened") -> dict:
    return {
        "action": action,
        "issue": {"number": 42, "title": "Something is broken"},
        "repository": {"full_name": "acme/widgets"},
    }


def test_processes_well_formed_event():
    # jobs.py's own job is extracting fields + delegating to run_triage and
    # shaping the result dict - the full retrieval/agent-core/mcp-server
    # glue is covered separately in tests/test_pipeline.py with fakes, so
    # here we just stub run_triage out.
    canned = TriageResult(repo="acme/widgets", issue_number=42, status="acted", confidence=0.92, reasons=["ok"])
    with patch("worker.jobs.run_triage", return_value=canned) as mock_run_triage:
        result = process_issue_event("issues", make_payload(), delivery_id="delivery-1")

    mock_run_triage.assert_called_once_with(make_payload(), delivery_id="delivery-1")
    assert result == {
        "repo": "acme/widgets",
        "issue_number": 42,
        "status": "acted",
        "confidence": 0.92,
    }


def test_skips_payload_missing_issue():
    payload = make_payload()
    del payload["issue"]

    result = process_issue_event("issues", payload, delivery_id="delivery-2")

    assert result["status"] == "invalid_payload"


def test_skips_payload_missing_repository():
    payload = make_payload()
    del payload["repository"]

    result = process_issue_event("issues", payload, delivery_id="delivery-3")

    assert result["status"] == "invalid_payload"
