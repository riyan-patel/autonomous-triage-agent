import logging
import time
from dataclasses import dataclass

from github import GithubException

logger = logging.getLogger("mcp_server.github_client")

# Written into every comment the agent posts so post_comment/link_duplicate
# can detect "have I already said something on this issue" and skip -
# the no-spam guardrail from docs/ARCHITECTURE.md (max 1 agent comment/issue).
AGENT_COMMENT_MARKER = "<!-- triage-agent:comment -->"

# Rate-limit/abuse-detection guardrail from docs/ARCHITECTURE.md: back off
# on 403/429 rather than erroring out immediately. Any other status (404,
# 422, ...) is a real error, not a rate limit, so it's raised immediately -
# retrying it would just waste attempts on a guaranteed failure.
RETRYABLE_STATUSES = {403, 429}
MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 1.0


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
    fake double instead of talking to the real GitHub API. `sleep` is
    injected too, so retry-backoff tests don't actually block.
    """

    def __init__(self, github, dry_run: bool = True, sleep=time.sleep) -> None:
        self._github = github
        self.dry_run = dry_run
        self._sleep = sleep

    def _call(self, fn):
        """Invoke a zero-arg PyGithub call with rate-limit-aware retry:
        honor GitHub's Retry-After header on 403/429 if present, else back
        off exponentially, up to MAX_ATTEMPTS."""
        attempt = 0
        while True:
            try:
                return fn()
            except GithubException as exc:
                attempt += 1
                if exc.status not in RETRYABLE_STATUSES or attempt >= MAX_ATTEMPTS:
                    raise
                delay = self._retry_delay(exc, attempt)
                logger.warning(
                    "GitHub API returned %s, retrying in %.1fs (attempt %d/%d)",
                    exc.status, delay, attempt, MAX_ATTEMPTS,
                )
                self._sleep(delay)

    @staticmethod
    def _retry_delay(exc: GithubException, attempt: int) -> float:
        retry_after = (exc.headers or {}).get("retry-after")
        if retry_after is not None:
            try:
                return float(retry_after)
            except ValueError:
                pass
        return BASE_DELAY_SECONDS * (2 ** (attempt - 1))

    def _get_issue(self, repo: str, issue_number: int):
        return self._call(lambda: self._github.get_repo(repo).get_issue(issue_number))

    def apply_labels(self, repo: str, issue_number: int, labels: list[str]) -> ActionResult:
        if self.dry_run:
            logger.info("[dry-run] would apply labels %s to %s#%s", labels, repo, issue_number)
            return ActionResult(action="apply_labels", ok=True, dry_run=True)

        issue = self._get_issue(repo, issue_number)
        self._call(lambda: issue.add_to_labels(*labels))
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

        self._call(lambda: issue.create_comment(marked_body))
        return ActionResult(action="post_comment", ok=True)

    def assign_reviewer(self, repo: str, issue_number: int, username: str) -> ActionResult:
        if self.dry_run:
            logger.info("[dry-run] would assign %s to %s#%s", username, repo, issue_number)
            return ActionResult(action="assign_reviewer", ok=True, dry_run=True)

        issue = self._get_issue(repo, issue_number)
        self._call(lambda: issue.add_to_assignees(username))
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

        self._call(lambda: issue.create_comment(body))
        return ActionResult(action="link_duplicate", ok=True)

    def search_issues(self, repo: str, query: str, limit: int = 10) -> list[dict]:
        results = self._call(lambda: list(self._github.search_issues(f"repo:{repo} {query}")))
        return [{"number": i.number, "title": i.title, "state": i.state} for i in results[:limit]]

    def _agent_already_commented(self, issue) -> bool:
        comments = self._call(lambda: list(issue.get_comments()))
        return any(AGENT_COMMENT_MARKER in (comment.body or "") for comment in comments)
