from .types import FewShotExample, IssueInput, LabelSpec, SimilarIssueContext

SYSTEM_PROMPT = """\
You are an autonomous GitHub issue triage agent. Given a newly filed or \
edited issue, you must decide how to classify it, which labels apply, \
whether it duplicates an existing issue, who should review it, and what \
first-response comment to post.

Only choose labels from the taxonomy you are given - never invent a label \
that isn't listed. Only set duplicate_of to a number that appears in the \
list of similar issues you are given, and only when you are confident it \
is the same underlying issue, not just a related one. Set confidence \
honestly: it gates whether this triage is applied automatically or \
escalated to a human, so an overconfident score on a genuinely ambiguous \
issue causes real harm (a wrong label or a bad duplicate link shipped \
without review) - when in doubt, score lower.\
"""


def _format_labels(labels: list[LabelSpec]) -> str:
    if not labels:
        return "(no label taxonomy provided)"
    return "\n".join(f"- {label.name}: {label.description}" if label.description else f"- {label.name}" for label in labels)


def _format_similar_issues(similar: list[SimilarIssueContext]) -> str:
    if not similar:
        return "(no similar issues found)"
    return "\n".join(
        f"- #{issue.issue_number} [{issue.state}] {issue.title} (cosine distance {issue.distance:.3f})"
        for issue in similar
    )


def _format_few_shot(examples: list[FewShotExample]) -> str:
    if not examples:
        return ""
    blocks = []
    for example in examples:
        blocks.append(
            f"Issue: {example.title}\n{example.body}\n"
            f"Correct triage: {example.output.model_dump_json()}"
        )
    return "Past examples of correct triage on this repo:\n\n" + "\n\n".join(blocks) + "\n\n"


def build_user_prompt(
    issue: IssueInput,
    *,
    label_taxonomy: list[LabelSpec],
    similar_issues: list[SimilarIssueContext],
    few_shot_examples: list[FewShotExample] | None = None,
) -> str:
    return (
        f"{_format_few_shot(few_shot_examples or [])}"
        f"Repo: {issue.repo_full_name}\n"
        f"Issue #{issue.issue_number}: {issue.title}\n\n"
        f"{issue.body}\n\n"
        f"Label taxonomy:\n{_format_labels(label_taxonomy)}\n\n"
        f"Similar existing issues (for duplicate detection and context):\n"
        f"{_format_similar_issues(similar_issues)}\n\n"
        "Triage this issue."
    )
