"""Tests for InferMatrix JSONL report writer."""

import json
from datetime import datetime, timezone
from pathlib import Path

from infermatrix.reports.jsonl_writer import write_jsonl_report
from infermatrix.reports.models import ReportCheck, RunReport


def _example_report(
    run_id: str = "run_jsonl_test_001",
    city: str = "深圳",
) -> RunReport:
    """构造一份固定 JSONL 测试报告。"""

    return RunReport(
        run_id=run_id,
        created_at=datetime(
            2026,
            7,
            13,
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
                "city": city,
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
            "infermatrix run examples/tool_call_weather.yaml"
        ),
    )


def test_write_jsonl_report_creates_file(
    tmp_path: Path,
) -> None:
    """JSONL Writer 应创建目标文件。"""

    report = _example_report()
    output_file = tmp_path / "runs" / "runs.jsonl"

    result_path = write_jsonl_report(
        report,
        output_file=output_file,
    )

    assert result_path == output_file
    assert result_path.exists()
    assert result_path.is_file()


def test_jsonl_file_contains_one_valid_json_object(
    tmp_path: Path,
) -> None:
    """写入一份报告后，文件应包含一条合法 JSON 记录。"""

    report = _example_report()
    output_file = tmp_path / "runs.jsonl"

    write_jsonl_report(
        report,
        output_file=output_file,
    )

    lines = output_file.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(lines) == 1

    record = json.loads(lines[0])

    assert record["run_id"] == "run_jsonl_test_001"
    assert record["case_id"] == "tool_call_weather_001"
    assert record["backend"] == "mock"
    assert record["model"] == "mock-model"
    assert record["verdict"] == "pass"


def test_write_jsonl_report_appends_multiple_records(
    tmp_path: Path,
) -> None:
    """多次写入应该追加，而不是覆盖旧记录。"""

    output_file = tmp_path / "runs.jsonl"

    first_report = _example_report(
        run_id="run_jsonl_test_001",
        city="深圳",
    )
    second_report = _example_report(
        run_id="run_jsonl_test_002",
        city="武汉",
    )

    write_jsonl_report(
        first_report,
        output_file=output_file,
    )
    write_jsonl_report(
        second_report,
        output_file=output_file,
    )

    lines = output_file.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(lines) == 2

    first_record = json.loads(lines[0])
    second_record = json.loads(lines[1])

    assert first_record["run_id"] == "run_jsonl_test_001"
    assert second_record["run_id"] == "run_jsonl_test_002"

    assert (
        first_record["parsed_output"]["arguments"]["city"]
        == "深圳"
    )
    assert (
        second_record["parsed_output"]["arguments"]["city"]
        == "武汉"
    )


def test_write_jsonl_report_preserves_unicode(
    tmp_path: Path,
) -> None:
    """JSONL 中的中文应该保持原文。"""

    output_file = tmp_path / "runs.jsonl"

    write_jsonl_report(
        _example_report(),
        output_file=output_file,
    )

    content = output_file.read_text(encoding="utf-8")

    assert "深圳" in content
    assert "\\u6df1\\u5733" not in content


def test_write_jsonl_report_serializes_datetime(
    tmp_path: Path,
) -> None:
    """created_at 应被转换为 JSON 字符串。"""

    output_file = tmp_path / "runs.jsonl"

    write_jsonl_report(
        _example_report(),
        output_file=output_file,
    )

    line = output_file.read_text(
        encoding="utf-8"
    ).splitlines()[0]

    record = json.loads(line)

    assert isinstance(record["created_at"], str)
    assert record["created_at"].startswith(
        "2026-07-13T12:30:00"
    )


def test_write_jsonl_report_creates_parent_directories(
    tmp_path: Path,
) -> None:
    """多层父目录不存在时应自动创建。"""

    output_file = (
        tmp_path
        / "artifacts"
        / "reports"
        / "runs.jsonl"
    )

    result_path = write_jsonl_report(
        _example_report(),
        output_file=output_file,
    )

    assert result_path.exists()
    assert result_path.parent.exists()


def test_json_string_newline_does_not_break_jsonl_record(
    tmp_path: Path,
) -> None:
    """字段中的换行符不能把一条记录拆成多行。"""

    output_file = tmp_path / "runs.jsonl"

    report = _example_report().model_copy(
        update={
            "checks": [
                ReportCheck(
                    name="multiline_check",
                    status="fail",
                    reason="First line.\nSecond line.",
                )
            ],
            "verdict": "fail",
            "failure_reasons": [
                "First line.\nSecond line."
            ],
        }
    )

    write_jsonl_report(
        report,
        output_file=output_file,
    )

    physical_lines = output_file.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(physical_lines) == 1

    record = json.loads(physical_lines[0])

    assert record["checks"][0]["reason"] == (
        "First line.\nSecond line."
    )


def test_write_jsonl_report_returns_path(
    tmp_path: Path,
) -> None:
    """Writer 应返回最终输出路径。"""

    output_file = tmp_path / "runs.jsonl"

    result = write_jsonl_report(
        _example_report(),
        output_file=output_file,
    )

    assert isinstance(result, Path)
    assert result == output_file