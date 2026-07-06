"""Command-line interface for InferMatrix.

这个模块定义 infermatrix 命令。

阶段 A：CLI 只负责读取 YAML case。
阶段 B：CLI 会把 mock backend 接进来，让 case 可以被真正 run 一次。
阶段 C：CLI 不再手动访问 response["choices"][0]["message"]["content"]，而是调用 response parser 解析模型响应。
"""

from pathlib import Path

import typer
from packaging.metadata import parse_email
from rich.console import Console

from infermatrix.cases import load_case
from infermatrix.clients.mock_openai import MockOpenAIClient
from infermatrix.parsers.chat_completion import (
    ChatCompletionParseError,
    parse_chat_completion_response,
)

# Typer app object.
# pyproject.toml points the `infermatrix` command to this object.
app = typer.Typer(
    help = "InferMatrix: Agentic LLM Systems behavior analysis framework.",
    no_args_is_help=True,
)

# Rich console gives us nicer terminal output.
console = Console()

@app.callback()
def main() -> None:
    """InferMatrix command line interface."""
    # This function intentionally does nothing.
    # Its job is to make `infermatrix` behave like a command group.
    #
    # Without this callback, Typer may treat a single-command app as a
    # single command, which changes how command-line arguments are parsed.
    pass

@app.command()
def run(case_file: Path) -> None:
    """
    Load and display an InferMatrix case.

    Args:
        case_file: Path to a YAML case file.

    Example:
        infermatrix run examples/basic_chat.yaml
    """

    # Load and validate the YAML case.
    case = load_case(case_file)

    # Print basic information.
    console.print("[bold green]InferMatrix case loaded successfully[/bold green]")
    console.print(f"Case ID: {case.case_id}")
    console.print(f"Backend: {case.backend}")
    console.print(f"Model: {case.model}")
    console.print(f"Streaming: {case.features.streaming}")
    console.print(f"Tool calling: {case.features.tool_calling}")
    console.print(f"Structured output: {case.features.structured_output}")
    console.print(f"Messages: {len(case.messages)}")

    if case.backend != "mock":
        console.print(f"[bold red]Unsupported backnd in Phase B:[/bold redd] {case.backend}")
        raise typer.Exit(code = 1)
    
    client = MockOpenAIClient()

    try:
        response = client.run_case(case)
        parsed = parse_chat_completion_response(response)
    except NotImplementedError as error:
        console.print(f"[bold red]Unsupported case feature:[/bold red] {error}")
        raise typer.Exit(code = 1) from error
    except ChatCompletionParseError as error:
        console.print(f"[bold red]Failed to parse response:[/bold red] {error}")
        raise typer.Exit(code = 1) from error
    
    console.print("[bold blue]Parsed assistant message[/bold blue]")
    console.print(f"Role: {parsed.role}")
    console.print(f"Finish reason: {parsed.finish_reason}")
    console.print(f"Content: {parsed.content}")