"""End-to-end execution pipeline for InferMatrix.

阶段 D-6 的目标：

    InferCase
        ↓
    Runner
        ↓
    Parser
        ↓
    Analyzer
        ↓
    RunReport

Pipeline 保证：

- 正常执行会生成 PASS 或 FAIL 报告
- Analyzer 不符合预期会生成 FAIL 报告
- Parser 抛出已知解析错误时会生成 FAIL 报告
- Runner 抛出已知执行错误时会生成 FAIL 报告

Pipeline 不负责写入文件。
文件写入仍然属于 reports writer。
"""

from __future__ import annotations
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from jsonschema import SchemaError
from pydantic import BaseModel, ConfigDict

from infermatrix.analyzers.schema_checker import (
    check_json_schema,
)
from infermatrix.analyzers.tool_call_checker import (
    ToolCallCheckError,
    check_tool_call,
)
from infermatrix.cases import InferCase
from infermatrix.parsers.chat_completion import (
    ChatCompletionParseError,
    parse_chat_completion_response,
)
from infermatrix.parsers.stream_parser import (
    StreamParseError,
    parse_streaming_chunks,
)
from infermatrix.parsers.structured_output_parser import (
    StructuredOutputParseError,
    parse_structured_output_text,
)
from infermatrix.parsers.tool_call_parser import (
    ToolCallParseError,
    parse_tool_call_response,
)
from infermatrix.reports.assembler import (
    assemble_failure_report,
    assemble_run_report,
)
from infermatrix.reports.models import RunReport
from infermatrix.runner import (
    RunResult,
    UnsupportedBackendError,
    run_case,
)
from infermatrix.clients.openai_compatible import (
    OpenAICompatibleClientError,
)
from infermatrix.protocols.chat_completions import (
    ChatCompletionsProtocolError,
)
from infermatrix.transports.base import SyncHttpTransport
from infermatrix.transports.errors import (
    HttpStatusError,
    HttpTransportError,
)


class PipelineResult(BaseModel):
    """一次完整 Pipeline 执行的结果。

    report:
        无论成功或失败，都尽量生成 RunReport。

    exit_code:
        0 表示 Case 满足预期。
        1 表示执行、解析、分析或检查失败。
    """

    model_config = ConfigDict(extra="forbid")

    report: RunReport
    exit_code: Literal[0, 1]


def run_case_pipeline(
    *,
    case: InferCase,
    case_file: str | Path,
    transport: SyncHttpTransport | None = None,
    environ: Mapping[str, str] | None = None,
) -> PipelineResult:
    """运行完整 Case Pipeline，并生成统一报告。"""

    try:
        run_result = run_case(case, transport=transport, environ=environ)
    except (
        UnsupportedBackendError,
        NotImplementedError,
        OpenAICompatibleClientError,
        HttpTransportError,
        HttpStatusError,
        ChatCompletionsProtocolError,
    ) as error:
        report = assemble_failure_report(
            case=case,
            case_file=case_file,
            stage="execution",
            reason=str(error),
            response_type="execution_error",
            raw_output=None,
            details=_build_execution_error_details(error),
        )

        return PipelineResult(
            report=report,
            exit_code=1,
        )

    raw_output = _extract_available_raw_output(
        run_result
    )

    try:
        parsed_output, check_results = (
            _parse_and_analyze(
                case=case,
                run_result=run_result,
            )
        )
    except (
        ChatCompletionParseError,
        ToolCallParseError,
        StreamParseError,
        StructuredOutputParseError,
    ) as error:
        report = assemble_failure_report(
            case=case,
            case_file=case_file,
            stage="parsing",
            reason=str(error),
            response_type=run_result.response_type,
            raw_output=raw_output,
            details={
                "error_type": type(error).__name__,
            },
        )

        return PipelineResult(
            report=report,
            exit_code=1,
        )
    except (
        ToolCallCheckError,
        SchemaError,
    ) as error:
        report = assemble_failure_report(
            case=case,
            case_file=case_file,
            stage="analysis",
            reason=str(error),
            response_type=run_result.response_type,
            raw_output=raw_output,
            details={
                "error_type": type(error).__name__,
            },
        )

        return PipelineResult(
            report=report,
            exit_code=1,
        )

    report = assemble_run_report(
        case=case,
        case_file=case_file,
        run_result=run_result,
        parsed_output=parsed_output,
        check_results=check_results,
    )

    exit_code: Literal[0, 1] = (
        1 if report.verdict == "fail" else 0
    )

    return PipelineResult(
        report=report,
        exit_code=exit_code,
    )


def _parse_and_analyze(
    *,
    case: InferCase,
    run_result: RunResult,
) -> tuple[
    BaseModel | dict[str, Any] | None,
    list[BaseModel],
]:
    """根据 Case Feature 选择 Parser 和 Analyzer。"""

    if (
        run_result.response_type
        == "chat_completion_chunks"
    ):
        if run_result.chunks is None:
            raise StreamParseError(
                "Streaming RunResult does not contain chunks."
            )

        parsed_stream = parse_streaming_chunks(
            run_result.chunks
        )

        if not case.features.structured_output:
            return parsed_stream, []

        structured_output = (
            parse_structured_output_text(
                parsed_stream.merged_content
            )
        )

        schema_result = check_json_schema(
            case,
            structured_output,
        )

        combined_output = {
            "stream": parsed_stream.model_dump(
                mode="json"
            ),
            "structured_output": (
                structured_output.model_dump(
                    mode="json"
                )
            ),
        }

        return combined_output, [
            schema_result,
        ]

    if run_result.response is None:
        raise ChatCompletionParseError(
            "Non-streaming RunResult does not "
            "contain a response."
        )

    if case.features.tool_calling:
        parsed_tool_message = (
            parse_tool_call_response(
                run_result.response
            )
        )

        tool_checks = check_tool_call(
            case=case,
            parsed_message=parsed_tool_message,
        )

        return parsed_tool_message, list(tool_checks)

    parsed_message = parse_chat_completion_response(
        run_result.response
    )

    if not case.features.structured_output:
        return parsed_message, []

    structured_output = parse_structured_output_text(
        parsed_message.content
    )

    schema_result = check_json_schema(
        case,
        structured_output,
    )

    combined_output = {
        "assistant_message": (
            parsed_message.model_dump(
                mode="json"
            )
        ),
        "structured_output": (
            structured_output.model_dump(
                mode="json"
            )
        ),
    }

    return combined_output, [
        schema_result,
    ]


def _extract_available_raw_output(
    run_result: RunResult,
) -> (
    dict[str, Any]
    | list[dict[str, Any]]
    | None
):
    """提取 Pipeline 当前已经获得的原始输出。"""

    if (
        run_result.response_type
        == "chat_completion"
    ):
        return run_result.response

    if (
        run_result.response_type
        == "chat_completion_chunks"
    ):
        return run_result.chunks

    return None


def _build_execution_error_details(
    error: Exception,
) -> dict[str, Any]:
    """提取执行异常中可安全写入报告的结构化证据。"""

    details: dict[str, Any] = {
        "error_type": type(error).__name__,
    }

    if isinstance(error, HttpTransportError):
        details["transport_failure"] = (
            error.failure.model_dump(mode="json")
        )

    elif isinstance(error, HttpStatusError):
        details["http_exchange"] = (
            error.exchange.model_dump(mode="json")
        )

    return details