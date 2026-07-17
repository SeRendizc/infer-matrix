"""真实 OpenAI-compatible Backend Client。"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict

from infermatrix.cases import InferCase
from infermatrix.protocols.chat_completions import (
    ChatCompletionsResponseResult,
    build_chat_completions_request,
    parse_chat_completions_response,
)
from infermatrix.transports.base import SyncHttpTransport
from infermatrix.transports.models import HttpExchange


class OpenAICompatibleClientError(RuntimeError):
    """OpenAI-compatible Client 执行失败。"""


class OpenAICompatibleClientConfigurationError(
    OpenAICompatibleClientError
):
    """Case 或 Client 配置不完整。"""


class OpenAICompatibleRequestSerializationError(
    OpenAICompatibleClientError
):
    """Request Payload 无法序列化为标准 JSON。"""


class OpenAICompatibleCallResult(BaseModel):
    """一次真实 OpenAI-compatible 调用的完整结果。

    同时保存：

    - 原始 HTTP Exchange
    - 协议层解析结果
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    exchange: HttpExchange
    protocol_result: ChatCompletionsResponseResult

    @property
    def payload(self) -> dict[str, Any]:
        """返回经过协议层校验的原始响应对象。"""

        return self.protocol_result.payload

    @property
    def observations(self):
        """返回非致命协议兼容性偏差。"""

        return self.protocol_result.observations


class OpenAICompatibleClient:
    """调用真实 OpenAI-compatible HTTP Backend。

    Transport 由外部注入，因此：

    - Client 不绑定 HTTPX
    - 测试时可以注入 Mock Transport
    - 多次调用可以复用连接池
    - Transport 生命周期由调用方管理
    """

    def __init__(
        self,
        *,
        transport: SyncHttpTransport,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self._transport = transport
        self._environ = (
            os.environ
            if environ is None
            else environ
        )

    def run_case(
        self,
        case: InferCase,
    ) -> OpenAICompatibleCallResult:
        """执行一个非流式 Chat Completions Case。"""

        self._validate_backend(case)

        request_payload = (
            build_chat_completions_request(case)
        )

        request_body = self._serialize_request(
            request_payload
        )

        headers = self._build_headers(case)
        url = self._build_chat_completions_url(case)

        exchange = self._transport.request(
            method="POST",
            url=url,
            headers=headers,
            content=request_body,
        )

        protocol_result = (
            parse_chat_completions_response(exchange)
        )

        return OpenAICompatibleCallResult(
            exchange=exchange,
            protocol_result=protocol_result,
        )

    def _validate_backend(
        self,
        case: InferCase,
    ) -> None:
        """确认 Case 要求调用真实兼容服务。"""

        if (
            case.backend.provider
            != "openai_compatible"
        ):
            raise (
                OpenAICompatibleClientConfigurationError(
                    "OpenAICompatibleClient requires "
                    "backend.provider='openai_compatible'."
                )
            )

        if case.backend.base_url is None:
            raise (
                OpenAICompatibleClientConfigurationError(
                    "OpenAI-compatible backend requires "
                    "backend.base_url."
                )
            )

    def _build_headers(
        self,
        case: InferCase,
    ) -> dict[str, str]:
        """构造 HTTP Header，并从环境变量读取 API Key。"""

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        api_key_env = case.backend.api_key_env

        # 本地 vLLM 等服务可能没有开启 API Key，
        # 因此 api_key_env 本身是可选的。
        if api_key_env is None:
            return headers

        raw_api_key = self._environ.get(api_key_env)

        if (
            raw_api_key is None
            or not raw_api_key.strip()
        ):
            raise (
                OpenAICompatibleClientConfigurationError(
                    "API key environment variable "
                    f"'{api_key_env}' is missing or empty."
                )
            )

        headers["Authorization"] = (
            f"Bearer {raw_api_key.strip()}"
        )

        return headers

    @staticmethod
    def _build_chat_completions_url(
        case: InferCase,
    ) -> str:
        """在 Base URL 后拼接 Chat Completions 路径。"""

        assert case.backend.base_url is not None

        base_url = str(
            case.backend.base_url
        ).rstrip("/")

        return f"{base_url}/chat/completions"

    @staticmethod
    def _serialize_request(
        payload: dict[str, Any],
    ) -> bytes:
        """生成严格 UTF-8 JSON Request Body。"""

        try:
            text = json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as error:
            raise (
                OpenAICompatibleRequestSerializationError(
                    "Chat Completions request payload "
                    "cannot be serialized as valid JSON."
                )
            ) from error

        return text.encode("utf-8")