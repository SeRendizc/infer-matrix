"""
Command-line interface for InferMatrix.

This module defines the `infermatrix` command.

For Stage A, the CLI only loads a YAML case and prints its basic information.
Later, the CLI will run cases against mock or real OpenAI-compatible backends.
"""

from pathlib import Path

import typer
from rich.console import Console

from infermatrix.cases import load_case

# Typer app object.
# pyproject.toml points the `infermatrix` command to this object.
app = typer.Typer(
    help = "InferMatrix: Agentic LLM Systems behavior analysis framework."
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

    if case.expected.contains_text:
        console.print(f"Expected text: {case.expected.contains_text}")