from dataclasses import dataclass, field
from enum import Enum

from .schema import TriageOutput


class DecisionAction(str, Enum):
    ACT = "act"
    ESCALATE = "escalate"


@dataclass
class Decision:
    action: DecisionAction
    reasons: list[str] = field(default_factory=list)


def decide(output: TriageOutput, *, confidence_threshold: float) -> Decision:
    """Confidence-gated autonomy policy (docs/ARCHITECTURE.md section D/4):
    low-confidence issues always escalate to a human rather than being
    acted on automatically. A duplicate_of link is treated as higher-stakes
    than labels/comments - it's escalated unless confidence clears the
    threshold with margin, since a wrong duplicate link is more disruptive
    to undo than a wrong label."""
    reasons = []

    if output.confidence < confidence_threshold:
        reasons.append(f"confidence {output.confidence:.2f} below threshold {confidence_threshold:.2f}")
        return Decision(action=DecisionAction.ESCALATE, reasons=reasons)

    if output.duplicate_of is not None and output.confidence < confidence_threshold + 0.1:
        reasons.append(
            f"duplicate_of=#{output.duplicate_of} needs extra margin above threshold "
            f"(confidence {output.confidence:.2f} < {confidence_threshold + 0.1:.2f})"
        )
        return Decision(action=DecisionAction.ESCALATE, reasons=reasons)

    reasons.append(f"confidence {output.confidence:.2f} meets bar for autonomous action")
    return Decision(action=DecisionAction.ACT, reasons=reasons)
