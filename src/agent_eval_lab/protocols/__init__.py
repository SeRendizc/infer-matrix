"""Agent Eval Lab API protocol adapters."""

from agent_eval_lab.protocols.chat_completions import (
    ChatCompletionsProtocolError,
    ChatCompletionsResponseDecodeError,
    ChatCompletionsResponseError,
    ChatCompletionsResponseResult,
    ChatCompletionsResponseShapeError,
    ProtocolObservation,
    build_chat_completions_request,
    parse_chat_completions_response,
)

__all__ = [
    "ChatCompletionsProtocolError",
    "ChatCompletionsResponseDecodeError",
    "ChatCompletionsResponseError",
    "ChatCompletionsResponseResult",
    "ChatCompletionsResponseShapeError",
    "ProtocolObservation",
    "build_chat_completions_request",
    "parse_chat_completions_response",
]