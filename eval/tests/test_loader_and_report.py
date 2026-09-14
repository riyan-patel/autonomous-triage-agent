"""Integration test: seeds the synthetic benchmark into real Postgres,
runs the actual loader + report against it, and checks against hand-
computed expected metrics (see the comment in fixtures/sample_benchmark.py
usage below) - proving the SQL join in loader.py is correct, not just the
pure metric math already covered by test_metrics.py.
"""

import pytest

from eval.fixtures.sample_benchmark import BENCHMARK
from eval.report import build_report
from eval.seed import seed_benchmark


def test_seed_and_report_against_real_db(db_session):
    seed_benchmark(db_session, BENCHMARK)
    db_session.flush()

    from eval.loader import load_eval_examples

    examples = load_eval_examples(db_session)
    seeded_repo_issue_numbers = {(row["repo_full_name"], row["issue_number"]) for row in BENCHMARK}
    examples = [
        e for e in examples if (e.repo_full_name, e.issue_number) in seeded_repo_issue_numbers
    ]

    report = build_report(examples)

    assert report["example_count"] == len(BENCHMARK)

    # hand-computed from fixtures/sample_benchmark.py: TP=9, FP=2, FN=2
    assert report["labels"]["precision"] == pytest.approx(9 / 11)
    assert report["labels"]["recall"] == pytest.approx(9 / 11)

    # only issue 1002 (dup of 1001, correctly predicted) counts as correct;
    # issue 1007 should have linked 1006 but didn't.
    assert report["duplicates"] == {
        "predicted_count": 1,
        "true_count": 2,
        "correct_count": 1,
        "precision": 1.0,
        "recall": 0.5,
    }

    # 6 acted items (1001,1002,1004,1005,1006,1008); correct: 1001,1002,1004,1008 = 4/6
    assert report["escalation_calibration"]["acted_count"] == 6
    assert report["escalation_calibration"]["precision"] == pytest.approx(4 / 6)
