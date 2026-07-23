"""Tests for OpenAI-compatible tool call response parser."""

import pytest

from agent_eval_lab.clients.mock_openai import MockOpenAIClient
from agent_eval_lab.cases import load_case
from agent_eval_lab.parsers.tool_call_parser import (
    ParsedToolCallMessage,
    ToolCallParseError,
    parse_tool_call_response,
)


def _tool_call_response():
    """构造一个稳定的 mock tool call response。

    测试 parser 时，我们不直接手写正常 response，
    而是复用 B-2 已经实现的 MockOpenAIClient。

    这样可以验证：
    B-2 生成的 tool call response
    确实能被 C-1 的 parser 正确解析。
    """

    case = load_case("examples/tool_call_weather.yaml")
    response = MockOpenAIClient().run_case(case)
    return case, response


def test_parse_mock_tool_call_response() -> None:
    """parser 应该能解析 mock backend 生成的 tool call response。"""

    case, response = _tool_call_response()

    parsed = parse_tool_call_response(response)

    assert isinstance(parsed, ParsedToolCallMessage)
    assert parsed.model == "mock-model"
    assert parsed.choice_index == 0
    assert parsed.role == "assistant"
    assert parsed.finish_reason == "tool_calls"
    assert len(parsed.tool_calls) == 1

    tool_call = parsed.tool_calls[0]
    assert tool_call.id == "call_mock_001"
    assert tool_call.type == "function"
    assert tool_call.name == case.expected.tool_name
    assert tool_call.raw_arguments == '{"city": "Shenzhen", "unit": "celsius"}'
    assert tool_call.arguments == {
        "city": "Shenzhen",
        "unit": "celsius",
    }


def test_parse_tool_call_response_rejects_missing_tool_calls() -> None:
    """没有 message.tool_calls 时，tool call parser 应该明确失败。"""

    response = {
        "id": "chatcmpl-mock-broken",
        "object": "chat.completion",
        "model": "mock-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                },
                "finish_reason": "tool_calls",
            }
        ],
    }

    with pytest.raises(ToolCallParseError, match="tool_calls"):
        parse_tool_call_response(response)


def test_parse_tool_call_response_rejects_empty_tool_calls() -> None:
    """tool_calls 是空列表时，应该明确失败。"""

    response = {
        "id": "chatcmpl-mock-broken",
        "object": "chat.completion",
        "model": "mock-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }

    with pytest.raises(ToolCallParseError, match="must not be empty"):
        parse_tool_call_response(response)


def test_parse_tool_call_response_rejects_non_function_type() -> None:
    """阶段 C-1 只支持 type == function 的 tool call。"""

    response = {
        "id": "chatcmpl-mock-broken",
        "object": "chat.completion",
        "model": "mock-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_mock_001",
                            "type": "not_function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "Shenzhen"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }

    with pytest.raises(ToolCallParseError, match="type must be 'function'"):
        parse_tool_call_response(response)


def test_parse_tool_call_response_rejects_invalid_arguments_json() -> None:
    """function.arguments 不是合法 JSON string 时，应该明确失败。"""

    response = {
        "id": "chatcmpl-mock-broken",
        "object": "chat.completion",
        "model": "mock-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_mock_001",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "Shenzhen"',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }

    with pytest.raises(ToolCallParseError, match="valid JSON"):
        parse_tool_call_response(response)


def test_parse_tool_call_response_rejects_arguments_that_are_not_object() -> None:
    """arguments 虽然是合法 JSON，但不是 object 时，也应该失败。"""

    response = {
        "id": "chatcmpl-mock-broken",
        "object": "chat.completion",
        "model": "mock-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_mock_001",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '["Shenzhen"]',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }

    with pytest.raises(ToolCallParseError, match="JSON object"):
        parse_tool_call_response(response)


def test_parse_tool_call_response_supports_multiple_tool_calls() -> None:
    """parser 应该能解析多个 tool calls，但阶段 C-1 暂不做语义判断。"""

    response = {
        "id": "chatcmpl-mock-multiple-tools",
        "object": "chat.completion",
        "model": "mock-model",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_mock_001",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "Shenzhen"}',
                            },
                        },
                        {
                            "id": "call_mock_002",
                            "type": "function",
                            "function": {
                                "name": "get_time",
                                "arguments": '{"timezone": "Asia/Singapore"}',
                            },
                        },
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }

    parsed = parse_tool_call_response(response)

    assert len(parsed.tool_calls) == 2
    assert parsed.tool_calls[0].name == "get_weather"
    assert parsed.tool_calls[0].arguments == {"city": "Shenzhen"}
    assert parsed.tool_calls[1].name == "get_time"
    assert parsed.tool_calls[1].arguments == {"timezone": "Asia/Singapore"}
