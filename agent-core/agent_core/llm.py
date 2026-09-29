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


class GeminiLLMClient(LLMClient):
    """Forces structured output via Gemini's `response_schema` JSON mode,
    the closest equivalent to Anthropic's forced tool-use here: the model
    is constrained to emit JSON matching TriageOutput's schema directly."""

    def __init__(self, api_key: str, model: str) -> None:
        # Imported lazily so this module (and the fake used in tests) don't
        # require the google-genai package or an API key to import.
        from google import genai
        from google.genai import types

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=TriageOutput,
        )

    def generate_triage(self, user_prompt: str) -> TriageOutput:
        response = self._client.models.generate_content(
            model=self._model,
            contents=user_prompt,
            config=self._config,
        )

        if not response.text:
            raise ValueError("Gemini returned no content for triage generation")

        return TriageOutput.model_validate_json(response.text)
