"""Runner for InferMatrix cases."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from infermatrix.cases import InferCase, load_case
from infermatrix.clients.mock_openai import MockOpenAIClient
from infermatrix.clients.openai_compatible import (
    OpenAICompatibleClient,
)
from infermatrix.protocols.chat_completions import (
    ProtocolObservation,
)
from infermatrix.transports.base import SyncHttpTransport
from infermatrix.transports.httpx_transport import (
    HttpxTransport,
)
from infermatrix.transports.models import HttpExchange


class UnsupportedBackendError(ValueError):
    """当前 Runner 不支持指定 Backend 时抛出。"""


class RunResult(BaseModel):
    """Runner 对不同 Backend 执行结果的统一表示。

    response 和 chunks 保存协议 Payload。

    http_exchange 保存真实 HTTP 调用证据。Mock Backend 没有
    HTTP 调用，因此该字段为 None。

    protocol_observations 保存不阻断解析的协议兼容性偏差。
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    backend: str
    protocol: str = "chat_completions"
    model: str

    response_type: Literal[
        "chat_completion",
        "chat_completion_chunks",
    ]

    verdict: Literal[
        "completed",
        "failed",
    ] = "completed"

    response: dict[str, Any] | None = None
    chunks: list[dict[str, Any]] | None = None

    http_exchange: HttpExchange | None = None

    protocol_observations: list[
        ProtocolObservation
    ] = Field(default_factory=list)

    failure_reason: str | None = None


def run_case(
    case: InferCase,
    *,
    transport: SyncHttpTransport | None = None,
    environ: Mapping[str, str] | None = None,
) -> RunResult:
    """执行一个已经加载好的 InferCase。

    transport:
        可选的外部 HTTP Transport。

        测试可以注入 Mock Transport；真实 CLI 调用不传时，
        Runner 会根据 Case Timeout 创建 HttpxTransport。

    environ:
        可选环境变量映射，主要用于测试 API Key 读取。
    """

    provider = case.backend.provider

    if provider == "mock":
        return _run_mock_case(case)

    if provider == "openai_compatible":
        if case.features.streaming:
            raise NotImplementedError(
                "Real OpenAI-compatible streaming "
                "will be implemented in E-1D2."
            )

        return _run_openai_compatible_case(
            case=case,
            transport=transport,
            environ=environ,
        )

    raise UnsupportedBackendError(
        "Unsupported backend provider: "
        f"{provider!r}."
    )


def _run_mock_case(
    case: InferCase,
) -> RunResult:
    """执行进程内 Mock Backend。"""

    client = MockOpenAIClient()

    if case.features.streaming:
        chunks = client.stream_case(case)

        return RunResult(
            case_id=case.case_id,
            backend=case.backend.provider,
            protocol=case.protocol.type,
            model=case.model,
            response_type=(
                "chat_completion_chunks"
            ),
            verdict="completed",
            chunks=chunks,
        )

    response = client.run_case(case)

    return RunResult(
        case_id=case.case_id,
        backend=case.backend.provider,
        protocol=case.protocol.type,
        model=case.model,
        response_type="chat_completion",
        verdict="completed",
        response=response,
    )


def _run_openai_compatible_case(
    *,
    case: InferCase,
    transport: SyncHttpTransport | None,
    environ: Mapping[str, str] | None,
) -> RunResult:
    """执行真实 OpenAI-compatible 非流式 Case。

    外部传入的 Transport 不由 Runner 关闭。

    Runner 自己创建的 Transport，会在调用结束后关闭。
    """

    if transport is not None:
        return _execute_with_transport(
            case=case,
            transport=transport,
            environ=environ,
        )

    with HttpxTransport(
        timeout=case.backend.timeout,
    ) as owned_transport:
        return _execute_with_transport(
            case=case,
            transport=owned_transport,
            environ=environ,
        )


def _execute_with_transport(
    *,
    case: InferCase,
    transport: SyncHttpTransport,
    environ: Mapping[str, str] | None,
) -> RunResult:
    """使用指定 Transport 执行真实 Client。"""

    client = OpenAICompatibleClient(
        transport=transport,
        environ=environ,
    )

    call_result = client.run_case(case)

    return RunResult(
        case_id=case.case_id,
        backend=case.backend.provider,
        protocol=case.protocol.type,
        model=case.model,
        response_type="chat_completion",
        verdict="completed",
        response=call_result.payload,
        http_exchange=call_result.exchange,
        protocol_observations=list(
            call_result.observations
        ),
    )


def run_case_file(
    path: str | Path,
    *,
    transport: SyncHttpTransport | None = None,
    environ: Mapping[str, str] | None = None,
) -> RunResult:
    """从 YAML 文件加载并执行 Case。"""

    case = load_case(path)

    return run_case(
        case,
        transport=transport,
        environ=environ,
    )