from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Issue


@dataclass
class SimilarIssue:
    issue_number: int
    title: str
    state: str
    distance: float  # cosine distance: 0 = identical, 2 = opposite


def find_similar_issues(
    session: Session,
    *,
    repo_full_name: str,
    embedding: list[float],
    exclude_issue_number: int | None = None,
    limit: int = 5,
) -> list[SimilarIssue]:
    """k-NN cosine search over already-indexed issues in the same repo -
    used both for duplicate-detection candidates and as RAG context for
    the agent core's reasoning step (build order step 5)."""
    distance = Issue.embedding.cosine_distance(embedding)
    query = (
        select(Issue, distance.label("distance"))
        .where(Issue.repo_full_name == repo_full_name, Issue.embedding.is_not(None))
        .order_by(distance)
        .limit(limit + (1 if exclude_issue_number is not None else 0))
    )

    results = []
    for issue, dist in session.execute(query):
        if exclude_issue_number is not None and issue.issue_number == exclude_issue_number:
            continue
        results.append(SimilarIssue(issue_number=issue.issue_number, title=issue.title, state=issue.state, distance=dist))
        if len(results) == limit:
            break
    return results
