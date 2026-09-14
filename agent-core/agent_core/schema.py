from enum import Enum

from pydantic import BaseModel, Field


class IssueType(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    QUESTION = "question"
    DOCS = "docs"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TriageOutput(BaseModel):
    """Schema-constrained structured output the LLM must produce - this is
    the machine-actionable contract the decision policy and MCP tool calls
    consume, per docs/ARCHITECTURE.md section D."""

    summary: str = Field(description="One-sentence summary of the issue.")
    type: IssueType
    severity: Severity
    labels: list[str] = Field(default_factory=list, description="Labels to apply, drawn from the repo's taxonomy.")
    duplicate_of: int | None = Field(default=None, description="Issue number this duplicates, if any.")
    suggested_reviewer: str | None = Field(default=None, description="GitHub username/team to assign, if confident.")
    draft_reply: str = Field(description="First-response comment to post on the issue.")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence in this triage decision.")
