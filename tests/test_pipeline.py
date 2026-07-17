"""Tests for the InferMatrix end-to-end pipeline."""

from pathlib import Path

from infermatrix.cases import load_case, BackendConfig
from infermatrix.pipeline import run_case_pipeline
from infermatrix.runner import RunResult

import httpx

from infermatrix.transports import HttpxTransport


def test_pipeline_passes_basic_chat() -> None:
    """普通 Chat Case 应生成 PASS 报告。"""

    case_file = Path("examples/basic_chat.yaml")
    case = load_case(case_file)

    result = run_case_pipeline(
        case=case,
        case_file=case_file,
    )

    assert result.exit_code == 0
    assert result.report.verdict == "pass"
    assert result.report.raw_output is not None
    assert result.report.parsed_output is not None


def test_pipeline_passes_streaming_structured_output() -> None:
    """Streaming Structured Output 应完成两层解析。"""

    case_file = Path(
        "examples/streaming_json.yaml"
    )
    case = load_case(case_file)

    result = run_case_pipeline(
        case=case,
        case_file=case_file,
    )

    assert result.exit_code == 0
    assert result.report.verdict == "pass"

    assert result.report.parsed_output is not None
    assert "stream" in result.report.parsed_output
    assert (
        "structured_output"
        in result.report.parsed_output
    )

    assert result.report.checks[0].name == (
        "json_schema"
    )


def test_pipeline_reports_analyzer_failure() -> None:
    """Tool Arguments 不符合 Schema 时应生成 FAIL 报告。"""

    case_file = Path(
        "examples/tool_call_weather.yaml"
    )
    case = load_case(case_file)

    broken_metadata = dict(case.metadata)
    broken_metadata["mock_tool_arguments"] = {
        "unit": "celsius",
    }

    broken_case = case.model_copy(
        update={
            "metadata": broken_metadata,
        }
    )

    result = run_case_pipeline(
        case=broken_case,
        case_file=case_file,
    )

    assert result.exit_code == 1
    assert result.report.verdict == "fail"

    argument_check = next(
        check
        for check in result.report.checks
        if check.name == "tool_arguments_schema"
    )

    assert argument_check.status == "fail"
    assert "required" in argument_check.reason


def test_pipeline_reports_runner_failure() -> None:
    """真实 Backend 传输失败应生成 execution FAIL 报告。"""

    case_file = Path("examples/basic_chat.yaml")
    case = load_case(case_file)

    real_case = case.model_copy(
        update={
            "backend": BackendConfig(
                provider="openai_compatible",
                base_url=(
                    "http://127.0.0.1:8000/v1"
                ),
            ),
        }
    )

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "synthetic connection failure",
            request=request,
        )

    with HttpxTransport(
        timeout=real_case.backend.timeout,
        transport=httpx.MockTransport(handler),
    ) as transport:
        result = run_case_pipeline(
            case=real_case,
            case_file=case_file,
            transport=transport,
            environ={},
        )

    assert result.exit_code == 1
    assert result.report.verdict == "fail"

    execution_check = result.report.checks[0]

    assert execution_check.name == "execution"
    assert execution_check.status == "fail"
    assert (
        execution_check.details["error_type"]
        == "HttpTransportError"
    )

    transport_failure = (
        execution_check.details[
            "transport_failure"
        ]
    )

    assert (
        transport_failure["kind"]
        == "connect_error"
    )
    assert (
        transport_failure["request"]["method"]
        == "POST"
    )


def test_pipeline_reports_parser_failure(
    monkeypatch,
) -> None:
    """Raw Response 不合法时应生成 parsing FAIL 报告。"""

    case_file = Path("examples/basic_chat.yaml")
    case = load_case(case_file)

    def fake_run_case(
        _case,
        *,
        transport=None,
        environ=None,
    ):
        assert transport is None
        assert environ is None

        return RunResult(
            case_id=_case.case_id,
            backend=_case.backend.provider,
            protocol=_case.protocol.type,
            model=_case.model,
            response_type="chat_completion",
            verdict="completed",
            response={
                "choices": [],
            },
        )

    monkeypatch.setattr(
        "infermatrix.pipeline.run_case",
        fake_run_case,
    )

    result = run_case_pipeline(
        case=case,
        case_file=case_file,
    )

    assert result.exit_code == 1
    assert result.report.verdict == "fail"
    assert result.report.raw_output == {
        "choices": [],
    }

    assert result.report.checks[0].name == (
        "parsing"
    )