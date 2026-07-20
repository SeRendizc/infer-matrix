"""OpenAI Chat Completions 协议适配。"""

from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from infermatrix.cases import InferCase
from infermatrix.transports.errors import require_success
from infermatrix.transports.models import HttpExchange


class ChatCompletionsProtocolError(ValueError):
    """Chat Completions 协议适配失败。"""


class ChatCompletionsResponseError(
    ChatCompletionsProtocolError
):
    """Chat Completions Response 协议错误。

    即使响应无法被正确解析，也保留原始 HTTP Exchange，
    以便 Pipeline 和 Report 保存完整请求、响应及状态信息。
    """

    def __init__(
        self,
        message: str,
        *,
        exchange: HttpExchange,
    ) -> None:
        self.exchange = exchange
        super().__init__(message)


class ChatCompletionsResponseDecodeError(
    ChatCompletionsResponseError
):
    """HTTP Body 无法解码为 Chat Completions JSON。"""


class ChatCompletionsResponseShapeError(
    ChatCompletionsResponseError
):
    """JSON 顶层结构不符合 Chat Completions 协议。"""


class ProtocolObservation(BaseModel):
    """一条非致命协议兼容性偏差。

    这类偏差不会阻止后续 Parser 工作，但会被写入报告，
    供不同 OpenAI-compatible Backend 之间进行行为比较。
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    code: str
    path: str
    message: str


class ChatCompletionsResponseResult(BaseModel):
    """Chat Completions Response Adapter 的输出。"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    payload: dict[str, Any]
    observations: list[ProtocolObservation] = Field(
        default_factory=list
    )


def build_chat_completions_request(
    case: InferCase,
) -> dict[str, Any]:
    """把 InferCase 转换成 Chat Completions Request。

    本函数只负责协议转换，不负责发送 HTTP 请求。
    """

    if case.protocol.type != "chat_completions":
        raise ChatCompletionsProtocolError(
            "Chat Completions adapter requires "
            "protocol.type='chat_completions'."
        )

    payload: dict[str, Any] = {
        "model": case.model,
        "messages": [
            message.model_dump(mode="json")
            for message in case.messages
        ],
        "stream": case.features.streaming,
    }

    if case.tools:
        payload["tools"] = case.tools

    return payload


def parse_chat_completions_response(
    exchange: HttpExchange,
) -> ChatCompletionsResponseResult:
    """解析非流式 Chat Completions HTTP Response。

    本函数负责：

    - HTTP 成功状态检查
    - UTF-8 检查
    - JSON 解码
    - 顶层 Protocol Envelope 检查
    - 非致命协议偏差收集

    本函数不负责解析 assistant message、tool_calls 或业务预期。
    """

    require_success(exchange)

    body = exchange.response.body

    if body.encoding != "utf-8":
        raise ChatCompletionsResponseDecodeError(
            "Chat Completions response body must be valid UTF-8.",
            exchange=exchange,
        )

    try:
        payload = json.loads(body.data)
    except JSONDecodeError as error:
        raise ChatCompletionsResponseDecodeError(
            "Chat Completions response body is not valid JSON: "
            f"line {error.lineno}, column {error.colno}.",
            exchange=exchange,
        ) from error

    if not isinstance(payload, dict):
        raise ChatCompletionsResponseShapeError(
            "Chat Completions response JSON must be an object.",
            exchange=exchange,
        )

    choices = payload.get("choices")

    if not isinstance(choices, list):
        raise ChatCompletionsResponseShapeError(
            "Chat Completions response field "
            "'choices' must be a list.",
            exchange=exchange,
        )

    observations = _collect_response_observations(
        payload
    )

    return ChatCompletionsResponseResult(
        payload=payload,
        observations=observations,
    )


def _collect_response_observations(
    payload: dict[str, Any],
) -> list[ProtocolObservation]:
    """收集不会阻止后续 Parser 执行的协议兼容性偏差。"""

    observations: list[ProtocolObservation] = []

    _observe_required_string(
        payload=payload,
        key="id",
        observations=observations,
    )

    _observe_required_string(
        payload=payload,
        key="model",
        observations=observations,
    )

    created = payload.get("created")

    if created is None:
        observations.append(
            ProtocolObservation(
                code="missing_created",
                path="created",
                message=(
                    "Chat Completions response is missing "
                    "the 'created' field."
                ),
            )
        )
    elif not isinstance(created, int):
        observations.append(
            ProtocolObservation(
                code="invalid_created_type",
                path="created",
                message=(
                    "Chat Completions response field "
                    "'created' should be an integer."
                ),
            )
        )

    object_type = payload.get("object")

    if object_type is None:
        observations.append(
            ProtocolObservation(
                code="missing_object",
                path="object",
                message=(
                    "Chat Completions response is missing "
                    "the 'object' field."
                ),
            )
        )
    elif object_type != "chat.completion":
        observations.append(
            ProtocolObservation(
                code="unexpected_object",
                path="object",
                message=(
                    "Expected response object "
                    "'chat.completion', got "
                    f"{object_type!r}."
                ),
            )
        )

    usage = payload.get("usage")

    if usage is not None and not isinstance(
        usage,
        dict,
    ):
        observations.append(
            ProtocolObservation(
                code="invalid_usage_type",
                path="usage",
                message=(
                    "Chat Completions response field "
                    "'usage' should be an object when present."
                ),
            )
        )

    return observations


def _observe_required_string(
    *,
    payload: dict[str, Any],
    key: str,
    observations: list[ProtocolObservation],
) -> None:
    """记录缺失或类型错误的字符串元数据字段。"""

    value = payload.get(key)

    if value is None:
        observations.append(
            ProtocolObservation(
                code=f"missing_{key}",
                path=key,
                message=(
                    "Chat Completions response is missing "
                    f"the '{key}' field."
                ),
            )
        )
        return

    if not isinstance(value, str):
        observations.append(
            ProtocolObservation(
                code=f"invalid_{key}_type",
                path=key,
                message=(
                    "Chat Completions response field "
                    f"'{key}' should be a string."
                ),
            )
        )