"""Tests for Agent Eval Lab runner."""

import json

import httpx

from agent_eval_lab.cases import EvalCase
from agent_eval_lab.runner import (
    run_case,
    run_case_file,
)
from agent_eval_lab.transports import HttpxTransport


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
    assert "Agent Eval Lab" in message["content"]

    assert result.protocol == "chat_completions"
    assert result.http_exchange is None
    assert result.protocol_observations == []


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

    assert result.protocol == "chat_completions"
    assert result.http_exchange is None
    assert result.protocol_observations == []


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

    assert merged_content == '{"status": "ok", "answer": "Agent Eval Lab streaming mock"}'

    assert result.protocol == "chat_completions"
    assert result.http_exchange is None
    assert result.protocol_observations == []


def _make_real_backend_case(
    *,
    streaming: bool = False,
    api_key_env: str | None = None,
) -> EvalCase:
    backend: dict[str, object] = {
        "provider": "openai_compatible",
        "base_url": "http://127.0.0.1:8000/v1",
    }

    if api_key_env is not None:
        backend["api_key_env"] = api_key_env

    return EvalCase.model_validate(
        {
            "case_id": "runner-real-chat",
            "backend": backend,
            "protocol": {
                "type": "chat_completions",
            },
            "model": "Qwen3-8B",
            "features": {
                "streaming": streaming,
            },
            "messages": [
                {
                    "role": "user",
                    "content": "你好",
                }
            ],
        }
    )


def test_runner_supports_openai_compatible_backend() -> None:
    case = _make_real_backend_case(
        api_key_env="TEST_API_KEY"
    )

    response_payload = {
        "id": "chatcmpl-runner-test",
        "object": "chat.completion",
        "created": 1_784_000_000,
        "model": "Qwen3-8B",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "你好，我是模型。",
                },
                "finish_reason": "stop",
            }
        ],
    }

    captured_request: dict[str, object] = {}

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        captured_request["url"] = str(request.url)
        captured_request["body"] = json.loads(
            request.content
        )
        captured_request["authorization"] = (
            request.headers.get("authorization")
        )

        return httpx.Response(
            status_code=200,
            headers={
                "content-type": "application/json",
            },
            json=response_payload,
        )

    with HttpxTransport(
        timeout=case.backend.timeout,
        transport=httpx.MockTransport(handler),
    ) as transport:
        result = run_case(
            case,
            transport=transport,
            environ={
                "TEST_API_KEY": "runner-secret",
            },
        )

    assert result.case_id == case.case_id
    assert result.backend == "openai_compatible"
    assert result.protocol == "chat_completions"
    assert result.response_type == "chat_completion"
    assert result.verdict == "completed"

    assert result.response == response_payload
    assert result.chunks is None

    assert result.http_exchange is not None
    assert result.protocol_observations == []

    assert captured_request["url"] == (
        "http://127.0.0.1:8000/"
        "v1/chat/completions"
    )

    assert captured_request["authorization"] == (
        "Bearer runner-secret"
    )

    assert captured_request["body"] == {
        "model": "Qwen3-8B",
        "messages": [
            {
                "role": "user",
                "content": "你好",
            }
        ],
        "stream": False,
    }

    # Runner 保存的证据必须经过脱敏。
    assert "runner-secret" not in (
        result.http_exchange.model_dump_json()
    )


def test_runner_preserves_protocol_observations() -> None:
    case = _make_real_backend_case()

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "你好",
                        },
                        "finish_reason": "stop",
                    }
                ]
            },
        )

    with HttpxTransport(
        timeout=case.backend.timeout,
        transport=httpx.MockTransport(handler),
    ) as transport:
        result = run_case(
            case,
            transport=transport,
            environ={},
        )

    codes = {
        observation.code
        for observation
        in result.protocol_observations
    }

    assert codes == {
        "missing_id",
        "missing_model",
        "missing_created",
        "missing_object",
    }
