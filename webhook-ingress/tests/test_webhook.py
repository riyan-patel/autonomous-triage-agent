from .conftest import issue_payload, sign


def _headers(signature: str, event: str = "issues", delivery: str = "delivery-1") -> dict:
    return {
        "X-Hub-Signature-256": signature,
        "X-GitHub-Event": event,
        "X-GitHub-Delivery": delivery,
        "Content-Type": "application/json",
    }


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rejects_invalid_signature(client, signed_request):
    body, _ = signed_request(issue_payload())
    response = client.post(
        "/webhooks/github",
        content=body,
        headers=_headers("sha256=deadbeef"),
    )
    assert response.status_code == 401


def test_rejects_missing_signature(client):
    response = client.post(
        "/webhooks/github",
        content=b"{}",
        headers={"X-GitHub-Event": "issues", "X-GitHub-Delivery": "d1"},
    )
    assert response.status_code == 401


def test_accepts_valid_opened_issue(client, signed_request):
    body, signature = signed_request(issue_payload("opened"))
    response = client.post("/webhooks/github", content=body, headers=_headers(signature))
    assert response.status_code == 202


def test_ignores_unhandled_action(client, signed_request):
    body, signature = signed_request(issue_payload("closed"))
    response = client.post("/webhooks/github", content=body, headers=_headers(signature))
    assert response.status_code == 202


def test_ignores_non_issues_event(client, signed_request):
    body, signature = signed_request(issue_payload("opened"))
    response = client.post(
        "/webhooks/github",
        content=body,
        headers=_headers(signature, event="ping"),
    )
    assert response.status_code == 202


def test_duplicate_delivery_is_noop(client, signed_request):
    body, signature = signed_request(issue_payload("opened"))
    headers = _headers(signature, delivery="dup-1")

    first = client.post("/webhooks/github", content=body, headers=headers)
    second = client.post("/webhooks/github", content=body, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 202


def test_missing_delivery_id_rejected(client, signed_request):
    body, signature = signed_request(issue_payload("opened"))
    headers = _headers(signature)
    del headers["X-GitHub-Delivery"]
    response = client.post("/webhooks/github", content=body, headers=headers)
    assert response.status_code == 400
