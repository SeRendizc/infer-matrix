"""Buffered streaming client for OpenAI-compatible backends."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from infermatrix.cases import InferCase
from infermatrix.clients.openai_compatible import OpenAICompatibleClient
from infermatrix.protocols.chat_completions import (
    ProtocolObservation,
    build_chat_completions_request,
)
from infermatrix.protocols.chat_completions_stream import (
    parse_chat_completions_stream_response,
)
from infermatrix.transports.models import HttpExchange


class OpenAICompatibleStreamCallResult(BaseModel):
    """一次缓冲式 streaming 调用的协议结果与 HTTP 证据。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    exchange: HttpExchange
    chunks: list[dict[str, Any]]
    observations: list[ProtocolObservation]


class StreamingOpenAICompatibleClient(OpenAICompatibleClient):
    """复用同步 transport 执行完整 SSE response body。"""

    def stream_case(
        self,
        case: InferCase,
    ) -> OpenAICompatibleStreamCallResult:
        self._validate_backend(case)

        payload = build_chat_completions_request(case)
        request_body = self._serialize_request(payload)
        headers = self._build_headers(case)
        headers["Accept"] = "text/event-stream"

        exchange = self._transport.request(
            method="POST",
            url=self._build_chat_completions_url(case),
            headers=headers,
            content=request_body,
        )
        protocol_result = (
            parse_chat_completions_stream_response(exchange)
        )

        return OpenAICompatibleStreamCallResult(
            exchange=exchange,
            chunks=protocol_result.chunks,
            observations=protocol_result.observations,
        )
