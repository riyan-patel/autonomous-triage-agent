"""Pure metric functions over EvalExample - no DB, no I/O, so these are
fast to test in isolation. See docs/ARCHITECTURE.md section 5 for what
each metric means and why it's the one being measured.
"""

from dataclasses import dataclass


@dataclass
class EvalExample:
    issue_id: int
    repo_full_name: str
    issue_number: int
    predicted_labels: list[str]
    true_labels: list[str]
    predicted_duplicate_of: int | None
    true_duplicate_of: int | None
    action_type: str  # "act" | "escalate"
    confidence: float | None


def label_metrics(examples: list[EvalExample]) -> dict:
    """Micro-averaged precision/recall/F1 over predicted vs. true label
    sets, pooled across all examples (rather than averaging per-example
    scores) so a repo's more common labels aren't drowned out by a long
    tail of one-off labels appearing in only a couple of issues."""
    if not examples:
        return {"precision": None, "recall": None, "f1": None}

    tp = fp = fn = 0
    for example in examples:
        predicted = set(example.predicted_labels)
        true = set(example.true_labels)
        tp += len(predicted & true)
        fp += len(predicted - true)
        fn += len(true - predicted)

    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    if precision is None or recall is None:
        f1 = None
    elif precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}


def duplicate_metrics(examples: list[EvalExample]) -> dict:
    """Precision/recall of duplicate_of links against ground truth. A
    prediction only counts as correct when it names the exact same issue
    number as the ground truth - a duplicate link to the wrong issue is as
    wrong as no link at all."""
    predicted_positive = [e for e in examples if e.predicted_duplicate_of is not None]
    true_positive = [e for e in examples if e.true_duplicate_of is not None]
    correct = [
        e for e in examples
        if e.true_duplicate_of is not None and e.predicted_duplicate_of == e.true_duplicate_of
    ]

    precision = len(correct) / len(predicted_positive) if predicted_positive else None
    recall = len(correct) / len(true_positive) if true_positive else None
    return {
        "predicted_count": len(predicted_positive),
        "true_count": len(true_positive),
        "correct_count": len(correct),
        "precision": precision,
        "recall": recall,
    }


def is_fully_correct(example: EvalExample) -> bool:
    """An acted-on item is "correct" only if both the labels and the
    duplicate link match ground truth exactly - a partial match still
    means a human would have had to fix something the agent shipped
    unsupervised."""
    return (
        set(example.predicted_labels) == set(example.true_labels)
        and example.predicted_duplicate_of == example.true_duplicate_of
    )


def escalation_calibration(examples: list[EvalExample]) -> dict:
    """Of the items the agent acted on autonomously (didn't escalate),
    what fraction were actually correct? This is the number that matters
    for trusting the confidence threshold - a low value here means the
    threshold (AUTONOMY_CONFIDENCE_THRESHOLD) needs to go up."""
    acted = [e for e in examples if e.action_type == "act"]
    if not acted:
        return {"acted_count": 0, "precision": None}
    correct = sum(1 for e in acted if is_fully_correct(e))
    return {"acted_count": len(acted), "precision": correct / len(acted)}
