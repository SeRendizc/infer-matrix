"""End-to-end tests for CLI report generation."""

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from agent_eval_lab.cli import app


PROJECT_ROOT = Path(__file__).resolve().parents[1]

runner = CliRunner()


def test_cli_generates_reports_for_basic_chat(
    tmp_path: Path,
) -> None:
    """普通 Chat Case 应生成 Markdown 和 JSONL。"""

    case_file = (
        PROJECT_ROOT
        / "examples"
        / "basic_chat.yaml"
    )
    report_dir = tmp_path / "runs"

    result = runner.invoke(
        app,
        [
            "run",
            str(case_file),
            "--report-dir",
            str(report_dir),
        ],
    )

    assert result.exit_code == 0, result.output

    markdown_files = list(
        report_dir.glob("run_*.md")
    )

    assert len(markdown_files) == 1

    markdown = markdown_files[0].read_text(
        encoding="utf-8"
    )

    assert "# Agent Eval Lab Run Report" in markdown
    assert "basic_chat_001" in markdown
    assert "**PASS**" in markdown

    jsonl_file = report_dir / "runs.jsonl"

    assert jsonl_file.exists()

    records = [
        json.loads(line)
        for line in jsonl_file.read_text(
            encoding="utf-8"
        ).splitlines()
    ]

    assert len(records) == 1
    assert records[0]["case_id"] == "basic_chat_001"
    assert records[0]["verdict"] == "pass"


def test_cli_generates_tool_call_checks(
    tmp_path: Path,
) -> None:
    """Tool Call Case 报告应包含两个检查结果。"""

    case_file = (
        PROJECT_ROOT
        / "examples"
        / "tool_call_weather.yaml"
    )
    report_dir = tmp_path / "runs"

    result = runner.invoke(
        app,
        [
            "run",
            str(case_file),
            "--report-dir",
            str(report_dir),
        ],
    )

    assert result.exit_code == 0, result.output

    jsonl_file = report_dir / "runs.jsonl"

    record = json.loads(
        jsonl_file.read_text(
            encoding="utf-8"
        ).splitlines()[0]
    )

    check_names = {
        check["name"]
        for check in record["checks"]
    }

    assert check_names == {
        "tool_name",
        "tool_arguments_schema",
    }

    assert all(
        check["status"] == "pass"
        for check in record["checks"]
    )


def test_cli_writes_failure_report_before_exit(
    tmp_path: Path,
) -> None:
    """Analyzer 失败时 CLI 应先写报告，再返回退出码 1。"""

    source_case = (
        PROJECT_ROOT
        / "examples"
        / "tool_call_weather.yaml"
    )

    raw_case = yaml.safe_load(
        source_case.read_text(encoding="utf-8")
    )

    # 删除 required city 参数，使 Tool Arguments
    # Schema 检查稳定失败。
    raw_case["metadata"]["mock_tool_arguments"] = {
        "unit": "celsius",
    }

    broken_case = tmp_path / "broken_tool_call.yaml"

    broken_case.write_text(
        yaml.safe_dump(
            raw_case,
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    report_dir = tmp_path / "runs"

    result = runner.invoke(
        app,
        [
            "run",
            str(broken_case),
            "--report-dir",
            str(report_dir),
        ],
    )

    assert result.exit_code == 1

    # 即使 CLI 返回失败，报告仍然必须存在。
    markdown_files = list(
        report_dir.glob("run_*.md")
    )

    assert len(markdown_files) == 1

    jsonl_file = report_dir / "runs.jsonl"

    assert jsonl_file.exists()

    record = json.loads(
        jsonl_file.read_text(
            encoding="utf-8"
        ).splitlines()[0]
    )

    assert record["verdict"] == "fail"
    assert record["failure_reasons"]

    argument_check = next(
        check
        for check in record["checks"]
        if check["name"] == "tool_arguments_schema"
    )

    assert argument_check["status"] == "fail"
    assert "required" in argument_check["reason"]


def test_cli_generates_streaming_structured_report(
    tmp_path: Path,
) -> None:
    """Streaming Structured Output 应保留两层解析结果。"""

    case_file = (
        PROJECT_ROOT
        / "examples"
        / "streaming_json.yaml"
    )
    report_dir = tmp_path / "runs"

    result = runner.invoke(
        app,
        [
            "run",
            str(case_file),
            "--report-dir",
            str(report_dir),
        ],
    )

    assert result.exit_code == 0, result.output

    jsonl_file = report_dir / "runs.jsonl"

    record = json.loads(
        jsonl_file.read_text(
            encoding="utf-8"
        ).splitlines()[0]
    )

    assert record["verdict"] == "pass"

    assert "stream" in record["parsed_output"]
    assert (
        "structured_output"
        in record["parsed_output"]
    )

    assert (
        record["parsed_output"]
        ["structured_output"]
        ["data"]
        ["status"]
        == "ok"
    )

    assert record["checks"][0]["name"] == (
        "json_schema"
    )