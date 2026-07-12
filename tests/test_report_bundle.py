"""Tests for combined report writing."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from infermatrix.reports.bundle_writer import (
    write_report_bundle,
)
from infermatrix.reports.errors import (
    ReportWriteError,
)
from infermatrix.reports.models import RunReport


def _report() -> RunReport:
    return RunReport(
        run_id="run_bundle_test_001",
        created_at=datetime(
            2026,
            7,
            13,
            tzinfo=timezone.utc,
        ),
        case_id="basic_chat_001",
        case_file="examples/basic_chat.yaml",
        backend="mock",
        model="mock-model",
        features={
            "streaming": False,
            "tool_calling": False,
            "structured_output": False,
        },
        response_type="chat_completion",
        raw_output={
            "object": "chat.completion",
        },
        parsed_output={
            "content": "InferMatrix",
        },
        checks=[],
        verdict="pass",
        failure_reasons=[],
        reproduction_command=(
            'infermatrix run "examples/basic_chat.yaml"'
        ),
    )


def test_write_report_bundle_creates_both_formats(
    tmp_path: Path,
) -> None:
    """Bundle Writer 应生成 Markdown 和 JSONL。"""

    markdown_path, jsonl_path = write_report_bundle(
        _report(),
        output_dir=tmp_path / "runs",
    )

    assert markdown_path.exists()
    assert jsonl_path.exists()


def test_bundle_removes_markdown_when_jsonl_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """JSONL 写入失败时应尽力清理新 Markdown。"""

    def fail_jsonl(*args, **kwargs):
        raise ReportWriteError(
            "Simulated JSONL failure."
        )

    monkeypatch.setattr(
        "infermatrix.reports.bundle_writer."
        "write_jsonl_report",
        fail_jsonl,
    )

    output_dir = tmp_path / "runs"

    with pytest.raises(
        ReportWriteError,
        match="Simulated",
    ):
        write_report_bundle(
            _report(),
            output_dir=output_dir,
        )

    assert not (
        output_dir / "run_bundle_test_001.md"
    ).exists()