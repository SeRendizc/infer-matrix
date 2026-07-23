"""End-to-end execution pipeline for Agent Eval Lab."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from jsonschema import SchemaError
from pydantic import BaseModel, ConfigDict

from agent_eval_lab.analyzers.schema_checker import (
    check_json_schema,
)
from agent_eval_lab.analyzers.tool_call_checker import (
    ToolCallCheckError,
    check_tool_call,
)
from agent_eval_lab.cases import EvalCase
from agent_eval_lab.clients.openai_compatible import (
    OpenAICompatibleClientError,
)
from agent_eval_lab.parsers.chat_completion import (
    ChatCompletionParseError,
    parse_chat_completion_response,
)
from agent_eval_lab.parsers.stream_parser import (
    StreamParseError,
    parse_streaming_chunks,
)
from agent_eval_lab.parsers.structured_output_parser import (
    StructuredOutputParseError,
    parse_structured_output_text,
)
from agent_eval_lab.parsers.tool_call_parser import (
    ToolCallParseError,
    parse_tool_call_response,
)
from agent_eval_lab.protocols.chat_completions import (
    ChatCompletionsProtocolError,
    ChatCompletionsResponseError,
)
from agent_eval_lab.reports.assembler import (
    assemble_failure_report,
    assemble_run_report,
)
from agent_eval_lab.reports.models import RunReport
from agent_eval_lab.runner import (
    RunResult,
    UnsupportedBackendError,
    run_case,
)
from agent_eval_lab.transports.base import (
    SyncHttpTransport,
)
from agent_eval_lab.transports.errors import (
    HttpStatusError,
    HttpTransportError,
)
from agent_eval_lab.transports.models import (
    HttpExchange,
)


class PipelineResult(BaseModel):
    """一次完整 Pipeline 执行的结果。"""

    model_config = ConfigDict(
        extra="forbid"
    )

    report: RunReport
    exit_code: Literal[0, 1]


def run_case_pipeline(
    *,
    case: EvalCase,
    case_file: str | Path,
    transport: SyncHttpTransport | None = None,
    environ: Mapping[str, str] | None = None,
) -> PipelineResult:
    """运行完整 Case Pipeline，并生成统一报告。"""

    try:
        run_result = run_case(
            case,
            transport=transport,
            environ=environ,
        )
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
            http_exchange=(
                _extract_error_http_exchange(
                    error
                )
            ),
            details=(
                _build_execution_error_details(
                    error
                )
            ),
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
            response_type=(
                run_result.response_type
            ),
            raw_output=raw_output,
            http_exchange=(
                run_result.http_exchange
            ),
            protocol_observations=(
                run_result.protocol_observations
            ),
            details={
                "error_type": (
                    type(error).__name__
                ),
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
            response_type=(
                run_result.response_type
            ),
            raw_output=raw_output,
            http_exchange=(
                run_result.http_exchange
            ),
            protocol_observations=(
                run_result.protocol_observations
            ),
            details={
                "error_type": (
                    type(error).__name__
                ),
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
        1
        if report.verdict == "fail"
        else 0
    )

    return PipelineResult(
        report=report,
        exit_code=exit_code,
    )


def _parse_and_analyze(
    *,
    case: EvalCase,
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
                "Streaming RunResult does not "
                "contain chunks."
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
            "stream": (
                parsed_stream.model_dump(
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

        return (
            parsed_tool_message,
            list(tool_checks),
        )

    parsed_message = (
        parse_chat_completion_response(
            run_result.response
        )
    )

    if not case.features.structured_output:
        return parsed_message, []

    structured_output = (
        parse_structured_output_text(
            parsed_message.content
        )
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
    """提取 Pipeline 已经获得的协议原始输出。"""

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
    """提取执行异常中可安全写入报告的数据。"""

    details: dict[str, Any] = {
        "error_type": type(error).__name__,
    }

    if isinstance(
        error,
        HttpTransportError,
    ):
        details["transport_failure"] = (
            error.failure.model_dump(
                mode="json"
            )
        )

    elif isinstance(
        error,
        HttpStatusError,
    ):
        details["status_code"] = (
            error.exchange.response.status_code
        )
        details["reason_phrase"] = (
            error.exchange.response.reason_phrase
        )

    return details


def _extract_error_http_exchange(
    error: Exception,
) -> HttpExchange | None:
    """从执行异常中提取已存在的 HTTP Exchange。"""

    if isinstance(
        error,
        HttpStatusError,
    ):
        return error.exchange

    if isinstance(
        error,
        ChatCompletionsResponseError,
    ):
        return error.exchange

    return None