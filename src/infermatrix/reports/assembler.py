"""Run report assembler for InferMatrix."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from infermatrix.cases import InferCase
from infermatrix.protocols.chat_completions import (
    ProtocolObservation,
)
from infermatrix.reports.models import (
    ReportCheck,
    RunReport,
    build_run_report,
)
from infermatrix.runner import RunResult
from infermatrix.transports.models import (
    HttpExchange,
)


class ReportAssemblyError(ValueError):
    """无法从现有执行结果安全构造报告时抛出。"""


def assemble_run_report(
    *,
    case: InferCase,
    case_file: str | Path,
    run_result: RunResult,
    parsed_output: BaseModel | dict[str, Any] | None,
    check_results: Sequence[
        BaseModel | ReportCheck
    ] = (),
) -> RunReport:
    """将执行链路产生的对象组装成 RunReport。"""

    _validate_run_matches_case(
        case=case,
        run_result=run_result,
    )

    raw_output = _extract_raw_output(
        run_result
    )

    normalized_parsed_output = (
        _normalize_parsed_output(
            parsed_output
        )
    )

    normalized_checks = [
        _normalize_check_result(
            check_result
        )
        for check_result in check_results
    ]

    if run_result.verdict == "failed":
        normalized_checks.insert(
            0,
            ReportCheck(
                name="execution",
                status="fail",
                reason=(
                    run_result.failure_reason
                    or (
                        "Case execution failed "
                        "without a detailed reason."
                    )
                ),
                details={
                    "response_type": (
                        run_result.response_type
                    ),
                },
            ),
        )

    return build_run_report(
        case_id=case.case_id,
        case_file=str(case_file),
        backend=case.backend.provider,
        model=case.model,
        protocol=run_result.protocol,
        features=case.features.model_dump(
            mode="json"
        ),
        response_type=run_result.response_type,
        raw_output=raw_output,
        parsed_output=normalized_parsed_output,
        http_exchange=(
            _normalize_http_exchange(
                run_result.http_exchange
            )
        ),
        protocol_observations=(
            _normalize_protocol_observations(
                run_result.protocol_observations
            )
        ),
        checks=normalized_checks,
        reproduction_command=(
            _build_reproduction_command(
                case_file
            )
        ),
    )


def assemble_failure_report(
    *,
    case: InferCase,
    case_file: str | Path,
    stage: str,
    reason: str,
    response_type: str,
    raw_output: (
        dict[str, Any]
        | list[dict[str, Any]]
        | None
    ) = None,
    details: dict[str, Any] | None = None,
    http_exchange: HttpExchange | None = None,
    protocol_observations: Sequence[
        ProtocolObservation
    ] = (),
) -> RunReport:
    """为执行、解析或分析阶段的异常构造失败报告。"""

    failure_check = ReportCheck(
        name=stage,
        status="fail",
        reason=reason,
        details=details or {},
    )

    return build_run_report(
        case_id=case.case_id,
        case_file=str(case_file),
        backend=case.backend.provider,
        model=case.model,
        protocol=case.protocol.type,
        features=case.features.model_dump(
            mode="json"
        ),
        response_type=response_type,
        raw_output=raw_output,
        parsed_output=None,
        http_exchange=(
            _normalize_http_exchange(
                http_exchange
            )
        ),
        protocol_observations=(
            _normalize_protocol_observations(
                protocol_observations
            )
        ),
        checks=[
            failure_check,
        ],
        reproduction_command=(
            _build_reproduction_command(
                case_file
            )
        ),
    )


def _validate_run_matches_case(
    *,
    case: InferCase,
    run_result: RunResult,
) -> None:
    """确认 RunResult 确实属于当前 InferCase。"""

    if run_result.case_id != case.case_id:
        raise ReportAssemblyError(
            "RunResult case_id does not match InferCase: "
            f"{run_result.case_id!r} != "
            f"{case.case_id!r}."
        )

    if (
        run_result.backend
        != case.backend.provider
    ):
        raise ReportAssemblyError(
            "RunResult backend does not match InferCase: "
            f"{run_result.backend!r} != "
            f"{case.backend.provider!r}."
        )

    if run_result.model != case.model:
        raise ReportAssemblyError(
            "RunResult model does not match InferCase: "
            f"{run_result.model!r} != "
            f"{case.model!r}."
        )

    if (
        run_result.protocol
        != case.protocol.type
    ):
        raise ReportAssemblyError(
            "RunResult protocol does not match InferCase: "
            f"{run_result.protocol!r} != "
            f"{case.protocol.type!r}."
        )


def _extract_raw_output(
    run_result: RunResult,
) -> dict[str, Any] | list[dict[str, Any]]:
    """根据 response_type 从 RunResult 提取协议 Payload。"""

    if (
        run_result.response_type
        == "chat_completion"
    ):
        if run_result.response is None:
            raise ReportAssemblyError(
                "RunResult response_type is "
                "'chat_completion', but response "
                "is missing."
            )

        return run_result.response

    if (
        run_result.response_type
        == "chat_completion_chunks"
    ):
        if run_result.chunks is None:
            raise ReportAssemblyError(
                "RunResult response_type is "
                "'chat_completion_chunks', but "
                "chunks are missing."
            )

        return run_result.chunks

    raise ReportAssemblyError(
        "Unsupported RunResult response_type: "
        f"{run_result.response_type!r}."
    )


def _normalize_parsed_output(
    parsed_output: BaseModel | dict[str, Any] | None,
) -> dict[str, Any] | None:
    """把 Parser 输出统一转换成 JSON-compatible dict。"""

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
        "a dict, or None; received "
        f"{type(parsed_output).__name__}."
    )


def _normalize_check_result(
    check_result: BaseModel | ReportCheck,
) -> ReportCheck:
    """把不同 Analyzer Result 统一转换为 ReportCheck。"""

    if isinstance(check_result, ReportCheck):
        return check_result

    if not isinstance(check_result, BaseModel):
        raise ReportAssemblyError(
            "check_results must contain Pydantic "
            "models or ReportCheck objects; received "
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
            "Analyzer result is missing required "
            "report fields: "
            + ", ".join(missing_fields)
        )

    name = data.pop("name")
    status = data.pop("status")
    reason = data.pop("reason")

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
            "Analyzer result cannot be converted "
            f"into ReportCheck: {error}"
        ) from error


def _normalize_http_exchange(
    exchange: HttpExchange | None,
) -> dict[str, Any] | None:
    """把 HTTP Exchange 转换为报告可序列化数据。"""

    if exchange is None:
        return None

    return exchange.model_dump(
        mode="json"
    )


def _normalize_protocol_observations(
    observations: Sequence[
        ProtocolObservation
    ],
) -> list[dict[str, Any]]:
    """把协议观察结果转换为报告数据。"""

    return [
        observation.model_dump(
            mode="json"
        )
        for observation in observations
    ]


def _build_reproduction_command(
    case_file: str | Path,
) -> str:
    """根据 Case 文件生成复现命令。"""

    path_text = Path(
        case_file
    ).as_posix()

    return (
        f'infermatrix run "{path_text}"'
    )