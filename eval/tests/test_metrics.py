from eval.metrics import (
    EvalExample,
    duplicate_metrics,
    escalation_calibration,
    is_fully_correct,
    label_metrics,
)


def make_example(**overrides) -> EvalExample:
    defaults = dict(
        issue_id=1, repo_full_name="acme/widgets", issue_number=1,
        predicted_labels=["bug"], true_labels=["bug"],
        predicted_duplicate_of=None, true_duplicate_of=None,
        action_type="act", confidence=0.9,
    )
    defaults.update(overrides)
    return EvalExample(**defaults)


def test_label_metrics_empty():
    assert label_metrics([]) == {"precision": None, "recall": None, "f1": None}


def test_label_metrics_perfect_match():
    examples = [make_example(predicted_labels=["bug", "docs"], true_labels=["bug", "docs"])]
    result = label_metrics(examples)
    assert result == {"precision": 1.0, "recall": 1.0, "f1": 1.0}


def test_label_metrics_partial_overlap():
    # predicted {bug, needs-triage}, true {bug} -> TP=1, FP=1(needs-triage), FN=0
    examples = [make_example(predicted_labels=["bug", "needs-triage"], true_labels=["bug"])]
    result = label_metrics(examples)
    assert result["precision"] == 0.5
    assert result["recall"] == 1.0


def test_label_metrics_no_overlap():
    examples = [make_example(predicted_labels=["bug"], true_labels=["docs"])]
    result = label_metrics(examples)
    assert result["precision"] == 0.0
    assert result["recall"] == 0.0
    assert result["f1"] == 0.0


def test_duplicate_metrics_correct_link():
    examples = [make_example(predicted_duplicate_of=5, true_duplicate_of=5)]
    result = duplicate_metrics(examples)
    assert result == {"predicted_count": 1, "true_count": 1, "correct_count": 1, "precision": 1.0, "recall": 1.0}


def test_duplicate_metrics_wrong_link():
    examples = [make_example(predicted_duplicate_of=7, true_duplicate_of=5)]
    result = duplicate_metrics(examples)
    assert result["correct_count"] == 0
    assert result["precision"] == 0.0
    assert result["recall"] == 0.0


def test_duplicate_metrics_missed_duplicate():
    # agent didn't flag it as a duplicate, but ground truth says it is
    examples = [make_example(predicted_duplicate_of=None, true_duplicate_of=5)]
    result = duplicate_metrics(examples)
    assert result["predicted_count"] == 0
    assert result["precision"] is None  # no predictions to score precision over
    assert result["recall"] == 0.0


def test_duplicate_metrics_no_positives_at_all():
    examples = [make_example(predicted_duplicate_of=None, true_duplicate_of=None)]
    result = duplicate_metrics(examples)
    assert result == {"predicted_count": 0, "true_count": 0, "correct_count": 0, "precision": None, "recall": None}


def test_is_fully_correct_requires_labels_and_duplicate_match():
    assert is_fully_correct(make_example(predicted_labels=["bug"], true_labels=["bug"], predicted_duplicate_of=None, true_duplicate_of=None))
    assert not is_fully_correct(make_example(predicted_labels=["bug"], true_labels=["docs"]))
    assert not is_fully_correct(make_example(predicted_duplicate_of=1, true_duplicate_of=2))


def test_escalation_calibration_no_acted_items():
    examples = [make_example(action_type="escalate")]
    assert escalation_calibration(examples) == {"acted_count": 0, "precision": None}


def test_escalation_calibration_mixed_correctness():
    examples = [
        make_example(action_type="act", predicted_labels=["bug"], true_labels=["bug"]),  # correct
        make_example(action_type="act", predicted_labels=["bug"], true_labels=["docs"]),  # wrong
        make_example(action_type="escalate"),  # not counted
    ]
    result = escalation_calibration(examples)
    assert result == {"acted_count": 2, "precision": 0.5}
