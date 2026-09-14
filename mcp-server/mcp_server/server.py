import logging
from dataclasses import asdict

from mcp.server.mcpserver import MCPServer

from .config import settings
from .github_client import GitHubClient

logging.basicConfig(level=logging.INFO)

mcp = MCPServer(
    "triage-agent-github",
    instructions=(
        "GitHub actions for autonomous issue triage. Every mutating tool "
        "respects DRY_RUN and is idempotent per issue - calling "
        "post_comment or link_duplicate twice on the same issue is a "
        "no-op the second time."
    ),
)


def _build_default_client() -> GitHubClient:
    github = None
    if settings.github_token:
        from github import Github

        github = Github(settings.github_token)
    return GitHubClient(github, dry_run=settings.dry_run)


# Module-level so `main.py` and tests share one instance; tests swap it via
# set_client() to inject a fake instead of talking to the real GitHub API.
_client = _build_default_client()


def set_client(client: GitHubClient) -> None:
    global _client
    _client = client


@mcp.tool()
def apply_labels(repo: str, issue_number: int, labels: list[str]) -> dict:
    """Apply labels from the repo's label taxonomy to an issue."""
    return asdict(_client.apply_labels(repo, issue_number, labels))


@mcp.tool()
def post_comment(repo: str, issue_number: int, body: str) -> dict:
    """Post the agent's first-response comment on an issue (posts at most once per issue)."""
    return asdict(_client.post_comment(repo, issue_number, body))


@mcp.tool()
def assign_reviewer(repo: str, issue_number: int, username: str) -> dict:
    """Assign a suggested reviewer/owner to an issue."""
    return asdict(_client.assign_reviewer(repo, issue_number, username))


@mcp.tool()
def link_duplicate(repo: str, issue_number: int, duplicate_of: int) -> dict:
    """Comment linking an issue as a likely duplicate of another issue number."""
    return asdict(_client.link_duplicate(repo, issue_number, duplicate_of))


@mcp.tool()
def search_issues(repo: str, query: str, limit: int = 10) -> list[dict]:
    """Search a repo's issues (GitHub search-qualifier syntax) for duplicate/context lookup."""
    return _client.search_issues(repo, query, limit)
