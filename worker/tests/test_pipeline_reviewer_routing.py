import pytest

from worker import pipeline

CODEOWNERS = """
*                   @acme/maintainers
/worker/            @riyan-patel
"""


class FakeGithubClient:
    """Minimal stand-in for GitHubClient, only implementing the surface
    _default_reviewer_routing touches (get_file_contents) plus a non-None
    `_github` so pipeline's "no token configured" guard doesn't short-circuit."""

    def __init__(self, files: dict[str, str]) -> None:
        self._github = object()
        self.files = files

    def get_file_contents(self, repo, path):
        return self.files.get(path)


@pytest.fixture(autouse=True)
def reset_codeowners_cache():
    pipeline._codeowners_cache.clear()
    yield
    pipeline._codeowners_cache.clear()


def test_default_reviewer_routing_drops_team_slug_owners():
    from mcp_server import server

    server.set_client(FakeGithubClient({".github/CODEOWNERS": CODEOWNERS}))
    try:
        owners = pipeline._default_reviewer_routing(
            "acme/widgets", "Getting an error in worker/jobs.py after retries."
        )
    finally:
        server.set_client(server._build_default_client())

    assert owners == ["riyan-patel"]


def test_default_reviewer_routing_returns_empty_when_no_codeowners_file():
    from mcp_server import server

    server.set_client(FakeGithubClient({}))
    try:
        owners = pipeline._default_reviewer_routing("acme/widgets", "worker/jobs.py is broken")
    finally:
        server.set_client(server._build_default_client())

    assert owners == []
