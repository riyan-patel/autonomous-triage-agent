import asyncio

import pytest

from mcp_server import server
from mcp_server.github_client import ActionResult


class FakeClient:
    """Stands in for GitHubClient in tool-registration tests - the actual
    GitHub interaction logic is covered by test_github_client.py; this file
    only proves each @mcp.tool() wires its arguments through correctly."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def apply_labels(self, repo, issue_number, labels):
        self.calls.append(("apply_labels", repo, issue_number, labels))
        return ActionResult(action="apply_labels", ok=True)

    def post_comment(self, repo, issue_number, body):
        self.calls.append(("post_comment", repo, issue_number, body))
        return ActionResult(action="post_comment", ok=True)

    def assign_reviewer(self, repo, issue_number, username):
        self.calls.append(("assign_reviewer", repo, issue_number, username))
        return ActionResult(action="assign_reviewer", ok=True)

    def link_duplicate(self, repo, issue_number, duplicate_of):
        self.calls.append(("link_duplicate", repo, issue_number, duplicate_of))
        return ActionResult(action="link_duplicate", ok=True)

    def search_issues(self, repo, query, limit=10):
        self.calls.append(("search_issues", repo, query, limit))
        return [{"number": 1, "title": "x", "state": "open"}]


@pytest.fixture
def fake_client():
    client = FakeClient()
    server.set_client(client)
    yield client
    server.set_client(server._build_default_client())


def test_apply_labels_delegates(fake_client):
    result = server.apply_labels("acme/widgets", 1, ["bug"])
    assert result == {"action": "apply_labels", "ok": True, "dry_run": False, "skipped_reason": None}
    assert fake_client.calls == [("apply_labels", "acme/widgets", 1, ["bug"])]


def test_post_comment_delegates(fake_client):
    server.post_comment("acme/widgets", 1, "hello")
    assert fake_client.calls == [("post_comment", "acme/widgets", 1, "hello")]


def test_assign_reviewer_delegates(fake_client):
    server.assign_reviewer("acme/widgets", 1, "octocat")
    assert fake_client.calls == [("assign_reviewer", "acme/widgets", 1, "octocat")]


def test_link_duplicate_delegates(fake_client):
    server.link_duplicate("acme/widgets", 5, 2)
    assert fake_client.calls == [("link_duplicate", "acme/widgets", 5, 2)]


def test_search_issues_delegates(fake_client):
    result = server.search_issues("acme/widgets", "bug", 3)
    assert result == [{"number": 1, "title": "x", "state": "open"}]
    assert fake_client.calls == [("search_issues", "acme/widgets", "bug", 3)]


def test_tools_are_registered_with_mcp():
    tool_names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert tool_names == {
        "apply_labels",
        "post_comment",
        "assign_reviewer",
        "link_duplicate",
        "search_issues",
    }
