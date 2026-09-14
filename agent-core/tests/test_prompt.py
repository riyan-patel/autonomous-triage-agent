from agent_core.prompt import build_user_prompt
from agent_core.schema import IssueType, Severity, TriageOutput
from agent_core.types import FewShotExample, IssueInput, LabelSpec, SimilarIssueContext


def make_issue() -> IssueInput:
    return IssueInput(repo_full_name="acme/widgets", issue_number=42, title="Login broken", body="Safari only.")


def test_prompt_includes_issue_and_labels():
    prompt = build_user_prompt(
        make_issue(),
        label_taxonomy=[LabelSpec("bug", "Something broken"), LabelSpec("docs")],
        similar_issues=[],
    )
    assert "acme/widgets" in prompt
    assert "#42" in prompt
    assert "Login broken" in prompt
    assert "bug: Something broken" in prompt
    assert "- docs" in prompt


def test_prompt_includes_similar_issues():
    prompt = build_user_prompt(
        make_issue(),
        label_taxonomy=[],
        similar_issues=[SimilarIssueContext(issue_number=7, title="Login broken on Safari", state="open", distance=0.1)],
    )
    assert "#7" in prompt
    assert "Login broken on Safari" in prompt
    assert "0.100" in prompt


def test_prompt_handles_empty_context():
    prompt = build_user_prompt(make_issue(), label_taxonomy=[], similar_issues=[])
    assert "no label taxonomy" in prompt
    assert "no similar issues" in prompt


def test_prompt_includes_few_shot_examples():
    example_output = TriageOutput(
        summary="dup", type=IssueType.BUG, severity=Severity.LOW,
        draft_reply="thanks", confidence=0.95, duplicate_of=3,
    )
    prompt = build_user_prompt(
        make_issue(),
        label_taxonomy=[],
        similar_issues=[],
        few_shot_examples=[FewShotExample(title="Old bug", body="repro steps", output=example_output)],
    )
    assert "Old bug" in prompt
    assert "Correct triage:" in prompt
