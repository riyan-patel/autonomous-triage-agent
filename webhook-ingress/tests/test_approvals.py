from .conftest import INTERNAL_TOKEN


def test_execute_approval_requires_token(client):
    response = client.post("/internal/approvals/1/execute")
    assert response.status_code == 401


def test_execute_approval_rejects_wrong_token(client):
    response = client.post(
        "/internal/approvals/1/execute", headers={"X-Internal-Token": "wrong"}
    )
    assert response.status_code == 401


def test_execute_approval_enqueues_with_valid_token(client):
    response = client.post(
        "/internal/approvals/1/execute", headers={"X-Internal-Token": INTERNAL_TOKEN}
    )
    assert response.status_code == 202


def test_execute_approval_duplicate_request_is_noop(client):
    headers = {"X-Internal-Token": INTERNAL_TOKEN}
    first = client.post("/internal/approvals/5/execute", headers=headers)
    second = client.post("/internal/approvals/5/execute", headers=headers)

    assert first.status_code == 202
    assert second.status_code == 202


def test_execute_approval_endpoint_closed_when_token_unset(client):
    from app import config

    config.settings.internal_api_token = ""
    try:
        response = client.post(
            "/internal/approvals/1/execute", headers={"X-Internal-Token": ""}
        )
        assert response.status_code == 401
    finally:
        config.settings.internal_api_token = INTERNAL_TOKEN
