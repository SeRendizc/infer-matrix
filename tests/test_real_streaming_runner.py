import json

import httpx

from infermatrix.cases import InferCase
from infermatrix.runner import run_case
from infermatrix.transports import HttpxTransport


def test_runner_executes_real_buffered_streaming_case() -> None:
    case = InferCase.model_validate(
        {
            "case_id": "runner-real-stream",
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
    chunk = {
        "id": "chatcmpl-runner-stream",
        "choices": [
            {
                "index": 0,
                "delta": {"content": "你好"},
                "finish_reason": "stop",
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["stream"] is True
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=(
                "data: " + json.dumps(chunk) + "\n\n"
                "data: [DONE]\n\n"
            ).encode("utf-8"),
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

    assert result.response_type == "chat_completion_chunks"
    assert result.response is None
    assert result.chunks == [chunk]
    assert result.http_exchange is not None
    assert result.protocol_observations == []
