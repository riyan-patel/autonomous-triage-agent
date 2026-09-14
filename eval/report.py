from .loader import load_eval_examples
from .metrics import duplicate_metrics, escalation_calibration, label_metrics


def build_report(examples) -> dict:
    return {
        "example_count": len(examples),
        "labels": label_metrics(examples),
        "duplicates": duplicate_metrics(examples),
        "escalation_calibration": escalation_calibration(examples),
    }


def run_report(session) -> dict:
    examples = load_eval_examples(session)
    return build_report(examples)


def format_report(report: dict) -> str:
    def pct(x):
        return "—" if x is None else f"{x * 100:.1f}%"

    labels = report["labels"]
    dupes = report["duplicates"]
    esc = report["escalation_calibration"]

    lines = [
        f"Evaluated {report['example_count']} labeled issue(s)",
        "",
        "Label accuracy",
        f"  precision={pct(labels['precision'])}  recall={pct(labels['recall'])}  f1={pct(labels['f1'])}",
        "",
        "Duplicate detection",
        f"  precision={pct(dupes['precision'])}  recall={pct(dupes['recall'])}"
        f"  (predicted={dupes['predicted_count']}, true={dupes['true_count']}, correct={dupes['correct_count']})",
        "",
        "Escalation calibration (precision of auto-acted items)",
        f"  precision={pct(esc['precision'])}  (acted_count={esc['acted_count']})",
    ]
    return "\n".join(lines)
