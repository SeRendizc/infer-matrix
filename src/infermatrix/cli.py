"""Command-line interface for InferMatrix.

阶段 B-2 之后，CLI 不再自己直接创建 client。
CLI 的职责是：
- 读取用户命令
- 调用 runner
- 打印人类可读的最小执行结果

真正的执行流程交给 runner。
"""

from pathlib import Path
from typing import Any

import typer
from pydantic import BaseModel
from rich.console import Console

from infermatrix.cases import InferCase, load_case
from infermatrix.reports import (
    ReportAssemblyError,
    ReportWriteError,
    RunReport,
    assemble_run_report,
    write_jsonl_report,
    write_markdown_report,
    write_report_bundle,
)
from infermatrix.runner import (
    RunResult,
)
from infermatrix.pipeline import run_case_pipeline


app = typer.Typer(
    help="InferMatrix: Agentic LLM Systems behavior analysis framework.",
    no_args_is_help=True,
)

console = Console()


@app.callback()
def main() -> None:
    """InferMatrix command line interface."""
    pass


def _write_run_reports(
    *,
    case: InferCase,
    case_file: Path,
    run_result: RunResult,
    parsed_output: BaseModel | dict[str, Any] | None,
    check_results: list[BaseModel],
    report_dir: Path,
) -> RunReport:
    """组装并写入一次 Case 执行报告。

    输出两种格式：

    - runs/<run_id>.md
    - runs/runs.jsonl

    CLI 只调用这个统一函数，不分别处理报告内部细节。
    """

    try:
        report = assemble_run_report(
            case=case,
            case_file=case_file,
            run_result=run_result,
            parsed_output=parsed_output,
            check_results=check_results,
        )

        markdown_path = write_markdown_report(
            report,
            output_dir=report_dir,
        )

        jsonl_path = write_jsonl_report(
            report,
            output_file=report_dir / "runs.jsonl",
        )
    except (
        ReportAssemblyError,
        ReportWriteError,
    ) as error:
        console.print(
            "[bold red]Failed to generate run report:"
            f"[/bold red] {error}"
        )
        raise typer.Exit(code=1) from error

    console.print("[bold blue]Run report[/bold blue]")
    console.print(f"Run ID: {report.run_id}")
    console.print(f"Verdict: {report.verdict}")
    console.print(f"Markdown: {markdown_path}")
    console.print(f"JSONL: {jsonl_path}")

    return report


@app.command()
def run(
    case_file: Path,
    report_dir: Path = typer.Option(
        Path("runs"),
        "--report-dir",
        help="报告输出目录。",
    ),
) -> None:
    """运行一个 InferMatrix Case 并生成报告。"""

    try:
        case = load_case(case_file)
    except (
        FileNotFoundError,
        ValueError,
    ) as error:
        console.print(
            "[bold red]Failed to load case:"
            f"[/bold red] {error}"
        )
        raise typer.Exit(code=1) from error

    console.print(
        "[bold green]InferMatrix case loaded[/bold green]"
    )
    console.print(f"Case ID: {case.case_id}")
    console.print(f"Backend: {case.backend.provider}")
    console.print(f"Protocol: {case.protocol.type}")
    console.print(f"Model: {case.model}")

    pipeline_result = run_case_pipeline(
        case=case,
        case_file=case_file,
    )

    try:
        markdown_path, jsonl_path = (
            write_report_bundle(
                pipeline_result.report,
                output_dir=report_dir,
            )
        )
    except ReportWriteError as error:
        console.print(
            "[bold red]Failed to write reports:"
            f"[/bold red] {error}"
        )
        raise typer.Exit(code=1) from error

    report = pipeline_result.report

    console.print("[bold blue]Run result[/bold blue]")
    console.print(f"Run ID: {report.run_id}")
    console.print(f"Verdict: {report.verdict}")
    console.print(
        f"Response type: {report.response_type}"
    )

    if report.checks:
        console.print("[bold blue]Checks[/bold blue]")

        for check in report.checks:
            console.print(
                f"{check.name}: "
                f"{check.status} — {check.reason}"
            )

    console.print(
        f"Markdown report: {markdown_path}"
    )
    console.print(
        f"JSONL report: {jsonl_path}"
    )

    if pipeline_result.exit_code != 0:
        raise typer.Exit(
            code=pipeline_result.exit_code
        )