"""Placeholder for the perceive->reason->act pipeline.

Real implementation lands in build order step 5 (agent-core): retrieval
for duplicate/reviewer context, an LLM call for structured triage output,
and MCP tool calls to act on GitHub. For now this just proves the job
reaches a pipeline hook with a well-formed issue.
"""

from dataclasses import dataclass


@dataclass
class TriageResult:
    repo: str
    issue_number: int
    status: str


def run_triage(payload: dict) -> TriageResult:
    repo = payload["repository"]["full_name"]
    issue_number = payload["issue"]["number"]
    return TriageResult(repo=repo, issue_number=issue_number, status="not_implemented")
