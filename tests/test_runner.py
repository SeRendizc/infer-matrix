"""Tests for InferMatrix runner."""

import json

import pytest

from infermatrix.cases import load_case
from infermatrix.runner import UnsupportedBackendError, run_case, run_case_file


def test_runner_executes_basic_chat_case() -> None:
    """runner 应该能执行普通 chat case，并返回 chat_completion response。"""

    result = run_case_file("examples/basic_chat.yaml")

    assert result.case_id == "basic_chat_001"
    assert result.backend == "mock"
    assert result.model == "mock-model"
    assert result.verdict == "completed"
    assert result.response_type == "chat_completion"
    assert result.response is not None
    assert result.chunks is None

    message = result.response["choices"][0]["message"]
    assert message["role"] == "assistant"
    assert "InferMatrix" in message["content"]


def test_runner_executes_tool_call_case() -> None:
    """runner 应该能执行 tool calling case，并返回 tool_calls。"""

    result = run_case_file("examples/tool_call_weather.yaml")

    assert result.case_id == "tool_call_weather_001"
    assert result.response_type == "chat_completion"
    assert result.response is not None

    choice = result.response["choices"][0]
    message = choice["message"]

    assert message["role"] == "assistant"
    assert message["content"] is None
    assert choice["finish_reason"] == "tool_calls"

    tool_calls = message["tool_calls"]
    assert len(tool_calls) == 1

    function = tool_calls[0]["function"]
    assert function["name"] == "get_weather"

    arguments = json.loads(function["arguments"])
    assert arguments == {
        "city": "Shenzhen",
        "unit": "celsius",
    }


def test_runner_executes_streaming_case() -> None:
    """runner 应该能执行 streaming case，并返回 streaming chunks。"""

    result = run_case_file("examples/streaming_json.yaml")

    assert result.case_id == "streaming_json_001"
    assert result.response_type == "chat_completion_chunks"
    assert result.response is None
    assert result.chunks is not None
    assert len(result.chunks) >= 3

    first_chunk = result.chunks[0]
    assert first_chunk["object"] == "chat.completion.chunk"
    assert first_chunk["choices"][0]["delta"]["role"] == "assistant"

    final_chunk = result.chunks[-1]
    assert final_chunk["choices"][0]["finish_reason"] == "stop"

    merged_content = "".join(
        choice.get("delta", {}).get("content", "")
        for chunk in result.chunks
        for choice in chunk["choices"]
    )

    assert merged_content == '{"status": "ok", "answer": "InferMatrix streaming mock"}'


def test_runner_rejects_unsupported_backend() -> None:
    """runner 遇到不支持的 backend 时应该明确失败。"""

    case = load_case("examples/basic_chat.yaml")
    unsupported_case = case.model_copy(update={"backend": "unknown"})

    with pytest.raises(UnsupportedBackendError, match="Unsupported backend"):
        run_case(unsupported_case)