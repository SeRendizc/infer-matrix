"""Tests for shared report data models."""

from infermatrix.reports.models import (
    ReportCheck,
    RunReport,
    build_run_report,
)


def test_build_run_report_passes_when_no_check_fails() -> None:
    """没有 fail 检查项时，报告 verdict 应该是 pass。"""

    checks = [
        ReportCheck(
            name="tool_name",
            status="pass",
            reason="Tool name matches expected value.",
        ),
        ReportCheck(
            name="tool_arguments_schema",
            status="skip",
            reason="Arguments Schema check was not requested.",
        ),
    ]

    report = build_run_report(
        case_id="tool_call_weather_001",
        case_file="examples/tool_call_weather.yaml",
        backend="mock",
        model="mock-model",
        features={
            "streaming": False,
            "tool_calling": True,
            "structured_output": False,
        },
        response_type="chat_completion",
        raw_output={
            "object": "chat.completion",
        },
        parsed_output={
            "tool_name": "get_weather",
            "arguments": {
                "city": "Shenzhen",
            },
        },
        checks=checks,
        reproduction_command=(
            "infermatrix run examples/tool_call_weather.yaml"
        ),
    )

    assert isinstance(report, RunReport)
    assert report.run_id.startswith("run_")
    assert report.created_at.tzinfo is not None
    assert report.verdict == "pass"
    assert report.failure_reasons == []


def test_build_run_report_fails_when_any_check_fails() -> None:
    """任意检查项失败时，报告 verdict 应该是 fail。"""

    checks = [
        ReportCheck(
            name="tool_name",
            status="pass",
            reason="Tool name matches expected value.",
        ),
        ReportCheck(
            name="tool_arguments_schema",
            status="fail",
            reason="'city' is a required property.",
        ),
    ]

    report = build_run_report(
        case_id="tool_call_weather_001",
        case_file="examples/tool_call_weather.yaml",
        backend="mock",
        model="mock-model",
        features={
            "streaming": False,
            "tool_calling": True,
            "structured_output": False,
        },
        response_type="chat_completion",
        raw_output={
            "object": "chat.completion",
        },
        parsed_output={
            "tool_name": "get_weather",
            "arguments": {},
        },
        checks=checks,
        reproduction_command=(
            "infermatrix run examples/tool_call_weather.yaml"
        ),
    )

    assert report.verdict == "fail"
    assert report.failure_reasons == [
        "'city' is a required property."
    ]


def test_each_report_gets_a_unique_run_id() -> None:
    """两次报告构造应该得到不同 run_id。"""

    common_arguments = {
        "case_id": "basic_chat_001",
        "case_file": "examples/basic_chat.yaml",
        "backend": "mock",
        "model": "mock-model",
        "features": {
            "streaming": False,
            "tool_calling": False,
            "structured_output": False,
        },
        "response_type": "chat_completion",
        "raw_output": {
            "object": "chat.completion",
        },
        "parsed_output": {
            "content": "hello",
        },
        "checks": [],
        "reproduction_command": (
            "infermatrix run examples/basic_chat.yaml"
        ),
    }

    first_report = build_run_report(**common_arguments)
    second_report = build_run_report(**common_arguments)

    assert first_report.run_id != second_report.run_id