import pytest
from pydantic import ValidationError

from agent_core.schema import IssueType, Severity, TriageOutput


def test_valid_output_parses():
    output = TriageOutput(
        summary="Login broken on Safari",
        type=IssueType.BUG,
        severity=Severity.HIGH,
        labels=["bug", "needs-triage"],
        duplicate_of=None,
        suggested_reviewer=None,
        draft_reply="Thanks for the report!",
        confidence=0.9,
    )
    assert output.type == IssueType.BUG


def test_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        TriageOutput(
            summary="x", type=IssueType.BUG, severity=Severity.LOW,
            draft_reply="x", confidence=1.5,
        )


def test_unknown_type_rejected():
    with pytest.raises(ValidationError):
        TriageOutput(
            summary="x", type="not-a-real-type", severity=Severity.LOW,
            draft_reply="x", confidence=0.5,
        )
