import json
from datetime import datetime, timezone

import pytest

from infermatrix.cases import InferCase
from infermatrix.protocols.chat_completions import (
    build_chat_completions_request,
)
from infermatrix.protocols.chat_completions_stream import (
    ChatCompletionsStreamResponseDecodeError,
    parse_chat_completions_stream_response,
)
from infermatrix.transports.models import (
    HeaderEntry,
    HttpExchange,
    HttpRequestRecord,
    HttpResponseRecord,
    WireBody,
)


def _make_streaming_case() -> InferCase:
    return InferCase.model_validate(
        {
            "case_id": "stream-protocol",
            "backend": {
                "provider": "openai_compatible",
                "base_url": "http://127.0.0.1:8000/v1",
            },
            "protocol": {"type": "chat_completions"},
            "model": "Qwen3-8B",
            "features": {"streaming": True},
            "messages": [
                {"role": "user", "content": "你好"}
            ],
        }
    )


def _make_exchange(response_body: bytes) -> HttpExchange:
    return HttpExchange(
        started_at=datetime.now(timezone.utc),
        elapsed_ms=12.5,
        request=HttpRequestRecord(
            method="POST",
            url="http://127.0.0.1:8000/v1/chat/completions",
            headers=[],
            body=WireBody.from_bytes(
                b'{"stream":true}',
                content_type="application/json",
            ),
        ),
        response=HttpResponseRecord(
            status_code=200,
            reason_phrase="OK",
            http_version="HTTP/1.1",
            headers=[
                HeaderEntry(
                    name="content-type",
                    value="text/event-stream",
                )
            ],
            body=WireBody.from_bytes(
                response_body,
                content_type="text/event-stream",
            ),
        ),
    )


def _event(payload: dict[str, object]) -> bytes:
    return (
        "data: " + json.dumps(payload) + "\n\n"
    ).encode("utf-8")


def test_streaming_request_sets_stream_true() -> None:
    payload = build_chat_completions_request(
        _make_streaming_case()
    )

    assert payload["stream"] is True


def test_stream_response_returns_json_chunks() -> None:
    chunks = [
        {
            "id": "chatcmpl-1",
            "choices": [
                {"index": 0, "delta": {"content": "你"}}
            ],
        },
        {
            "id": "chatcmpl-1",
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
        },
    ]
    body = b"".join(_event(chunk) for chunk in chunks)
    body += b"data: [DONE]\n\n"

    result = parse_chat_completions_stream_response(
        _make_exchange(body)
    )

    assert result.chunks == chunks
    assert result.observations == []


def test_invalid_json_retains_exchange() -> None:
    exchange = _make_exchange(b"data: {broken}\n\n")

    with pytest.raises(
        ChatCompletionsStreamResponseDecodeError,
        match="not valid JSON",
    ) as error_info:
        parse_chat_completions_stream_response(exchange)

    assert error_info.value.exchange is exchange


def test_missing_done_is_non_fatal_observation() -> None:
    chunk = {"choices": []}
    exchange = _make_exchange(_event(chunk))

    result = parse_chat_completions_stream_response(exchange)

    assert result.chunks == [chunk]
    assert [item.code for item in result.observations] == [
        "missing_done"
    ]
