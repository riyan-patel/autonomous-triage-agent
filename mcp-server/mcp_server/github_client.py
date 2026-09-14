import logging
from dataclasses import dataclass

logger = logging.getLogger("mcp_server.github_client")

# Written into every comment the agent posts so post_comment/link_duplicate
# can detect "have I already said something on this issue" and skip -
# the no-spam guardrail from docs/ARCHITECTURE.md (max 1 agent comment/issue).
AGENT_COMMENT_MARKER = "<!-- triage-agent:comment -->"


@dataclass
class ActionResult:
    action: str
    ok: bool
    dry_run: bool = False
    skipped_reason: str | None = None


class GitHubClient:
    """Thin wrapper around a PyGithub `Github` instance.

    Deliberately exposes only the allow-listed actions the agent is
    permitted to take (see docs/ARCHITECTURE.md guardrails): it has no
    method to close an issue, push code, or otherwise act outside apply
    labels / comment / assign / link-duplicate / search.

    `github` is injected rather than constructed here so tests can pass a
    fake double instead of talking to the real GitHub API.
    """

    def __init__(self, github, dry_run: bool = True) -> None:
        self._github = github
        self.dry_run = dry_run

    def _get_issue(self, repo: str, issue_number: int):
        return self._github.get_repo(repo).get_issue(issue_number)

    def apply_labels(self, repo: str, issue_number: int, labels: list[str]) -> ActionResult:
        if self.dry_run:
            logger.info("[dry-run] would apply labels %s to %s#%s", labels, repo, issue_number)
            return ActionResult(action="apply_labels", ok=True, dry_run=True)

        issue = self._get_issue(repo, issue_number)
        issue.add_to_labels(*labels)
        return ActionResult(action="apply_labels", ok=True)

    def post_comment(self, repo: str, issue_number: int, body: str) -> ActionResult:
        marked_body = f"{body}\n\n{AGENT_COMMENT_MARKER}"

        if self.dry_run:
            logger.info("[dry-run] would comment on %s#%s: %s", repo, issue_number, body)
            return ActionResult(action="post_comment", ok=True, dry_run=True)

        issue = self._get_issue(repo, issue_number)
        if self._agent_already_commented(issue):
            logger.info("skipping duplicate comment on %s#%s", repo, issue_number)
            return ActionResult(action="post_comment", ok=True, skipped_reason="already_commented")

        issue.create_comment(marked_body)
        return ActionResult(action="post_comment", ok=True)

    def assign_reviewer(self, repo: str, issue_number: int, username: str) -> ActionResult:
        if self.dry_run:
            logger.info("[dry-run] would assign %s to %s#%s", username, repo, issue_number)
            return ActionResult(action="assign_reviewer", ok=True, dry_run=True)

        issue = self._get_issue(repo, issue_number)
        issue.add_to_assignees(username)
        return ActionResult(action="assign_reviewer", ok=True)

    def link_duplicate(self, repo: str, issue_number: int, duplicate_of: int) -> ActionResult:
        body = f"Possible duplicate of #{duplicate_of}.\n\n{AGENT_COMMENT_MARKER}"

        if self.dry_run:
            logger.info("[dry-run] would link %s#%s as duplicate of #%s", repo, issue_number, duplicate_of)
            return ActionResult(action="link_duplicate", ok=True, dry_run=True)

        issue = self._get_issue(repo, issue_number)
        if self._agent_already_commented(issue):
            logger.info("skipping duplicate-link comment on %s#%s", repo, issue_number)
            return ActionResult(action="link_duplicate", ok=True, skipped_reason="already_commented")

        issue.create_comment(body)
        return ActionResult(action="link_duplicate", ok=True)

    def search_issues(self, repo: str, query: str, limit: int = 10) -> list[dict]:
        results = self._github.search_issues(f"repo:{repo} {query}")
        return [{"number": i.number, "title": i.title, "state": i.state} for i in list(results)[:limit]]

    @staticmethod
    def _agent_already_commented(issue) -> bool:
        return any(AGENT_COMMENT_MARKER in (comment.body or "") for comment in issue.get_comments())
