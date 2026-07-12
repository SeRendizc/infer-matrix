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

from infermatrix.analyzers import (
    check_json_schema,
    check_tool_call,
)
from infermatrix.analyzers.tool_call_checker import (
    ToolCallCheckError,
)
from infermatrix.cases import InferCase, load_case
from infermatrix.parsers import (
    ChatCompletionParseError,
    StreamParseError,
    StructuredOutputParseError,
    ToolCallParseError,
    parse_chat_completion_response,
    parse_streaming_chunks,
    parse_structured_output_text,
    parse_tool_call_response,
)
from infermatrix.reports import (
    ReportAssemblyError,
    ReportWriteError,
    RunReport,
    assemble_run_report,
    write_jsonl_report,
    write_markdown_report,
)
from infermatrix.runner import (
    RunResult,
    UnsupportedBackendError,
    run_case,
)


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
        help="Directory used to store Markdown and JSONL reports.",
    ),
) -> None:
    """运行一个 InferMatrix Case，并生成可复现报告。"""

    case = load_case(case_file)

    console.print(
        "[bold green]InferMatrix case loaded successfully[/bold green]"
    )
    console.print(f"Case ID: {case.case_id}")
    console.print(f"Backend: {case.backend}")
    console.print(f"Model: {case.model}")
    console.print(f"Streaming: {case.features.streaming}")
    console.print(
        f"Tool calling: {case.features.tool_calling}"
    )
    console.print(
        f"Structured output: "
        f"{case.features.structured_output}"
    )
    console.print(f"Messages: {len(case.messages)}")
    console.print(f"Tools: {len(case.tools)}")

    try:
        run_result = run_case(case)
    except UnsupportedBackendError as error:
        console.print(
            f"[bold red]Unsupported backend:[/bold red] {error}"
        )
        raise typer.Exit(code=1) from error
    except NotImplementedError as error:
        console.print(
            "[bold red]Unsupported case feature:"
            f"[/bold red] {error}"
        )
        raise typer.Exit(code=1) from error

    console.print("[bold blue]Run result[/bold blue]")
    console.print(f"Verdict: {run_result.verdict}")
    console.print(
        f"Response type: {run_result.response_type}"
    )

    # 这些变量在三个分支中分别赋值，
    # 最后统一交给报告组装器。
    parsed_output: BaseModel | dict[str, Any] | None = None
    check_results: list[BaseModel] = []

    # 不在 Analyzer 失败时立即退出。
    # 先记录退出码，写完报告后再退出。
    exit_code = 0

    # ---------------------------------------------------------
    # 1. Streaming Response
    # ---------------------------------------------------------
    if run_result.response_type == "chat_completion_chunks":
        chunks = run_result.chunks

        if chunks is None:
            console.print(
                "[bold red]No streaming chunks returned."
                "[/bold red]"
            )
            raise typer.Exit(code=1)

        try:
            parsed_stream = parse_streaming_chunks(chunks)
        except StreamParseError as error:
            console.print(
                "[bold red]Failed to parse streaming chunks:"
                f"[/bold red] {error}"
            )
            raise typer.Exit(code=1) from error

        console.print(
            "[bold blue]Parsed streaming message[/bold blue]"
        )
        console.print(f"Role: {parsed_stream.role}")
        console.print(
            f"Finish reason: {parsed_stream.finish_reason}"
        )
        console.print(
            f"Content chunks: "
            f"{len(parsed_stream.content_chunks)}"
        )
        console.print(
            f"Merged content: {parsed_stream.merged_content}"
        )

        # 普通 Streaming Case 只记录 Stream Parser 输出。
        parsed_output = parsed_stream

        if case.features.structured_output:
            try:
                structured_output = (
                    parse_structured_output_text(
                        parsed_stream.merged_content
                    )
                )
            except StructuredOutputParseError as error:
                console.print(
                    "[bold red]Failed to parse structured output:"
                    f"[/bold red] {error}"
                )
                raise typer.Exit(code=1) from error

            console.print(
                "[bold blue]Parsed structured output[/bold blue]"
            )
            console.print(
                f"Keys: {list(structured_output.data.keys())}"
            )
            console.print(f"Data: {structured_output.data}")

            schema_result = check_json_schema(
                case,
                structured_output,
            )

            check_results.append(schema_result)

            console.print(
                "[bold blue]Schema check result[/bold blue]"
            )
            console.print(
                f"Status: {schema_result.status}"
            )
            console.print(
                f"Reason: {schema_result.reason}"
            )

            # 同时保留 Streaming Parser 和
            # Structured Output Parser 的结果。
            parsed_output = {
                "stream": parsed_stream.model_dump(
                    mode="json"
                ),
                "structured_output": (
                    structured_output.model_dump(
                        mode="json"
                    )
                ),
            }

            if schema_result.failed:
                exit_code = 1

    # ---------------------------------------------------------
    # 2. Non-streaming Response
    # ---------------------------------------------------------
    else:
        response = run_result.response

        if response is None:
            console.print(
                "[bold red]No response returned.[/bold red]"
            )
            raise typer.Exit(code=1)

        # -----------------------------------------------------
        # 2A. Tool Calling
        # -----------------------------------------------------
        if case.features.tool_calling:
            try:
                parsed_tool_message = (
                    parse_tool_call_response(response)
                )
            except ToolCallParseError as error:
                console.print(
                    "[bold red]Failed to parse tool call response:"
                    f"[/bold red] {error}"
                )
                raise typer.Exit(code=1) from error

            console.print(
                "[bold blue]Parsed tool call message[/bold blue]"
            )
            console.print(
                f"Role: {parsed_tool_message.role}"
            )
            console.print(
                "Finish reason: "
                f"{parsed_tool_message.finish_reason}"
            )
            console.print(
                f"Tool calls: "
                f"{len(parsed_tool_message.tool_calls)}"
            )

            for index, tool_call in enumerate(
                parsed_tool_message.tool_calls
            ):
                console.print(f"Tool call #{index}")
                console.print(f"  ID: {tool_call.id}")
                console.print(f"  Type: {tool_call.type}")
                console.print(f"  Name: {tool_call.name}")
                console.print(
                    f"  Raw arguments: "
                    f"{tool_call.raw_arguments}"
                )
                console.print(
                    f"  Parsed arguments: "
                    f"{tool_call.arguments}"
                )

            try:
                tool_check_results = check_tool_call(
                    case=case,
                    parsed_message=parsed_tool_message,
                )
            except ToolCallCheckError as error:
                console.print(
                    "[bold red]Failed to check tool call:"
                    f"[/bold red] {error}"
                )
                raise typer.Exit(code=1) from error

            check_results.extend(tool_check_results)
            parsed_output = parsed_tool_message

            console.print(
                "[bold blue]Tool call checks[/bold blue]"
            )

            for check_result in tool_check_results:
                console.print(
                    f"Check: {check_result.name}"
                )
                console.print(
                    f"  Status: {check_result.status}"
                )
                console.print(
                    f"  Reason: {check_result.reason}"
                )

            if any(
                check_result.failed
                for check_result in tool_check_results
            ):
                exit_code = 1

        # -----------------------------------------------------
        # 2B. Normal Assistant Message
        # -----------------------------------------------------
        else:
            try:
                parsed_message = (
                    parse_chat_completion_response(
                        response
                    )
                )
            except ChatCompletionParseError as error:
                console.print(
                    "[bold red]Failed to parse response:"
                    f"[/bold red] {error}"
                )
                raise typer.Exit(code=1) from error

            console.print(
                "[bold blue]Parsed assistant message[/bold blue]"
            )
            console.print(f"Role: {parsed_message.role}")
            console.print(
                f"Finish reason: "
                f"{parsed_message.finish_reason}"
            )
            console.print(
                f"Content: {parsed_message.content}"
            )

            parsed_output = parsed_message

            # 支持未来的 non-streaming structured output。
            if case.features.structured_output:
                try:
                    structured_output = (
                        parse_structured_output_text(
                            parsed_message.content
                        )
                    )
                except StructuredOutputParseError as error:
                    console.print(
                        "[bold red]Failed to parse "
                        "structured output:"
                        f"[/bold red] {error}"
                    )
                    raise typer.Exit(code=1) from error

                schema_result = check_json_schema(
                    case,
                    structured_output,
                )

                check_results.append(schema_result)

                console.print(
                    "[bold blue]Schema check result"
                    "[/bold blue]"
                )
                console.print(
                    f"Status: {schema_result.status}"
                )
                console.print(
                    f"Reason: {schema_result.reason}"
                )

                parsed_output = {
                    "assistant_message": (
                        parsed_message.model_dump(
                            mode="json"
                        )
                    ),
                    "structured_output": (
                        structured_output.model_dump(
                            mode="json"
                        )
                    ),
                }

                if schema_result.failed:
                    exit_code = 1

    # ---------------------------------------------------------
    # 3. 统一生成报告
    # ---------------------------------------------------------
    report = _write_run_reports(
        case=case,
        case_file=case_file,
        run_result=run_result,
        parsed_output=parsed_output,
        check_results=check_results,
        report_dir=report_dir,
    )

    # 理论上 report.verdict 与 exit_code 应一致。
    # 再使用报告 Verdict 兜底，避免漏掉失败检查。
    if report.verdict == "fail":
        exit_code = 1

    if exit_code != 0:
        raise typer.Exit(code=exit_code)