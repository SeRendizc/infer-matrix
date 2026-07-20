"""Buffered SSE adapter for Chat Completions streaming responses."""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from infermatrix.protocols.chat_completions import (
    ChatCompletionsProtocolError,
    ProtocolObservation,
)
from infermatrix.transports import decode_sse_chunks
from infermatrix.transports.errors import (
    SseDecodeError,
    require_success,
)
from infermatrix.transports.models import HttpExchange


class ChatCompletionsStreamResponseError(
    ChatCompletionsProtocolError
):
    """流式响应协议错误，并保留原始 HTTP 证据。"""

    def __init__(
        self,
        message: str,
        *,
        exchange: HttpExchange,
    ) -> None:
        self.exchange = exchange
        super().__init__(message)


class ChatCompletionsStreamResponseDecodeError(
    ChatCompletionsStreamResponseError
):
    """SSE wire data 或 event data 无法解码。"""


class ChatCompletionsStreamResponseShapeError(
    ChatCompletionsStreamResponseError
):
    """SSE event data 不符合最小 chunk envelope。"""


class ChatCompletionsStreamResponseResult(BaseModel):
    """缓冲式 SSE adapter 的输出。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunks: list[dict[str, Any]]
    observations: list[ProtocolObservation] = Field(
        default_factory=list
    )


def parse_chat_completions_stream_response(
    exchange: HttpExchange,
) -> ChatCompletionsStreamResponseResult:
    """从完整 HTTP response body 中解析 SSE JSON chunks。"""

    require_success(exchange)

    try:
        frames = decode_sse_chunks(
            [exchange.response.body.to_bytes()]
        )
    except SseDecodeError as error:
        raise ChatCompletionsStreamResponseDecodeError(
            f"Chat Completions SSE body cannot be decoded: {error}",
            exchange=exchange,
        ) from error

    chunks: list[dict[str, Any]] = []
    saw_done = False

    for frame in frames:
        event = frame.event

        if event is None:
            continue

        if event.is_done:
            saw_done = True
            continue

        try:
            payload = json.loads(event.data)
        except JSONDecodeError as error:
            raise ChatCompletionsStreamResponseDecodeError(
                "Chat Completions SSE event data is not valid JSON: "
                f"line {error.lineno}, column {error.colno}.",
                exchange=exchange,
            ) from error

        if not isinstance(payload, dict):
            raise ChatCompletionsStreamResponseShapeError(
                "Chat Completions stream chunk must be a JSON object.",
                exchange=exchange,
            )

        if not isinstance(payload.get("choices"), list):
            raise ChatCompletionsStreamResponseShapeError(
                "Chat Completions stream chunk field 'choices' "
                "must be a list.",
                exchange=exchange,
            )

        chunks.append(payload)

    if not chunks:
        raise ChatCompletionsStreamResponseShapeError(
            "Chat Completions stream must contain at least one chunk.",
            exchange=exchange,
        )

    observations: list[ProtocolObservation] = []

    if not saw_done:
        observations.append(
            ProtocolObservation(
                code="missing_done",
                path="$",
                message=(
                    "Chat Completions stream ended without "
                    "the '[DONE]' sentinel."
                ),
            )
        )

    return ChatCompletionsStreamResponseResult(
        chunks=chunks,
        observations=observations,
    )
