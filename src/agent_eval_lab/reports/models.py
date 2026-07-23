"""Shared report data models for Agent Eval Lab."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def _generate_run_id() -> str:
    """生成一次执行的唯一标识。"""

    return f"run_{uuid4().hex}"


def _utc_now() -> datetime:
    """返回带时区信息的当前 UTC 时间。"""

    return datetime.now(timezone.utc)


class ReportCheck(BaseModel):
    """报告中的单个检查项。"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    status: Literal["pass", "fail", "skip"]
    reason: str = Field(min_length=1)
    details: dict[str, Any] = Field(
        default_factory=dict
    )


class RunReport(BaseModel):
    """一次 Agent Eval Lab 执行的统一报告数据。

    Markdown 和 JSONL 都从该模型生成。

    http_exchange 和 protocol_observations 使用 JSON-compatible
    数据，而不是直接引用 Transport 或 Protocol 层对象。
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(
        default_factory=_generate_run_id
    )
    created_at: datetime = Field(
        default_factory=_utc_now
    )

    case_id: str = Field(min_length=1)
    case_file: str = Field(min_length=1)
    backend: str = Field(min_length=1)
    model: str = Field(min_length=1)
    protocol: str = Field(
        default="chat_completions",
        min_length=1,
    )
    features: dict[str, bool]

    response_type: str = Field(min_length=1)

    raw_output: (
        dict[str, Any]
        | list[dict[str, Any]]
        | None
    ) = None

    parsed_output: dict[str, Any] | None = None

    http_exchange: dict[str, Any] | None = None

    protocol_observations: list[
        dict[str, Any]
    ] = Field(default_factory=list)

    checks: list[ReportCheck] = Field(
        default_factory=list
    )

    verdict: Literal["pass", "fail"]

    failure_reasons: list[str] = Field(
        default_factory=list
    )

    reproduction_command: str = Field(
        min_length=1
    )


def build_run_report(
    *,
    case_id: str,
    case_file: str,
    backend: str,
    model: str,
    features: dict[str, bool],
    response_type: str,
    raw_output: (
        dict[str, Any]
        | list[dict[str, Any]]
        | None
    ),
    parsed_output: dict[str, Any] | None,
    checks: list[ReportCheck],
    reproduction_command: str,
    protocol: str = "chat_completions",
    http_exchange: dict[str, Any] | None = None,
    protocol_observations: (
        list[dict[str, Any]] | None
    ) = None,
) -> RunReport:
    """根据执行、解析和检查结果构造 RunReport。

    Verdict 规则：

    - 任意 Check 为 fail，最终 verdict 为 fail
    - 没有 fail，最终 verdict 为 pass
    - skip 不视为失败
    """

    failed_checks = [
        check
        for check in checks
        if check.status == "fail"
    ]

    verdict: Literal["pass", "fail"] = (
        "fail"
        if failed_checks
        else "pass"
    )

    failure_reasons = [
        check.reason
        for check in failed_checks
    ]

    return RunReport(
        case_id=case_id,
        case_file=case_file,
        backend=backend,
        model=model,
        protocol=protocol,
        features=features,
        response_type=response_type,
        raw_output=raw_output,
        parsed_output=parsed_output,
        http_exchange=http_exchange,
        protocol_observations=list(
            protocol_observations or []
        ),
        checks=checks,
        verdict=verdict,
        failure_reasons=failure_reasons,
        reproduction_command=reproduction_command,
    )