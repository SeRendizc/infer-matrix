"""Tests for InferMatrix RunReport assembler."""

from pathlib import Path

import pytest

from infermatrix.analyzers.schema_checker import (
    check_json_schema,
)
from infermatrix.analyzers.tool_call_checker import (
    check_tool_call,
)
from infermatrix.cases import load_case
from infermatrix.parsers.chat_completion import (
    parse_chat_completion_response,
)
from infermatrix.parsers.stream_parser import (
    parse_streaming_chunks,
)
from infermatrix.parsers.structured_output_parser import (
    parse_structured_output_text,
)
from infermatrix.parsers.tool_call_parser import (
    parse_tool_call_response,
)
from infermatrix.reports.assembler import (
    ReportAssemblyError,
    assemble_run_report,
)
from infermatrix.reports.models import RunReport
from infermatrix.runner import RunResult, run_case


def test_assemble_basic_chat_report() -> None:
    """普通 Chat Case 应能组装成通过报告。"""

    case_file = Path("examples/basic_chat.yaml")
    case = load_case(case_file)

    run_result = run_case(case)

    assert run_result.response is not None

    parsed_message = parse_chat_completion_response(
        run_result.response
    )

    report = assemble_run_report(
        case=case,
        case_file=case_file,
        run_result=run_result,
        parsed_output=parsed_message,
        check_results=[],
    )

    assert isinstance(report, RunReport)
    assert report.case_id == "basic_chat_001"
    assert report.backend == "mock"
    assert report.model == "mock-model"
    assert report.response_type == "chat_completion"
    assert report.verdict == "pass"
    assert report.failure_reasons == []
    assert report.checks == []

    assert report.parsed_output is not None
    assert report.parsed_output["role"] == "assistant"
    assert "InferMatrix" in report.parsed_output["content"]

    assert report.raw_output == run_result.response

    assert report.reproduction_command == (
        'infermatrix run "examples/basic_chat.yaml"'
    )


def test_assemble_streaming_schema_report() -> None:
    """Streaming Structured Output 的 Schema 结果应进入报告。"""

    case_file = Path("examples/streaming_json.yaml")
    case = load_case(case_file)

    run_result = run_case(case)

    assert run_result.chunks is not None

    parsed_stream = parse_streaming_chunks(
        run_result.chunks
    )

    structured_output = parse_structured_output_text(
        parsed_stream.merged_content
    )

    schema_result = check_json_schema(
        case,
        structured_output,
    )

    report = assemble_run_report(
        case=case,
        case_file=case_file,
        run_result=run_result,
        parsed_output=structured_output,
        check_results=[
            schema_result,
        ],
    )

    assert report.verdict == "pass"
    assert len(report.checks) == 1

    report_check = report.checks[0]

    assert report_check.name == "json_schema"
    assert report_check.status == "pass"
    assert (
        "matches expected JSON Schema"
        in report_check.reason
    )

    assert "expected_schema" in report_check.details
    assert "actual_data" in report_check.details

    assert isinstance(report.raw_output, list)


def test_assemble_tool_call_report() -> None:
    """Tool Call Parser 和 Analyzer 结果应进入报告。"""

    case_file = Path(
        "examples/tool_call_weather.yaml"
    )
    case = load_case(case_file)

    run_result = run_case(case)

    assert run_result.response is not None

    parsed_message = parse_tool_call_response(
        run_result.response
    )

    tool_check_results = check_tool_call(
        case,
        parsed_message,
    )

    report = assemble_run_report(
        case=case,
        case_file=case_file,
        run_result=run_result,
        parsed_output=parsed_message,
        check_results=tool_check_results,
    )

    assert report.verdict == "pass"
    assert len(report.checks) == 2

    check_names = {
        check.name
        for check in report.checks
    }

    assert check_names == {
        "tool_name",
        "tool_arguments_schema",
    }

    assert report.parsed_output is not None

    tool_calls = report.parsed_output["tool_calls"]

    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "get_weather"
    assert tool_calls[0]["arguments"]["city"] == "Shenzhen"


def test_assembler_rejects_mismatched_case_id() -> None:
    """InferCase 与 RunResult 的 case_id 不一致时应失败。"""

    case = load_case(
        "examples/basic_chat.yaml"
    )

    wrong_run_result = RunResult(
        case_id="different_case",
        backend=case.backend.provider,
        model=case.model,
        response_type="chat_completion",
        verdict="completed",
        response={
            "object": "chat.completion",
        },
    )

    with pytest.raises(
        ReportAssemblyError,
        match="case_id does not match",
    ):
        assemble_run_report(
            case=case,
            case_file="examples/basic_chat.yaml",
            run_result=wrong_run_result,
            parsed_output=None,
        )


def test_assembler_rejects_missing_response() -> None:
    """chat_completion 类型缺少 response 时应失败。"""

    case = load_case(
        "examples/basic_chat.yaml"
    )

    broken_run_result = RunResult(
        case_id=case.case_id,
        backend=case.backend.provider,
        model=case.model,
        response_type="chat_completion",
        verdict="completed",
        response=None,
    )

    with pytest.raises(
        ReportAssemblyError,
        match="response is missing",
    ):
        assemble_run_report(
            case=case,
            case_file="examples/basic_chat.yaml",
            run_result=broken_run_result,
            parsed_output=None,
        )


def test_failed_run_becomes_failed_report() -> None:
    """Runner 执行失败时应产生 execution fail 检查。"""

    case = load_case(
        "examples/basic_chat.yaml"
    )

    failed_run_result = RunResult(
        case_id=case.case_id,
        backend=case.backend.provider,
        model=case.model,
        response_type="chat_completion",
        verdict="failed",
        response={},
        failure_reason="Mock backend execution failed.",
    )

    report = assemble_run_report(
        case=case,
        case_file="examples/basic_chat.yaml",
        run_result=failed_run_result,
        parsed_output=None,
    )

    assert report.verdict == "fail"
    assert report.failure_reasons == [
        "Mock backend execution failed."
    ]

    assert len(report.checks) == 1
    assert report.checks[0].name == "execution"
    assert report.checks[0].status == "fail"


def test_assembler_converts_pydantic_parser_output() -> None:
    """Pydantic Parser 输出应该自动转换成 dict。"""

    case = load_case(
        "examples/basic_chat.yaml"
    )
    run_result = run_case(case)

    assert run_result.response is not None

    parsed_message = parse_chat_completion_response(
        run_result.response
    )

    report = assemble_run_report(
        case=case,
        case_file="examples/basic_chat.yaml",
        run_result=run_result,
        parsed_output=parsed_message,
    )

    assert isinstance(report.parsed_output, dict)
    assert report.parsed_output == (
        parsed_message.model_dump(mode="json")
    )