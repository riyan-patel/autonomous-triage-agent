from abc import ABC, abstractmethod

from .prompt import SYSTEM_PROMPT
from .schema import TriageOutput

TOOL_NAME = "emit_triage"


class LLMClient(ABC):
    @abstractmethod
    def generate_triage(self, user_prompt: str) -> TriageOutput:
        """Run the reasoning step and return schema-constrained output."""


class AnthropicLLMClient(LLMClient):
    """Forces structured output via tool use: the model must call a single
    tool whose input_schema is TriageOutput's JSON schema, so the response
    is always parseable rather than free-text that might drift from the
    contract. See docs/ARCHITECTURE.md section D ("structured output")."""

    def __init__(self, api_key: str, model: str) -> None:
        # Imported lazily so this module (and the fake used in tests) don't
        # require the anthropic package or an API key to import.
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._model = model

    def generate_triage(self, user_prompt: str) -> TriageOutput:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[
                {
                    "name": TOOL_NAME,
                    "description": "Emit the structured triage decision for this issue.",
                    "input_schema": TriageOutput.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": TOOL_NAME},
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == TOOL_NAME:
                return TriageOutput.model_validate(block.input)

        raise ValueError(f"model did not call {TOOL_NAME}; got content types: {[b.type for b in response.content]}")
