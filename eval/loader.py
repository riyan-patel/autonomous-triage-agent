"""Loads (prediction, ground truth) pairs out of Postgres for the eval
harness. Reuses retrieval's models/session setup directly rather than
duplicating the schema - eval only needs DB access (sqlalchemy, psycopg,
pgvector for the Issue.embedding column type), not retrieval's heavier
runtime deps like sentence-transformers.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from retrieval.models import Action, EvalLabel, Issue

from .metrics import EvalExample


def load_eval_examples(session: Session) -> list[EvalExample]:
    """One EvalExample per issue that has a ground-truth label row,
    paired with that issue's most recent agent decision. An issue with
    ground truth but no recorded action (never triaged, or triaged before
    audit logging existed) is skipped - there's nothing to score."""
    latest_action = (
        select(Action.issue_id, func.max(Action.created_at).label("max_created_at"))
        .group_by(Action.issue_id)
        .subquery()
    )

    query = (
        select(EvalLabel, Action, Issue)
        .join(Issue, Issue.id == EvalLabel.issue_id)
        .join(Action, Action.issue_id == EvalLabel.issue_id)
        .join(
            latest_action,
            (Action.issue_id == latest_action.c.issue_id)
            & (Action.created_at == latest_action.c.max_created_at),
        )
    )

    examples = []
    for eval_label, action, issue in session.execute(query):
        payload = action.payload or {}
        examples.append(
            EvalExample(
                issue_id=issue.id,
                repo_full_name=issue.repo_full_name,
                issue_number=issue.issue_number,
                predicted_labels=payload.get("labels", []),
                true_labels=list(eval_label.ground_truth_labels or []),
                predicted_duplicate_of=payload.get("duplicate_of"),
                true_duplicate_of=eval_label.ground_truth_duplicate_of,
                action_type=action.action_type,
                confidence=action.confidence,
            )
        )
    return examples
