from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from agent_core.llm import TOOL_NAME, AnthropicLLMClient
from agent_core.schema import IssueType, Severity


def make_tool_use_response(input_payload: dict):
    block = SimpleNamespace(type="tool_use", name=TOOL_NAME, input=input_payload)
    return SimpleNamespace(content=[block])


def test_generate_triage_parses_tool_use_response():
    payload = {
        "summary": "Crash on launch",
        "type": IssueType.BUG.value,
        "severity": Severity.HIGH.value,
        "labels": ["bug"],
        "duplicate_of": None,
        "suggested_reviewer": None,
        "draft_reply": "Thanks for the report.",
        "confidence": 0.9,
    }

    with patch("anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = make_tool_use_response(payload)
        mock_anthropic_cls.return_value = mock_client

        client = AnthropicLLMClient(api_key="test-key", model="claude-sonnet-5")
        output = client.generate_triage("some prompt")

    assert output.summary == "Crash on launch"
    assert output.confidence == 0.9

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": TOOL_NAME}
    assert call_kwargs["tools"][0]["name"] == TOOL_NAME


def test_generate_triage_raises_if_tool_not_called():
    text_only_response = SimpleNamespace(content=[SimpleNamespace(type="text", text="I refuse")])

    with patch("anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = text_only_response
        mock_anthropic_cls.return_value = mock_client

        client = AnthropicLLMClient(api_key="test-key", model="claude-sonnet-5")

        try:
            client.generate_triage("some prompt")
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "did not call" in str(exc)
