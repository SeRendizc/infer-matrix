"""Shared report data models for InferMatrix.

阶段 D 的第一步不是立即拼接 Markdown，
而是定义 Markdown 和 JSONL 共用的报告数据结构。

数据流：

    InferCase
    + RunResult
    + parsed output
    + analyzer results
        ↓
    RunReport
        ↓
    Markdown renderer / JSONL writer

这样 Markdown 和 JSONL 使用同一份数据，不会分别维护两套逻辑。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def _generate_run_id() -> str:
    """生成一次执行的唯一标识。

    uuid4() 几乎不会重复，适合标识彼此独立的运行。

    添加 run_ 前缀后，日志和文件名更容易辨认：
        run_a12b34...
    """

    return f"run_{uuid4().hex}"


def _utc_now() -> datetime:
    """返回带时区信息的当前 UTC 时间。"""

    return datetime.now(timezone.utc)


class ReportCheck(BaseModel):
    """报告中的单个检查项。

    这个模型统一包装不同 analyzer 的结果。

    例如：

    - json_schema
    - tool_name
    - tool_arguments_schema

    reports 层不需要知道检查结果原来来自哪个具体类，
    只需要统一的 name、status、reason 和 details。
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    status: Literal["pass", "fail", "skip"]
    reason: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)


class RunReport(BaseModel):
    """一次 InferMatrix 执行的统一报告数据。

    这个对象暂时不关心最终输出是 Markdown 还是 JSONL。

    字段分成五组：

    1. 运行身份
       run_id、created_at

    2. Case 信息
       case_id、case_file、backend、model、features

    3. 执行结果
       response_type、raw_output、parsed_output

    4. 分析结果
       checks、verdict、failure_reasons

    5. 可复现信息
       reproduction_command
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(default_factory=_generate_run_id)
    created_at: datetime = Field(default_factory=_utc_now)

    case_id: str = Field(min_length=1)
    case_file: str = Field(min_length=1)
    backend: str = Field(min_length=1)
    model: str = Field(min_length=1)
    features: dict[str, bool]

    response_type: str = Field(min_length=1)
    raw_output: dict[str, Any] | list[dict[str, Any]] | None = None
    parsed_output: dict[str, Any] | None = None

    checks: list[ReportCheck] = Field(default_factory=list)
    verdict: Literal["pass", "fail"]
    failure_reasons: list[str] = Field(default_factory=list)

    reproduction_command: str = Field(min_length=1)


def build_run_report(
    *,
    case_id: str,
    case_file: str,
    backend: str,
    model: str,
    features: dict[str, bool],
    response_type: str,
    raw_output: dict[str, Any] | list[dict[str, Any]] | None,
    parsed_output: dict[str, Any] | None,
    checks: list[ReportCheck],
    reproduction_command: str,
) -> RunReport:
    """根据执行、解析和检查结果构造 RunReport。

    Verdict 规则：

    - 任意 check 为 fail → verdict 为 fail
    - 没有 fail → verdict 为 pass
    - skip 不视为失败

    failure_reasons 只收集失败检查的 reason，
    后续 Markdown 报告可以直接显示。
    """

    failed_checks = [
        check
        for check in checks
        if check.status == "fail"
    ]

    verdict: Literal["pass", "fail"] = (
        "fail" if failed_checks else "pass"
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
        features=features,
        response_type=response_type,
        raw_output=raw_output,
        parsed_output=parsed_output,
        checks=checks,
        verdict=verdict,
        failure_reasons=failure_reasons,
        reproduction_command=reproduction_command,
    )