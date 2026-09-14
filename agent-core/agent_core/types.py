from dataclasses import dataclass

from .schema import TriageOutput


@dataclass
class IssueInput:
    repo_full_name: str
    issue_number: int
    title: str
    body: str


@dataclass
class LabelSpec:
    name: str
    description: str = ""


@dataclass
class SimilarIssueContext:
    issue_number: int
    title: str
    state: str
    distance: float


@dataclass
class FewShotExample:
    title: str
    body: str
    output: TriageOutput
