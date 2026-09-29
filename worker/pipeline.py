"""Wires retrieval -> agent-core -> mcp-server into one real triage
decision (build order step 5's follow-up glue).

mcp-server and agent-core live at mcp-server/mcp_server and
agent-core/agent_core on disk (hyphenated dirs aren't valid package
names), so their parent directories need to be on sys.path in addition to
the repo root that makes `retrieval` and `worker` importable - done once,
here, before anything imports them.
"""

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("worker.pipeline")

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _extra in ("agent-core", "mcp-server"):
    _path = str(_REPO_ROOT / _extra)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from agent_core.config import settings as agent_settings  # noqa: E402
from agent_core.llm import AnthropicLLMClient, GeminiLLMClient, LLMClient  # noqa: E402
from agent_core.pipeline import run_triage as run_agent_triage  # noqa: E402
from agent_core.policy import Decision  # noqa: E402
from agent_core.schema import TriageOutput  # noqa: E402
from agent_core.types import IssueInput, LabelSpec, SimilarIssueContext  # noqa: E402
from mcp_server import server as mcp_tools  # noqa: E402
from mcp_server.config import settings as mcp_settings  # noqa: E402
from retrieval.config import settings as retrieval_settings  # noqa: E402
from retrieval.db import get_engine, get_session_factory  # noqa: E402
from retrieval.duplicates import find_similar_issues  # noqa: E402
from retrieval.embeddings import Embedder, SentenceTransformerEmbedder  # noqa: E402
from retrieval.indexer import index_issue  # noqa: E402
from retrieval.models import Action, Issue, Review  # noqa: E402
from retrieval.reviewer_routing import suggest_reviewers  # noqa: E402

# Fallback used when a repo has no fetchable labels (no GITHUB_TOKEN
# configured, or the repo genuinely has none) - see _default_label_taxonomy.
DEFAULT_LABEL_TAXONOMY = [
    LabelSpec("bug", "Something isn't working as expected"),
    LabelSpec("feature", "A request for new functionality"),
    LabelSpec("question", "A question rather than a bug/feature"),
    LabelSpec("docs", "Documentation is missing or incorrect"),
    LabelSpec("needs-triage", "Not yet reviewed by a maintainer"),
]

# GitHub checks these locations for CODEOWNERS, in this precedence order.
CODEOWNERS_PATHS = [".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"]

RetrievalFn = Callable[[str, int, str, str, str], list[SimilarIssueContext]]
ActFn = Callable[[str, int, TriageOutput], None]
AuditFn = Callable[[str, str, int, TriageOutput, Decision, bool], None]
ReviewerFn = Callable[[str, str], list[str]]
LabelTaxonomyFn = Callable[[str], list[LabelSpec]]

_embedder: Embedder | None = None
_engine = None
_llm_client: LLMClient | None = None
_codeowners_cache: dict[str, str | None] = {}
_label_taxonomy_cache: dict[str, list[LabelSpec]] = {}


def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformerEmbedder(retrieval_settings.embedding_model)
    return _embedder


def _get_session_factory():
    global _engine
    if _engine is None:
        _engine = get_engine()
    return get_session_factory(_engine)


def _get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        if agent_settings.llm_provider == "gemini":
            _llm_client = GeminiLLMClient(agent_settings.gemini_api_key, agent_settings.llm_model)
        else:
            _llm_client = AnthropicLLMClient(agent_settings.anthropic_api_key, agent_settings.llm_model)
    return _llm_client


def _default_retrieval(repo: str, issue_number: int, title: str, body: str, state: str) -> list[SimilarIssueContext]:
    embedder = _get_embedder()
    session = _get_session_factory()()
    try:
        index_issue(
            session, embedder,
            repo_full_name=repo, issue_number=issue_number, title=title, body=body, state=state,
        )
        query_embedding = embedder.embed(f"{title}\n\n{body}")
        similar = find_similar_issues(
            session, repo_full_name=repo, embedding=query_embedding,
            exclude_issue_number=issue_number, limit=5,
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return [SimilarIssueContext(s.issue_number, s.title, s.state, s.distance) for s in similar]


def _get_codeowners(repo: str) -> str | None:
    """Fetch and cache a repo's CODEOWNERS content (checking GitHub's three
    conventional locations in order). Cached per repo for the process
    lifetime - CODEOWNERS changes rarely enough that a stale read between
    deploys is an acceptable tradeoff against re-fetching on every issue."""
    if mcp_tools._client._github is None:
        # No GITHUB_TOKEN configured - can't fetch anything real, so skip
        # rather than crash (mirrors mcp-server's own dry-run posture).
        return None
    if repo not in _codeowners_cache:
        content = None
        for path in CODEOWNERS_PATHS:
            content = mcp_tools._client.get_file_contents(repo, path)
            if content is not None:
                break
        _codeowners_cache[repo] = content
    return _codeowners_cache[repo]


def _default_reviewer_routing(repo: str, issue_text: str) -> list[str]:
    codeowners = _get_codeowners(repo)
    if codeowners is None:
        return []
    owners = suggest_reviewers(codeowners, issue_text)
    # CODEOWNERS entries are "@user" or "@org/team"; GitHub's assignee API
    # only accepts a plain user login, not a team, so team-slug owners
    # (containing "/") can't be auto-assigned and are dropped here.
    return [owner.lstrip("@") for owner in owners if "/" not in owner]


def _default_label_taxonomy(repo: str) -> list[LabelSpec]:
    """Fetch the repo's real configured labels; fall back to the static
    default taxonomy if the repo has none fetchable (no GITHUB_TOKEN
    configured, or a genuinely label-less repo). Cached per repo for the
    process lifetime, same tradeoff as _get_codeowners."""
    if repo not in _label_taxonomy_cache:
        labels: list[LabelSpec] = []
        if mcp_tools._client._github is not None:
            labels = [
                LabelSpec(entry["name"], entry["description"])
                for entry in mcp_tools._client.list_labels(repo)
            ]
        _label_taxonomy_cache[repo] = labels or DEFAULT_LABEL_TAXONOMY
    return _label_taxonomy_cache[repo]


def _default_act(repo: str, issue_number: int, output: TriageOutput) -> None:
    """Apply an "act" decision via the MCP tool layer. mcp-server is
    dry-run by default (DRY_RUN=true), so this is safe to call without
    opting in to a real GitHub token."""
    if output.labels:
        mcp_tools.apply_labels(repo, issue_number, output.labels)
    if output.draft_reply:
        mcp_tools.post_comment(repo, issue_number, output.draft_reply)
    if output.suggested_reviewer:
        mcp_tools.assign_reviewer(repo, issue_number, output.suggested_reviewer)
    if output.duplicate_of is not None:
        mcp_tools.link_duplicate(repo, issue_number, output.duplicate_of)


def _default_audit(
    delivery_id: str, repo: str, issue_number: int, output: TriageOutput, decision: Decision, dry_run: bool
) -> None:
    """Record every triage decision to the actions table - the audit log
    docs/ARCHITECTURE.md calls for, and the data source the eval harness
    (build order step 8) will read from. `actions` has a UNIQUE(delivery_id,
    action_type) constraint, so a retried job re-recording the same
    decision is a DB-level no-op, same as the queue-level dedupe."""
    session = _get_session_factory()()
    try:
        issue = session.scalar(
            select(Issue).where(Issue.repo_full_name == repo, Issue.issue_number == issue_number)
        )
        if issue is None:
            logger.warning("no indexed issue row for %s#%s; skipping audit log", repo, issue_number)
            return

        session.add(
            Action(
                issue_id=issue.id,
                delivery_id=delivery_id,
                action_type=decision.action.value,
                payload=output.model_dump(mode="json"),
                confidence=output.confidence,
                dry_run=dry_run,
            )
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        logger.info("audit row for delivery %s already exists, skipping", delivery_id)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@dataclass
class TriageResult:
    repo: str
    issue_number: int
    status: str  # "acted" | "escalated"
    confidence: float
    reasons: list[str]


def run_triage(
    payload: dict,
    *,
    delivery_id: str,
    retrieval_fn: RetrievalFn | None = None,
    llm_client: LLMClient | None = None,
    act_fn: ActFn | None = None,
    audit_fn: AuditFn | None = None,
    reviewer_fn: ReviewerFn | None = None,
    label_taxonomy_fn: LabelTaxonomyFn | None = None,
) -> TriageResult:
    issue = payload["issue"]
    repo = payload["repository"]["full_name"]
    issue_number = issue["number"]
    title = issue.get("title", "")
    body = issue.get("body") or ""
    state = issue.get("state", "open")

    retrieval_fn = retrieval_fn or _default_retrieval
    llm_client = llm_client or _get_llm_client()
    act_fn = act_fn or _default_act
    audit_fn = audit_fn or _default_audit
    reviewer_fn = reviewer_fn or _default_reviewer_routing
    label_taxonomy_fn = label_taxonomy_fn or _default_label_taxonomy

    similar_issues = retrieval_fn(repo, issue_number, title, body, state)

    agent_run = run_agent_triage(
        llm_client,
        IssueInput(repo_full_name=repo, issue_number=issue_number, title=title, body=body),
        label_taxonomy=label_taxonomy_fn(repo),
        similar_issues=similar_issues,
        confidence_threshold=agent_settings.confidence_threshold,
    )
    output, decision = agent_run.output, agent_run.decision

    # CODEOWNERS-grounded routing overrides the LLM's own guess - an
    # ungrounded reviewer suggestion (the model naming a team/person with
    # nothing backing it) is worse than none at all.
    suggested = reviewer_fn(repo, f"{title}\n\n{body}")
    output.suggested_reviewer = suggested[0] if suggested else None

    if decision.action.value == "act":
        act_fn(repo, issue_number, output)
        status = "acted"
    else:
        status = "escalated"

    audit_fn(delivery_id, repo, issue_number, output, decision, mcp_settings.dry_run)

    logger.info(
        "triage %s#%s -> %s (confidence=%.2f, reasons=%s)",
        repo, issue_number, status, output.confidence, decision.reasons,
    )
    return TriageResult(
        repo=repo, issue_number=issue_number, status=status,
        confidence=output.confidence, reasons=decision.reasons,
    )


def execute_approval(action_id: int, act_fn: ActFn | None = None) -> dict:
    """Execute a human-approved escalated action (dashboard "Approve"
    button, via webhook-ingress's /internal/approvals/{id}/execute ->
    worker.jobs.execute_approval). Only actually calls mcp-server's tools
    if `reviews.decision == 'approved'` for this action - a defense-in-depth
    check independent of the caller, not just the enqueue-time trust.

    Checks for an existing "approved_execute" audit row *before* calling
    act_fn (not just catching the resulting IntegrityError after the fact)
    so a re-clicked Approve or a retried job skips the real GitHub calls
    entirely instead of just skipping the audit write - actions.delivery_id
    UNIQUE(delivery_id, action_type) constraint still backstops this
    against a race between two concurrent workers."""
    act_fn = act_fn or _default_act
    session = _get_session_factory()()
    try:
        review = session.scalar(select(Review).where(Review.action_id == action_id))
        if review is None or review.decision != "approved":
            return {"status": "not_approved"}

        action = session.get(Action, action_id)
        if action is None:
            return {"status": "action_not_found"}

        already_executed = session.scalar(
            select(Action).where(
                Action.delivery_id == f"approval-{action_id}", Action.action_type == "approved_execute"
            )
        )
        if already_executed is not None:
            return {"status": "already_executed"}

        issue = session.get(Issue, action.issue_id)
        if issue is None:
            return {"status": "issue_not_found"}

        output = TriageOutput.model_validate(action.payload)
        act_fn(issue.repo_full_name, issue.issue_number, output)

        session.add(
            Action(
                issue_id=issue.id,
                delivery_id=f"approval-{action_id}",
                action_type="approved_execute",
                payload=action.payload,
                confidence=action.confidence,
                dry_run=mcp_settings.dry_run,
            )
        )
        session.commit()
        return {"status": "executed", "repo": issue.repo_full_name, "issue_number": issue.issue_number}
    except IntegrityError:
        session.rollback()
        logger.info("action %s already executed, skipping", action_id)
        return {"status": "already_executed"}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
