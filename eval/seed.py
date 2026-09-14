"""Loads eval/fixtures/sample_benchmark.py into Postgres (issues, actions,
eval_labels) so the harness has something to run against. Synthetic data
standing in for a real labeled benchmark - see the fixture file's
docstring. Safe to re-run: upserts by (repo_full_name, issue_number).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from retrieval.models import Action, EvalLabel, Issue

from .fixtures.sample_benchmark import BENCHMARK


def seed_benchmark(session: Session, benchmark: list[dict] = BENCHMARK) -> list[int]:
    issue_ids = []
    for row in benchmark:
        issue = session.scalar(
            select(Issue).where(
                Issue.repo_full_name == row["repo_full_name"],
                Issue.issue_number == row["issue_number"],
            )
        )
        if issue is None:
            issue = Issue(
                repo_full_name=row["repo_full_name"],
                issue_number=row["issue_number"],
                title=row["title"],
                body="",
            )
            session.add(issue)
            session.flush()

        delivery_id = f"eval-seed-{row['repo_full_name']}-{row['issue_number']}"
        action = session.scalar(
            select(Action).where(
                Action.delivery_id == delivery_id, Action.action_type == row["action_type"]
            )
        )
        if action is None:
            session.add(
                Action(
                    issue_id=issue.id,
                    delivery_id=delivery_id,
                    action_type=row["action_type"],
                    payload={
                        "labels": row["predicted_labels"],
                        "duplicate_of": row["predicted_duplicate_of"],
                    },
                    confidence=row["confidence"],
                    dry_run=True,
                )
            )

        eval_label = session.scalar(select(EvalLabel).where(EvalLabel.issue_id == issue.id))
        if eval_label is None:
            session.add(
                EvalLabel(
                    issue_id=issue.id,
                    ground_truth_labels=row["true_labels"],
                    ground_truth_duplicate_of=row["true_duplicate_of"],
                    notes="synthetic fixture (eval/fixtures/sample_benchmark.py)",
                )
            )

        issue_ids.append(issue.id)

    session.flush()
    return issue_ids


if __name__ == "__main__":
    from retrieval.db import get_engine, get_session_factory

    engine = get_engine()
    db_session = get_session_factory(engine)()
    try:
        ids = seed_benchmark(db_session)
        db_session.commit()
        print(f"seeded {len(ids)} benchmark issues")
    finally:
        db_session.close()
