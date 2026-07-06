"""Tests for OpenAI-compatible chat completion response parser."""

import pytest

from infermatrix.cases import load_case
from infermatrix.clients.mock_openai import MockOpenAIClient
from infermatrix.parsers.chat_completion import (
    ChatCompletionParseError,
    ParsedAssistantMessage,
    parse_chat_completion_response,
)


def test_parse_chat_completion_response() -> None:
    """Parser should extract assistant content from a mock chat response."""

    case = load_case("examples/basic_chat.yaml")
    response = MockOpenAIClient().run_case(case)

    parsed = parse_chat_completion_response(response)

    assert isinstance(parsed, ParsedAssistantMessage)
    assert parsed.model == "mock-model"
    assert parsed.choice_index == 0
    assert parsed.role == "assistant"
    assert parsed.content == case.metadata["mock_response"]
    assert parsed.finish_reason == "stop"


def test_parse_response_rejects_missing_choices() -> None:
    """Parser should fail clearly when choices is missing."""

    response = {  # <- NO CHOICES
        "id": "chatcmpl-mock-broken",
        "object": "chat.completion",
        "model": "mock-model",
    }

    with pytest.raises(ChatCompletionParseError, match="choices"):
        parse_chat_completion_response(response)


def test_parse_response_rejects_empty_choices() -> None:
    """Parser should fail clearly when choices is empty."""

    response = {
        "id": "chatcmpl-mock-broken",
        "object": "chat.completion",
        "choices": [],  # <- EMPTY CHOICES
    }

    with pytest.raises(ChatCompletionParseError, match = "must not be empty."):
        parse_chat_completion_response(response)


def test_parse_response_rejects_missing_message() -> None:
    """Parser should fail clearly when choices[0].message is missing."""

    response = {
        "id": "chatcmpl-mock-broken",
        "object": "chat.completion",
        "model": "mock-model",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": None,  # <- MISSING MESSAGE
            }
        ],
    }

    with pytest.raises(ChatCompletionParseError, match="message"):
        parse_chat_completion_response(response)


def test_parse_response_rejects_non_assistant_role() -> None:
    """Parser should only accept assistant messages in Phase C."""

    response = {
        "id": "chatcmpl-mock-broken",
        "object": "chat.completion",
        "model": "mock-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "user",  # <- NOT ASSISTANT
                    "content": "This should not be accepted.",
                },
                "finish_reason": "stop",
            }
        ],
    }

    with pytest.raises(ChatCompletionParseError, match="assistant"):
        parse_chat_completion_response(response)


def test_parse_response_rejects_empty_content() -> None:
    """Parser should reject empty assistant content."""

    response = {
        "id": "chatcmpl-mock-broken",
        "object": "chat.completion",
        "model": "mock-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "   ",  # <- EMPTY CONTENT
                },
                "finish_reason": "stop",
            }
        ],
    }

    with pytest.raises(ChatCompletionParseError, match="must not be empty"):
        parse_chat_completion_response(response)


def test_parse_response_rejects_tool_call_response_for_now() -> None:
    """Phase C content parser should not silently accept tool call responses."""

    response = {
        "id": "chatcmpl-mock-tool-call",
        "object": "chat.completion",
        "model": "mock-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [  # <- INVALID TOOL CALLS
                        {
                            "id": "call_mock_001",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city":"Shenzhen"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }

    with pytest.raises(ChatCompletionParseError, match="Tool call responses"):
        parse_chat_completion_response(response)