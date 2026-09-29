import pytest

from worker import pipeline


class FakeGithubClient:
    """Minimal stand-in for GitHubClient, only implementing the surface
    _default_label_taxonomy touches (list_labels) plus a non-None
    `_github` so pipeline's "no token configured" guard doesn't short-circuit."""

    def __init__(self, labels: list[dict]) -> None:
        self._github = object()
        self.labels = labels

    def list_labels(self, repo):
        return self.labels


@pytest.fixture(autouse=True)
def reset_label_taxonomy_cache():
    pipeline._label_taxonomy_cache.clear()
    yield
    pipeline._label_taxonomy_cache.clear()


def test_default_label_taxonomy_uses_real_repo_labels():
    from mcp_server import server

    server.set_client(
        FakeGithubClient([{"name": "triage", "description": "Needs a first look"}])
    )
    try:
        taxonomy = pipeline._default_label_taxonomy("acme/widgets")
    finally:
        server.set_client(server._build_default_client())

    assert [label.name for label in taxonomy] == ["triage"]
    assert taxonomy[0].description == "Needs a first look"


def test_default_label_taxonomy_falls_back_when_repo_has_no_labels():
    from mcp_server import server

    server.set_client(FakeGithubClient([]))
    try:
        taxonomy = pipeline._default_label_taxonomy("acme/widgets")
    finally:
        server.set_client(server._build_default_client())

    assert taxonomy == pipeline.DEFAULT_LABEL_TAXONOMY


def test_default_label_taxonomy_falls_back_when_no_token_configured():
    # No set_client() override here - the real default client has no
    # GITHUB_TOKEN in the test environment, so _github is None.
    taxonomy = pipeline._default_label_taxonomy("acme/widgets")

    assert taxonomy == pipeline.DEFAULT_LABEL_TAXONOMY
