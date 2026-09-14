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

from agent_core.config import settings as agent_settings  # noqa: E402
from agent_core.llm import AnthropicLLMClient, LLMClient  # noqa: E402
from agent_core.pipeline import run_triage as run_agent_triage  # noqa: E402
from agent_core.schema import TriageOutput  # noqa: E402
from agent_core.types import IssueInput, LabelSpec, SimilarIssueContext  # noqa: E402
from mcp_server import server as mcp_tools  # noqa: E402
from retrieval.config import settings as retrieval_settings  # noqa: E402
from retrieval.db import get_engine, get_session_factory  # noqa: E402
from retrieval.duplicates import find_similar_issues  # noqa: E402
from retrieval.embeddings import Embedder, SentenceTransformerEmbedder  # noqa: E402
from retrieval.indexer import index_issue  # noqa: E402

# Static default until per-repo label fetch (a GitHub "list labels" call
# not yet in mcp-server's tool surface) is wired up.
DEFAULT_LABEL_TAXONOMY = [
    LabelSpec("bug", "Something isn't working as expected"),
    LabelSpec("feature", "A request for new functionality"),
    LabelSpec("question", "A question rather than a bug/feature"),
    LabelSpec("docs", "Documentation is missing or incorrect"),
    LabelSpec("needs-triage", "Not yet reviewed by a maintainer"),
]

RetrievalFn = Callable[[str, int, str, str, str], list[SimilarIssueContext]]
ActFn = Callable[[str, int, TriageOutput], None]

_embedder: Embedder | None = None
_engine = None
_llm_client: LLMClient | None = None


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
    retrieval_fn: RetrievalFn | None = None,
    llm_client: LLMClient | None = None,
    act_fn: ActFn | None = None,
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

    similar_issues = retrieval_fn(repo, issue_number, title, body, state)

    agent_run = run_agent_triage(
        llm_client,
        IssueInput(repo_full_name=repo, issue_number=issue_number, title=title, body=body),
        label_taxonomy=DEFAULT_LABEL_TAXONOMY,
        similar_issues=similar_issues,
        confidence_threshold=agent_settings.confidence_threshold,
    )
    output, decision = agent_run.output, agent_run.decision

    if decision.action.value == "act":
        act_fn(repo, issue_number, output)
        status = "acted"
    else:
        status = "escalated"

    logger.info(
        "triage %s#%s -> %s (confidence=%.2f, reasons=%s)",
        repo, issue_number, status, output.confidence, decision.reasons,
    )
    return TriageResult(
        repo=repo, issue_number=issue_number, status=status,
        confidence=output.confidence, reasons=decision.reasons,
    )
