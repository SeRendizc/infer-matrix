import json

import httpx

from agent_eval_lab.cases import EvalCase
from agent_eval_lab.clients.openai_compatible_stream import (
    StreamingOpenAICompatibleClient,
)
from agent_eval_lab.transports import HttpxTransport


def _make_case() -> EvalCase:
    return EvalCase.model_validate(
        {
            "case_id": "stream-client",
            "backend": {
                "provider": "openai_compatible",
                "base_url": "http://127.0.0.1:8000/v1",
                "api_key_env": "TEST_API_KEY",
            },
            "protocol": {"type": "chat_completions"},
            "model": "Qwen3-8B",
            "features": {"streaming": True},
            "messages": [
                {"role": "user", "content": "你好"}
            ],
        }
    )


def test_client_runs_buffered_streaming_case() -> None:
    case = _make_case()
    chunk = {
        "id": "chatcmpl-stream",
        "choices": [
            {
                "index": 0,
                "delta": {"content": "你好"},
                "finish_reason": "stop",
            }
        ],
    }
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["accept"] = request.headers["accept"]
        captured["authorization"] = request.headers[
            "authorization"
        ]
        captured["body"] = json.loads(request.content)

        body = (
            "data: " + json.dumps(chunk) + "\n\n"
            "data: [DONE]\n\n"
        ).encode("utf-8")
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=body,
        )

    with HttpxTransport(
        timeout=case.backend.timeout,
        transport=httpx.MockTransport(handler),
    ) as transport:
        result = StreamingOpenAICompatibleClient(
            transport=transport,
            environ={"TEST_API_KEY": "stream-secret"},
        ).stream_case(case)

    assert captured == {
        "url": "http://127.0.0.1:8000/v1/chat/completions",
        "accept": "text/event-stream",
        "authorization": "Bearer stream-secret",
        "body": {
            "model": "Qwen3-8B",
            "messages": [
                {"role": "user", "content": "你好"}
            ],
            "stream": True,
        },
    }
    assert result.chunks == [chunk]
    assert result.observations == []
    assert result.exchange.response.body.to_bytes().endswith(
        b"data: [DONE]\n\n"
    )
    assert "stream-secret" not in result.exchange.model_dump_json()
