from agent_core.llm import LLMClient
from agent_core.schema import TriageOutput


class FakeLLMClient(LLMClient):
    """Returns a canned TriageOutput (or raises a canned exception) instead
    of calling the real Anthropic API - keeps prompt/policy/pipeline tests
    fast, offline, and independent of an API key."""

    def __init__(self, output: TriageOutput | None = None) -> None:
        self.output = output
        self.last_prompt: str | None = None

    def generate_triage(self, user_prompt: str) -> TriageOutput:
        self.last_prompt = user_prompt
        if self.output is None:
            raise AssertionError("FakeLLMClient was not configured with an output")
        return self.output
