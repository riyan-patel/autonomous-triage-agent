import hashlib
import hmac
import json

import fakeredis
import pytest
from fastapi.testclient import TestClient

WEBHOOK_SECRET = "test-secret"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", WEBHOOK_SECRET)

    from app import config, queue

    config.settings.github_webhook_secret = WEBHOOK_SECRET

    fake_conn = fakeredis.FakeStrictRedis()
    queue.get_redis_connection.cache_clear()
    queue.get_queue.cache_clear()
    monkeypatch.setattr(queue, "get_redis_connection", lambda: fake_conn)

    from app.main import app

    return TestClient(app)


def sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def issue_payload(action: str = "opened") -> dict:
    return {
        "action": action,
        "issue": {"number": 1, "title": "Something is broken", "body": "steps to repro..."},
        "repository": {"full_name": "acme/widgets"},
    }


@pytest.fixture
def signed_request():
    def _make(payload: dict):
        body = json.dumps(payload).encode()
        return body, sign(body)

    return _make
