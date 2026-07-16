"""InferMatrix API protocol adapters."""

from infermatrix.protocols.chat_completions import (
    ChatCompletionsProtocolError,
    ChatCompletionsResponseDecodeError,
    ChatCompletionsResponseResult,
    ChatCompletionsResponseShapeError,
    ProtocolObservation,
    build_chat_completions_request,
    parse_chat_completions_response,
)

__all__ = [
    "ChatCompletionsProtocolError",
    "ChatCompletionsResponseDecodeError",
    "ChatCompletionsResponseResult",
    "ChatCompletionsResponseShapeError",
    "ProtocolObservation",
    "build_chat_completions_request",
    "parse_chat_completions_response",
]