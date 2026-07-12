"""Tests for Markdown report renderer."""

from datetime import datetime, timezone

from infermatrix.reports.markdown_renderer import render_markdown_report
from infermatrix.reports.models import ReportCheck, RunReport


def _passing_tool_call_report() -> RunReport:
    """构造一份固定的通过报告。

    使用固定 run_id 和 created_at，
    避免测试因为 UUID 和当前时间而不稳定。
    """

    return RunReport(
        run_id="run_test_tool_call_001",
        created_at=datetime(
            2026,
            7,
            11,
            12,
            30,
            tzinfo=timezone.utc,
        ),
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
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "tool_calls",
                }
            ],
        },
        parsed_output={
            "tool_name": "get_weather",
            "arguments": {
                "city": "深圳",
                "unit": "celsius",
            },
        },
        checks=[
            ReportCheck(
                name="tool_name",
                status="pass",
                reason="Tool name matches expected value.",
                details={
                    "expected": "get_weather",
                    "actual": "get_weather",
                },
            ),
            ReportCheck(
                name="tool_arguments_schema",
                status="pass",
                reason="Tool arguments match the parameters Schema.",
            ),
        ],
        verdict="pass",
        failure_reasons=[],
        reproduction_command=(
            "infermatrix run examples/tool_call_weather.yaml"
        ),
    )


def test_render_markdown_report_contains_main_sections() -> None:
    """Markdown 报告应该包含所有核心区块。"""

    report = _passing_tool_call_report()

    markdown = render_markdown_report(report)

    assert markdown.startswith("# InferMatrix Run Report\n")

    assert "## Summary" in markdown
    assert "## Case" in markdown
    assert "## Features" in markdown
    assert "## Checks" in markdown
    assert "## Failure Reasons" in markdown
    assert "## Parsed Output" in markdown
    assert "## Raw Output" in markdown
    assert "## Reproduction" in markdown


def test_render_markdown_report_contains_run_metadata() -> None:
    """报告应该包含运行身份和 Case 信息。"""

    markdown = render_markdown_report(
        _passing_tool_call_report()
    )

    assert "`run_test_tool_call_001`" in markdown
    assert "`tool_call_weather_001`" in markdown
    assert "`examples/tool_call_weather.yaml`" in markdown
    assert "`mock`" in markdown
    assert "`mock-model`" in markdown
    assert "**PASS**" in markdown


def test_render_markdown_report_contains_checks() -> None:
    """报告应该展示每一个 Analyzer Check。"""

    markdown = render_markdown_report(
        _passing_tool_call_report()
    )

    assert "### `tool_name` — PASS" in markdown
    assert "Tool name matches expected value." in markdown

    assert "### `tool_arguments_schema` — PASS" in markdown
    assert (
        "Tool arguments match the parameters Schema."
        in markdown
    )


def test_render_markdown_report_keeps_unicode_json() -> None:
    """JSON 输出中的中文不应该转义成 Unicode 编码。"""

    markdown = render_markdown_report(
        _passing_tool_call_report()
    )

    assert '"city": "深圳"' in markdown
    assert "\\u6df1\\u5733" not in markdown


def test_render_markdown_report_contains_reproduction_command() -> None:
    """报告应该包含可以复制执行的复现命令。"""

    markdown = render_markdown_report(
        _passing_tool_call_report()
    )

    assert "```bash" in markdown
    assert (
        "infermatrix run examples/tool_call_weather.yaml"
        in markdown
    )


def test_render_markdown_report_lists_failure_reasons() -> None:
    """失败报告应该列出每个 failure reason。"""

    passing_report = _passing_tool_call_report()

    failing_report = passing_report.model_copy(
        update={
            "checks": [
                ReportCheck(
                    name="tool_name",
                    status="fail",
                    reason=(
                        "Expected get_weather, "
                        "but received get_time."
                    ),
                )
            ],
            "verdict": "fail",
            "failure_reasons": [
                "Expected get_weather, but received get_time."
            ],
        }
    )

    markdown = render_markdown_report(failing_report)

    assert "**FAIL**" in markdown
    assert "### `tool_name` — FAIL" in markdown
    assert (
        "- Expected get_weather, but received get_time."
        in markdown
    )


def test_render_markdown_report_handles_no_checks() -> None:
    """没有 Analyzer Check 时仍然应该生成合法报告。"""

    report = _passing_tool_call_report().model_copy(
        update={
            "checks": [],
        }
    )

    markdown = render_markdown_report(report)

    assert "## Checks" in markdown
    assert "No analyzer checks were recorded." in markdown


def test_render_markdown_report_ends_with_newline() -> None:
    """生成的 Markdown 应该以换行符结束。"""

    markdown = render_markdown_report(
        _passing_tool_call_report()
    )

    assert markdown.endswith("\n")


def test_renderer_handles_missing_raw_output() -> None:
    """Runner 失败报告允许没有 Raw Output。"""

    report = _passing_tool_call_report().model_copy(
        update={
            "response_type": "execution_error",
            "raw_output": None,
            "verdict": "fail",
            "failure_reasons": [
                "Unsupported backend."
            ],
        }
    )

    markdown = render_markdown_report(report)

    assert "## Raw Output" in markdown
    assert (
        "No raw output was recorded."
        in markdown
    )