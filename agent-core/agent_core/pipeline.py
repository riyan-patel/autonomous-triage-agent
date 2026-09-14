from dataclasses import dataclass

from .llm import LLMClient
from .policy import Decision, decide
from .prompt import build_user_prompt
from .schema import TriageOutput
from .types import FewShotExample, IssueInput, LabelSpec, SimilarIssueContext


@dataclass
class TriageRun:
    output: TriageOutput
    decision: Decision


def run_triage(
    llm: LLMClient,
    issue: IssueInput,
    *,
    label_taxonomy: list[LabelSpec],
    similar_issues: list[SimilarIssueContext],
    few_shot_examples: list[FewShotExample] | None = None,
    confidence_threshold: float,
) -> TriageRun:
    """The perceive->reason->act "reason" step: build the prompt from
    already-retrieved context, call the LLM, and apply the decision
    policy. Retrieval (similar_issues) and acting on the result (MCP tool
    calls) are the caller's responsibility - keeping this pure/injectable
    is what makes it testable with a fake LLMClient and no live services."""
    prompt = build_user_prompt(
        issue,
        label_taxonomy=label_taxonomy,
        similar_issues=similar_issues,
        few_shot_examples=few_shot_examples,
    )
    output = llm.generate_triage(prompt)
    decision = decide(output, confidence_threshold=confidence_threshold)
    return TriageRun(output=output, decision=decision)
