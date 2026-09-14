from worker.jobs import process_issue_event


def make_payload(action: str = "opened") -> dict:
    return {
        "action": action,
        "issue": {"number": 42, "title": "Something is broken"},
        "repository": {"full_name": "acme/widgets"},
    }


def test_processes_well_formed_event():
    result = process_issue_event("issues", make_payload())
    assert result == {
        "repo": "acme/widgets",
        "issue_number": 42,
        "status": "not_implemented",
    }


def test_skips_payload_missing_issue():
    payload = make_payload()
    del payload["issue"]

    result = process_issue_event("issues", payload)

    assert result["status"] == "invalid_payload"


def test_skips_payload_missing_repository():
    payload = make_payload()
    del payload["repository"]

    result = process_issue_event("issues", payload)

    assert result["status"] == "invalid_payload"
