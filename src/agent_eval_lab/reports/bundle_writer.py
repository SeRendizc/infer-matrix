"""Write all report formats for one Agent Eval Lab run."""

from __future__ import annotations

from pathlib import Path

from agent_eval_lab.reports.errors import (
    ReportWriteError,
)
from agent_eval_lab.reports.jsonl_writer import (
    write_jsonl_report,
)
from agent_eval_lab.reports.markdown_writer import (
    write_markdown_report,
)
from agent_eval_lab.reports.models import RunReport


def write_report_bundle(
    report: RunReport,
    output_dir: str | Path = "runs",
) -> tuple[Path, Path]:
    """同时写入 Markdown 和 JSONL 报告。

    Returns:
        tuple[Path, Path]:
            Markdown 路径和 JSONL 路径。

    如果 Markdown 成功但 JSONL 失败，
    会尽力删除刚刚生成的 Markdown，
    避免留下明显不完整的一组报告。
    """

    directory = Path(output_dir)

    markdown_path = write_markdown_report(
        report,
        output_dir=directory,
    )

    try:
        jsonl_path = write_jsonl_report(
            report,
            output_file=directory / "runs.jsonl",
        )
    except ReportWriteError:
        try:
            markdown_path.unlink(missing_ok=True)
        except OSError:
            # 原始 JSONL 错误更重要，不覆盖它。
            pass

        raise

    return markdown_path, jsonl_path