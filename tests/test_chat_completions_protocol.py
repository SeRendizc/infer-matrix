from infermatrix.cases import InferCase
from infermatrix.protocols.chat_completions import (
    build_chat_completions_request,
)
import json
from datetime import datetime, timezone

import pytest

from infermatrix.protocols.chat_completions import (
    ChatCompletionsResponseDecodeError,
    ChatCompletionsResponseShapeError,
    parse_chat_completions_response,
)
from infermatrix.transports import (
    HeaderEntry,
    HttpExchange,
    HttpRequestRecord,
    HttpResponseRecord,
    HttpStatusError,
    WireBody,
)


def test_build_basic_chat_completions_request() -> None:
    case = InferCase.model_validate(
        {
            "case_id": "real-chat",
            "backend": {
                "provider": "openai_compatible",
                "base_url": "http://127.0.0.1:8000/v1",
            },
            "protocol": {
                "type": "chat_completions",
            },
            "model": "Qwen3-8B",
            "messages": [
                {
                    "role": "user",
                    "content": "你好",
                }
            ],
        }
    )

    request = build_chat_completions_request(case)

    assert request == {
        "model": "Qwen3-8B",
        "messages": [
            {
                "role": "user",
                "content": "你好",
            }
        ],
        "stream": False,
    }


def test_request_includes_tools() -> None:
    case = InferCase.model_validate(
        {
            "case_id": "tool-call",
            "protocol": {
                "type": "chat_completions",
            },
            "model": "mock-model",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "查询天气",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "city": {
                                    "type": "string",
                                }
                            },
                            "required": ["city"],
                        },
                    },
                }
            ],
        }
    )

    request = build_chat_completions_request(case)

    assert request["tools"] == case.tools


def test_request_adapter_supports_streaming_case() -> None:
    case = InferCase.model_validate(
        {
            "case_id": "streaming-chat",
            "protocol": {
                "type": "chat_completions",
            },
            "features": {
                "streaming": True,
            },
        }
    )

    payload = build_chat_completions_request(case)

    assert payload["stream"] is True


def _make_exchange(
    response_body: bytes,
    *,
    status_code: int = 200,
    reason_phrase: str = "OK",
) -> HttpExchange:
    """构造协议测试所需的最小 HTTP Exchange。"""

    return HttpExchange(
        started_at=datetime.now(timezone.utc),
        elapsed_ms=12.5,
        request=HttpRequestRecord(
            method="POST",
            url=(
                "http://127.0.0.1:8000/"
                "v1/chat/completions"
            ),
            headers=[
                HeaderEntry(
                    name="content-type",
                    value="application/json",
                )
            ],
            body=WireBody.from_bytes(
                b'{"model":"Qwen3-8B"}',
                content_type="application/json",
            ),
        ),
        response=HttpResponseRecord(
            status_code=status_code,
            reason_phrase=reason_phrase,
            http_version="HTTP/1.1",
            headers=[
                HeaderEntry(
                    name="content-type",
                    value="application/json",
                )
            ],
            body=WireBody.from_bytes(
                response_body,
                content_type="application/json",
            ),
        ),
    )


def test_parse_chat_completions_response() -> None:
    payload = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1_784_000_000,
        "model": "Qwen3-8B",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "你好",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 2,
            "total_tokens": 7,
        },
    }

    exchange = _make_exchange(
        json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")
    )

    result = parse_chat_completions_response(
        exchange
    )

    assert result.payload == payload
    assert result.observations == []


def test_response_records_non_fatal_observations() -> None:
    payload = {
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
    }

    exchange = _make_exchange(
        json.dumps(payload).encode("utf-8")
    )

    result = parse_chat_completions_response(
        exchange
    )

    codes = {
        observation.code
        for observation in result.observations
    }

    assert result.payload == payload
    assert codes == {
        "missing_id",
        "missing_model",
        "missing_created",
        "missing_object",
    }


def test_response_rejects_invalid_json() -> None:
    exchange = _make_exchange(
        b'{"choices": [}'
    )

    with pytest.raises(
        ChatCompletionsResponseDecodeError,
        match="not valid JSON",
    ):
        parse_chat_completions_response(
            exchange
        )


def test_response_rejects_non_object_json() -> None:
    exchange = _make_exchange(
        b'["not", "an", "object"]'
    )

    with pytest.raises(
        ChatCompletionsResponseShapeError,
        match="must be an object",
    ):
        parse_chat_completions_response(
            exchange
        )


def test_response_rejects_missing_choices() -> None:
    exchange = _make_exchange(
        b'{"id":"chatcmpl-123"}'
    )

    with pytest.raises(
        ChatCompletionsResponseShapeError,
        match="'choices' must be a list",
    ):
        parse_chat_completions_response(
            exchange
        )


def test_response_rejects_non_success_status() -> None:
    exchange = _make_exchange(
        b'{"error":{"message":"Unauthorized"}}',
        status_code=401,
        reason_phrase="Unauthorized",
    )

    with pytest.raises(
        HttpStatusError
    ) as error_info:
        parse_chat_completions_response(
            exchange
        )

    assert error_info.value.exchange is exchange