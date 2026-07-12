"""Run report assembler for InferMatrix.

阶段 D-5A 的目标：

    InferCase
    + RunResult
    + Parser 输出
    + Analyzer 输出
        ↓
    assemble_run_report()
        ↓
    RunReport

这个模块负责把阶段 A–C 产生的不同对象，
转换成阶段 D 统一使用的报告数据结构。

它不负责：

- 执行 Case
- 选择 Parser
- 调用 Analyzer
- 渲染 Markdown
- 写入文件
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from infermatrix.cases import InferCase
from infermatrix.reports.models import (
    ReportCheck,
    RunReport,
    build_run_report,
)
from infermatrix.runner import RunResult


class ReportAssemblyError(ValueError):
    """无法从现有执行结果安全构造报告时抛出。

    常见原因：

    - InferCase 和 RunResult 的 case_id 不一致
    - Backend 不一致
    - Model 不一致
    - RunResult 缺少应有的 response 或 chunks
    - Analyzer Result 缺少 name、status 或 reason
    - parsed_output 类型不受支持
    """


def assemble_run_report(
    *,
    case: InferCase,
    case_file: str | Path,
    run_result: RunResult,
    parsed_output: BaseModel | dict[str, Any] | None,
    check_results: Sequence[BaseModel | ReportCheck] = (),
) -> RunReport:
    """将真实执行链路产生的对象组装成 RunReport。

    Args:
        case:
            当前已经加载并校验的 InferCase。

        case_file:
            当前 Case 对应的 YAML 文件路径。

        run_result:
            Runner 执行 Case 后返回的 RunResult。

        parsed_output:
            Parser 产生的结构化结果。

            支持：
            - Pydantic BaseModel
            - dict
            - None

        check_results:
            Analyzer 产生的检查结果列表。

            当前可以直接传入：
            - SchemaCheckResult
            - ToolCallCheckResult
            - ReportCheck

    Returns:
        RunReport:
            可继续交给 Markdown 和 JSONL Writer 的统一报告对象。

    Raises:
        ReportAssemblyError:
            输入对象彼此不一致或数据结构无效。
    """

    _validate_run_matches_case(
        case=case,
        run_result=run_result,
    )

    raw_output = _extract_raw_output(run_result)

    normalized_parsed_output = _normalize_parsed_output(
        parsed_output
    )

    normalized_checks = [
        _normalize_check_result(check_result)
        for check_result in check_results
    ]

    # Runner 本身执行失败时，也需要进入统一报告结果。
    #
    # 当前 ReportCheck 不只可以表示 Analyzer 结果，
    # 也可以表示一次执行阶段的失败。
    if run_result.verdict == "failed":
        normalized_checks.insert(
            0,
            ReportCheck(
                name="execution",
                status="fail",
                reason=(
                    run_result.failure_reason
                    or "Case execution failed without a detailed reason."
                ),
                details={
                    "response_type": run_result.response_type,
                },
            ),
        )

    return build_run_report(
        case_id=case.case_id,
        case_file=str(case_file),
        backend=case.backend,
        model=case.model,
        features=case.features.model_dump(
            mode="json"
        ),
        response_type=run_result.response_type,
        raw_output=raw_output,
        parsed_output=normalized_parsed_output,
        checks=normalized_checks,
        reproduction_command=_build_reproduction_command(
            case_file
        ),
    )


def _validate_run_matches_case(
    *,
    case: InferCase,
    run_result: RunResult,
) -> None:
    """确认 RunResult 确实属于当前 InferCase。

    如果不检查，调用方可能错误地把：

        basic_chat 的 Case

    和：

        tool_call_weather 的 RunResult

    组装到同一份报告中。
    """

    if run_result.case_id != case.case_id:
        raise ReportAssemblyError(
            "RunResult case_id does not match InferCase: "
            f"{run_result.case_id!r} != {case.case_id!r}."
        )

    if run_result.backend != case.backend:
        raise ReportAssemblyError(
            "RunResult backend does not match InferCase: "
            f"{run_result.backend!r} != {case.backend!r}."
        )

    if run_result.model != case.model:
        raise ReportAssemblyError(
            "RunResult model does not match InferCase: "
            f"{run_result.model!r} != {case.model!r}."
        )


def _extract_raw_output(
    run_result: RunResult,
) -> dict[str, Any] | list[dict[str, Any]]:
    """根据 response_type 从 RunResult 中提取原始输出。"""

    if run_result.response_type == "chat_completion":
        if run_result.response is None:
            raise ReportAssemblyError(
                "RunResult response_type is 'chat_completion', "
                "but response is missing."
            )

        return run_result.response

    if run_result.response_type == "chat_completion_chunks":
        if run_result.chunks is None:
            raise ReportAssemblyError(
                "RunResult response_type is "
                "'chat_completion_chunks', but chunks are missing."
            )

        return run_result.chunks

    # RunResult 当前使用 Literal，理论上不会走到这里。
    # 保留明确错误，方便未来增加新的 response_type。
    raise ReportAssemblyError(
        "Unsupported RunResult response_type: "
        f"{run_result.response_type!r}."
    )


def _normalize_parsed_output(
    parsed_output: BaseModel | dict[str, Any] | None,
) -> dict[str, Any] | None:
    """把 Parser 输出统一转换成 JSON-compatible dict。

    Parser 当前返回的对象包括：

    - ParsedAssistantMessage
    - ParsedToolCallMessage
    - ParsedStreamMessage
    - ParsedStructuredOutput

    它们都是 Pydantic BaseModel，因此可以统一使用：

        model_dump(mode="json")
    """

    if parsed_output is None:
        return None

    if isinstance(parsed_output, BaseModel):
        return parsed_output.model_dump(
            mode="json"
        )

    if isinstance(parsed_output, dict):
        return dict(parsed_output)

    raise ReportAssemblyError(
        "parsed_output must be a Pydantic BaseModel, "
        f"a dict, or None; received {type(parsed_output).__name__}."
    )


def _normalize_check_result(
    check_result: BaseModel | ReportCheck,
) -> ReportCheck:
    """把不同 Analyzer Result 统一转换成 ReportCheck。

    当前 Analyzer Result 都有三个公共字段：

    - name
    - status
    - reason

    其他字段会放入 details。

    例如 SchemaCheckResult：

        name
        status
        reason
        expected_schema
        actual_data

    转换后：

        ReportCheck(
            name=name,
            status=status,
            reason=reason,
            details={
                "expected_schema": ...,
                "actual_data": ...,
            },
        )
    """

    if isinstance(check_result, ReportCheck):
        return check_result

    if not isinstance(check_result, BaseModel):
        raise ReportAssemblyError(
            "check_results must contain Pydantic models "
            f"or ReportCheck objects; received "
            f"{type(check_result).__name__}."
        )

    data = check_result.model_dump(
        mode="json"
    )

    missing_fields = [
        field_name
        for field_name in (
            "name",
            "status",
            "reason",
        )
        if field_name not in data
    ]

    if missing_fields:
        raise ReportAssemblyError(
            "Analyzer result is missing required report fields: "
            + ", ".join(missing_fields)
        )

    name = data.pop("name")
    status = data.pop("status")
    reason = data.pop("reason")

    # 不把大量无意义的 None 写进报告。
    details = {
        key: value
        for key, value in data.items()
        if value is not None
    }

    try:
        return ReportCheck(
            name=name,
            status=status,
            reason=reason,
            details=details,
        )
    except Exception as error:
        raise ReportAssemblyError(
            "Analyzer result cannot be converted into "
            f"ReportCheck: {error}"
        ) from error


def _build_reproduction_command(
    case_file: str | Path,
) -> str:
    """根据 Case 文件生成复现命令。

    统一使用正斜杠，使报告在 GitHub、Windows 和 Linux
    上都更容易阅读。

    路径外始终加双引号，因此包含空格时也可以执行。
    """

    path_text = Path(case_file).as_posix()

    return f'infermatrix run "{path_text}"'