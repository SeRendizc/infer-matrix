import json

import httpx
import pytest

from infermatrix.cases import InferCase
from infermatrix.clients.openai_compatible import (
    OpenAICompatibleClient,
    OpenAICompatibleClientConfigurationError,
)
from infermatrix.transports import HttpxTransport


def _make_case(
    *,
    api_key_env: str | None = None,
) -> InferCase:
    backend: dict[str, object] = {
        "provider": "openai_compatible",
        "base_url": "http://127.0.0.1:8000/v1",
    }

    if api_key_env is not None:
        backend["api_key_env"] = api_key_env

    return InferCase.model_validate(
        {
            "case_id": "real-chat",
            "backend": backend,
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


def test_client_runs_non_streaming_case() -> None:
    case = _make_case(
        api_key_env="TEST_API_KEY"
    )

    response_payload = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 1_784_000_000,
        "model": "Qwen3-8B",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "你好，我是 Qwen。",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 2,
            "completion_tokens": 5,
            "total_tokens": 7,
        },
    }

    captured: dict[str, object] = {}

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["authorization"] = (
            request.headers.get("authorization")
        )
        captured["body"] = json.loads(
            request.content
        )

        return httpx.Response(
            status_code=200,
            headers={
                "content-type": "application/json"
            },
            json=response_payload,
        )

    with HttpxTransport(
        timeout=case.backend.timeout,
        transport=httpx.MockTransport(handler),
    ) as transport:
        client = OpenAICompatibleClient(
            transport=transport,
            environ={
                "TEST_API_KEY": "test-secret"
            },
        )

        result = client.run_case(case)

    assert captured["method"] == "POST"
    assert captured["url"] == (
        "http://127.0.0.1:8000/"
        "v1/chat/completions"
    )
    assert captured["authorization"] == (
        "Bearer test-secret"
    )
    assert captured["body"] == {
        "model": "Qwen3-8B",
        "messages": [
            {
                "role": "user",
                "content": "你好",
            }
        ],
        "stream": False,
    }

    assert result.payload == response_payload
    assert result.observations == []

    # 原始 Transport 证据中不能泄漏 API Key。
    assert "test-secret" not in (
        result.exchange.model_dump_json()
    )


def test_client_supports_backend_without_api_key() -> None:
    case = _make_case()

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            request.headers.get("authorization")
            is None
        )

        return httpx.Response(
            status_code=200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1,
                "model": "Qwen3-8B",
                "choices": [],
            },
        )

    with HttpxTransport(
        timeout=case.backend.timeout,
        transport=httpx.MockTransport(handler),
    ) as transport:
        result = OpenAICompatibleClient(
            transport=transport,
            environ={},
        ).run_case(case)

    assert result.payload["choices"] == []


def test_client_rejects_missing_api_key() -> None:
    case = _make_case(
        api_key_env="MISSING_API_KEY"
    )

    request_was_sent = False

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal request_was_sent
        request_was_sent = True

        return httpx.Response(
            status_code=500
        )

    with HttpxTransport(
        timeout=case.backend.timeout,
        transport=httpx.MockTransport(handler),
    ) as transport:
        client = OpenAICompatibleClient(
            transport=transport,
            environ={},
        )

        with pytest.raises(
            OpenAICompatibleClientConfigurationError,
            match="MISSING_API_KEY",
        ):
            client.run_case(case)

    assert request_was_sent is False


def test_client_preserves_protocol_observations() -> None:
    case = _make_case()

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
        result = OpenAICompatibleClient(
            transport=transport,
            environ={},
        ).run_case(case)

    observation_codes = {
        item.code
        for item in result.observations
    }

    assert observation_codes == {
        "missing_id",
        "missing_model",
        "missing_created",
        "missing_object",
    }


def test_client_rejects_mock_backend() -> None:
    case = InferCase.model_validate(
        {
            "case_id": "wrong-backend",
            "backend": {
                "provider": "mock",
            },
        }
    )

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise AssertionError(
            "HTTP request must not be sent."
        )

    with HttpxTransport(
        timeout=case.backend.timeout,
        transport=httpx.MockTransport(handler),
    ) as transport:
        client = OpenAICompatibleClient(
            transport=transport,
            environ={},
        )

        with pytest.raises(
            OpenAICompatibleClientConfigurationError,
            match="openai_compatible",
        ):
            client.run_case(case)