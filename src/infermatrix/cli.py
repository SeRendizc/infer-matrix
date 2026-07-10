"""Command-line interface for InferMatrix.

阶段 B-2 之后，CLI 不再自己直接创建 client。
CLI 的职责是：
- 读取用户命令
- 调用 runner
- 打印人类可读的最小执行结果

真正的执行流程交给 runner。
"""

from pathlib import Path

import typer
from rich.console import Console

from infermatrix.cases import load_case
from infermatrix.parsers import (
    parse_chat_completion_response,
    ChatCompletionParseError,
    ToolCallParseError,
    parse_tool_call_response,
    StreamParseError,
    parse_streaming_chunks,
    StructuredOutputParseError,
    parse_structured_output_text,
)
from infermatrix.analyzers.schema_checker import check_json_schema
from infermatrix.runner import UnsupportedBackendError, run_case


app = typer.Typer(
    help="InferMatrix: Agentic LLM Systems behavior analysis framework.",
    no_args_is_help=True,
)

console = Console()


@app.callback()
def main() -> None:
    """InferMatrix command line interface."""
    pass


@app.command()
def run(case_file: Path) -> None:
    """Load one case and run it through InferMatrix runner.

    Args:
        case_file: Path to a YAML case file.
    """

    case = load_case(case_file)

    console.print("[bold green]InferMatrix case loaded successfully[/bold green]")
    console.print(f"Case ID: {case.case_id}")
    console.print(f"Backend: {case.backend}")
    console.print(f"Model: {case.model}")
    console.print(f"Streaming: {case.features.streaming}")
    console.print(f"Tool calling: {case.features.tool_calling}")
    console.print(f"Structured output: {case.features.structured_output}")
    console.print(f"Messages: {len(case.messages)}")
    console.print(f"Tools: {len(case.tools)}")

    try:
        result = run_case(case)
    except UnsupportedBackendError as error:
        console.print(f"[bold red]Unsupported backend:[/bold red] {error}")
        raise typer.Exit(code=1) from error
    except NotImplementedError as error:
        console.print(f"[bold red]Unsupported case feature:[/bold red] {error}")
        raise typer.Exit(code=1) from error

    console.print("[bold blue]Run result[/bold blue]")
    console.print(f"Verdict: {result.verdict}")
    console.print(f"Response type: {result.response_type}")

    if result.response_type == "chat_completion_chunks":
        chunks = result.chunks or []

        try:
            parsed = parse_streaming_chunks(chunks)
        except StreamParseError as error:
            console.print(
                f"[bold red]Failed to parse streaming chunks:[/bold red] {error}"
            )
            raise typer.Exit(code=1) from error

        console.print("[bold blue]Parsed streaming message[/bold blue]")
        console.print(f"Role: {parsed.role}")
        console.print(f"Finish reason: {parsed.finish_reason}")
        console.print(f"Content chunks: {len(parsed.content_chunks)}")
        console.print(f"Merged content: {parsed.merged_content}")

        if case.features.structured_output:
            try:
                structured_output = parse_structured_output_text(parsed.merged_content)
            except StructuredOutputParseError as error:
                console.print(f"[bold red]Failed to parse structured output:[/bold red] {error}")
                raise typer.Exit(code=1) from error

            console.print("[bold blue]Parsed structured output[/bold blue]")
            console.print(f"Keys: {list(structured_output.data.keys())}")
            console.print(f"Data: {structured_output.data}")

            schema_result = check_json_schema(case, structured_output)

            console.print("[bold blue]Schema check result[/bold blue]")
            console.print(f"Status: {schema_result.status}")
            console.print(f"Reason: {schema_result.reason}")

            if schema_result.failed:
                raise typer.Exit(code=1)

        return

    if result.response is None:
        console.print("[bold red]No response returned.[/bold red]")
        raise typer.Exit(code=1)

    if case.features.tool_calling:
        try:
            parsed = parse_tool_call_response(result.response)
        except ToolCallParseError as error:
            console.print(f"[bold red]Failed to parse tool call response:[/bold red] {error}")
            raise typer.Exit(code=1) from error

        console.print("[bold blue]Parsed tool call response[/bold blue]")
        console.print(f"Role: {parsed.role}")
        console.print(f"Finish reason: {parsed.finish_reason}")
        console.print(f"Tool calls: {len(parsed.tool_calls)}")

        for index, tool_call in enumerate(parsed.tool_calls):
            console.print(f"Tool call #{index}")
            console.print(f"  ID: {tool_call.id}")
            console.print(f"  Type: {tool_call.type}")
            console.print(f"  Name: {tool_call.name}")
            console.print(f"  Raw arguments: {tool_call.raw_arguments}")
            console.print(f"  Parsed arguments: {tool_call.arguments}")

        return

    try:
        parsed = parse_chat_completion_response(result.response)
    except ChatCompletionParseError as error:
        console.print(f"[bold red]Failed to parse response:[/bold red] {error}")
        raise typer.Exit(code=1) from error

    console.print("[bold blue]Parsed assistant message[/bold blue]")
    console.print(f"Role: {parsed.role}")
    console.print(f"Finish reason: {parsed.finish_reason}")
    console.print(f"Content: {parsed.content}")

    if case.features.structured_output:
        try:
            structured_output = parse_structured_output_text(parsed.content)
        except StructuredOutputParseError as error:
            console.print(f"[bold red]Failed to parse structured output:[/bold red] {error}")
            raise typer.Exit(code=1) from error

        console.print("[bold blue]Parsed structured output[/bold blue]")
        console.print(f"Keys: {list(structured_output.data.keys())}")
        console.print(f"Data: {structured_output.data}")

        schema_result = check_json_schema(case, structured_output)

        console.print("[bold blue]Schema check result[/bold blue]")
        console.print(f"Status: {schema_result.status}")
        console.print(f"Reason: {schema_result.reason}")

        if schema_result.failed:
            raise typer.Exit(code=1)