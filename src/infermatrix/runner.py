"""Runner for InferMatrix cases.

runner 是 InferMatrix 的执行中枢。

阶段 B-2 的 runner 只做一件事：
把 InferCase 交给合适的 client 执行，并返回结构化 RunResult。

注意：
runner 不应该变成“什么都干”的大杂烩。

它不负责：
- 读取 YAML 的底层细节：交给 cases.load_case
- 生成 response：交给 client
- 解析 response：交给 parser
- 深度分析结果：交给后续 analyzer
- 输出正式报告：交给后续 reports
"""

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from infermatrix.cases import InferCase, load_case
from infermatrix.clients.mock_openai import MockOpenAIClient


class UnsupportedBackendError(ValueError):
    """当前 runner 不支持指定 backend 时抛出。"""


class RunResult(BaseModel):
    """一次 case 执行的最小结果。

    阶段 B-2 的 RunResult 是“最小 verdict”，不是正式报告。

    字段说明：
    - case_id: 当前 case ID
    - backend: 使用的 backend
    - model: 使用的模型名
    - response_type: 普通 response 还是 streaming chunks
    - verdict: 当前只表示 runner 是否完成执行
    - response: 非流式 response
    - chunks: streaming chunks
    - failure_reason: 失败原因，阶段 B-2 先预留
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    backend: str
    model: str
    response_type: Literal["chat_completion", "chat_completion_chunks"]
    verdict: Literal["completed", "failed"] = "completed"
    response: dict[str, Any] | None = None
    chunks: list[dict[str, Any]] | None = None
    failure_reason: str | None = None


def run_case(case: InferCase) -> RunResult:
    """执行一个已经加载好的 InferCase。

    Args:
        case: 已经通过 Pydantic 校验的 InferCase。

    Returns:
        RunResult: 结构化执行结果。

    Raises:
        UnsupportedBackendError: 当前 backend 不支持。
    """

    if case.backend != "mock":
        raise UnsupportedBackendError(
            f"Unsupported backend in Phase B-2 runner: {case.backend}"
        )

    client = MockOpenAIClient()

    if case.features.streaming:
        chunks = client.stream_case(case)
        return RunResult(
            case_id=case.case_id,
            backend=case.backend,
            model=case.model,
            response_type="chat_completion_chunks",
            verdict="completed",
            chunks=chunks,
        )

    response = client.run_case(case)
    return RunResult(
        case_id=case.case_id,
        backend=case.backend,
        model=case.model,
        response_type="chat_completion",
        verdict="completed",
        response=response,
    )


def run_case_file(path: str | Path) -> RunResult:
    """从 YAML 文件加载并执行一个 case。"""

    case = load_case(path)
    return run_case(case)