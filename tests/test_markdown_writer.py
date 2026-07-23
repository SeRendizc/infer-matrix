"""Tests for Markdown report file writer."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent_eval_lab.reports.markdown_renderer import render_markdown_report
from agent_eval_lab.reports.markdown_writer import (
    ReportWriteError,
    write_markdown_report,
)
from agent_eval_lab.reports.models import ReportCheck, RunReport


def _example_report(
    run_id: str = "run_test_writer_001",
) -> RunReport:
    """构造一份固定的测试报告。

    测试中固定 run_id 和 created_at，
    避免 UUID 与当前时间导致测试结果不稳定。
    """

    return RunReport(
        run_id=run_id,
        created_at=datetime(
            2026,
            7,
            12,
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
            ),
            ReportCheck(
                name="tool_arguments_schema",
                status="pass",
                reason=(
                    "Tool arguments match the parameters Schema."
                ),
            ),
        ],
        verdict="pass",
        failure_reasons=[],
        reproduction_command=(
            "agent-eval run examples/tool_call_weather.yaml"
        ),
    )


def test_write_markdown_report_creates_file(
    tmp_path: Path,
) -> None:
    """Writer 应该创建正确命名的 Markdown 文件。"""

    report = _example_report()
    output_dir = tmp_path / "runs"

    report_path = write_markdown_report(
        report,
        output_dir=output_dir,
    )

    assert report_path == (
        output_dir / "run_test_writer_001.md"
    )
    assert report_path.exists()
    assert report_path.is_file()


def test_written_content_matches_renderer(
    tmp_path: Path,
) -> None:
    """写入文件的内容应该与 renderer 输出完全一致。"""

    report = _example_report()

    report_path = write_markdown_report(
        report,
        output_dir=tmp_path / "runs",
    )

    written_content = report_path.read_text(
        encoding="utf-8"
    )
    expected_content = render_markdown_report(report)

    assert written_content == expected_content


def test_write_markdown_report_creates_nested_directories(
    tmp_path: Path,
) -> None:
    """多层输出目录不存在时，Writer 应该自动创建。"""

    report = _example_report()
    output_dir = (
        tmp_path
        / "artifacts"
        / "reports"
        / "markdown"
    )

    report_path = write_markdown_report(
        report,
        output_dir=output_dir,
    )

    assert output_dir.exists()
    assert report_path.exists()


def test_write_markdown_report_preserves_unicode(
    tmp_path: Path,
) -> None:
    """报告中的中文应该以 UTF-8 正确保存。"""

    report = _example_report()

    report_path = write_markdown_report(
        report,
        output_dir=tmp_path / "runs",
    )

    content = report_path.read_text(encoding="utf-8")

    assert '"city": "深圳"' in content
    assert "\\u6df1\\u5733" not in content


def test_write_markdown_report_rejects_existing_file(
    tmp_path: Path,
) -> None:
    """默认情况下，不应该覆盖同名报告。"""

    report = _example_report()
    output_dir = tmp_path / "runs"

    first_path = write_markdown_report(
        report,
        output_dir=output_dir,
    )

    assert first_path.exists()

    with pytest.raises(
        ReportWriteError,
        match="already exists",
    ):
        write_markdown_report(
            report,
            output_dir=output_dir,
        )


def test_write_markdown_report_can_overwrite_when_enabled(
    tmp_path: Path,
) -> None:
    """overwrite=True 时，应该允许替换同名报告。"""

    report = _example_report()
    output_dir = tmp_path / "runs"

    report_path = write_markdown_report(
        report,
        output_dir=output_dir,
    )

    updated_report = report.model_copy(
        update={
            "parsed_output": {
                "tool_name": "get_weather",
                "arguments": {
                    "city": "武汉",
                },
            }
        }
    )

    overwritten_path = write_markdown_report(
        updated_report,
        output_dir=output_dir,
        overwrite=True,
    )

    assert overwritten_path == report_path

    content = overwritten_path.read_text(
        encoding="utf-8"
    )

    assert '"city": "武汉"' in content
    assert '"city": "深圳"' not in content


def test_write_markdown_report_rejects_unsafe_run_id(
    tmp_path: Path,
) -> None:
    """run_id 中含路径字符时，Writer 应该拒绝。"""

    report = _example_report().model_copy(
        update={
            "run_id": "../outside",
        }
    )

    with pytest.raises(
        ReportWriteError,
        match="cannot be used safely",
    ):
        write_markdown_report(
            report,
            output_dir=tmp_path / "runs",
        )


def test_write_markdown_report_returns_path(
    tmp_path: Path,
) -> None:
    """Writer 应返回 Path，供 CLI 或其他模块继续使用。"""

    report = _example_report()

    report_path = write_markdown_report(
        report,
        output_dir=tmp_path / "runs",
    )

    assert isinstance(report_path, Path)