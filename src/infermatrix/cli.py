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
)
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
        console.print(f"Streaming chunks: {len(chunks)}")

        merged_content = "".join(
            choice.get("delta", {}).get("content", "")
            for chunk in chunks
            for choice in chunk.get("choices", [])
        )

        if merged_content:
            console.print(f"Merged content preview: {merged_content}")

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