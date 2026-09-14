from sqlalchemy import select
from sqlalchemy.orm import Session

from .embeddings import Embedder
from .models import Issue


def _embedding_text(title: str, body: str) -> str:
    return f"{title}\n\n{body}"


def index_issue(
    session: Session,
    embedder: Embedder,
    *,
    repo_full_name: str,
    issue_number: int,
    title: str,
    body: str,
    state: str = "open",
    installation_id: int | None = None,
) -> Issue:
    """Embed and upsert one issue. Used both for the install-time backfill
    of existing issues and for indexing a new issue at triage time."""
    embedding = embedder.embed(_embedding_text(title, body))

    existing = session.scalar(
        select(Issue).where(Issue.repo_full_name == repo_full_name, Issue.issue_number == issue_number)
    )
    if existing:
        existing.title = title
        existing.body = body
        existing.state = state
        existing.embedding = embedding
        session.flush()
        return existing

    issue = Issue(
        installation_id=installation_id,
        repo_full_name=repo_full_name,
        issue_number=issue_number,
        title=title,
        body=body,
        state=state,
        embedding=embedding,
    )
    session.add(issue)
    session.flush()
    return issue
