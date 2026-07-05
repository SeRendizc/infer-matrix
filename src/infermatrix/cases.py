"""
Case definitions and case loading utilities.

This module defines what an InferMatrix case looks like.

At this stage, a case is only a YAML file that describes:
- which backend to use,
- which model to use,
- which features are enabled,
- what messages are sent,
- what behavior is expected.

Later stages will use this case object to actually run requests.
"""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

class Message(BaseModel):
    """
    A single chat message.

    This follows the common chat-completion message format.

    Example:
        role: user
        content: "Explain InferMatrix in one sentence."
    """

    model_config = ConfigDict(extra="forbid")

    # Literal means role can only be one of these four strings.
    # If YAML contains role: random, Pydantic will reject it.
    role: Literal["system", "user", "assistant", "tool"]

    # The text content of the message.
    content: str

class CaseFeatures(BaseModel):
    """
    Feature switches for one test case.

    These flags describe which LLM-serving / Agent features are enabled.

    In Stage A, we only store them.
    In later stages, they will change how requests are sent and parsed.
    """

    model_config = ConfigDict(extra="forbid")
    
    # Whether the response is streamed chunk by chunk.
    streaming: bool = False

    # Whether the model is allowed or expected to call tools.
    tool_calling: bool = False

    # Whether the response should follow a structured JSON schema.
    structured_output: bool = False

class CaseExpected(BaseModel):
    """
    Expected behavior for one test case.

    This is intentionally simple for Stage A.

    Later we will add more precise checks, such as:
    - tool argument JSON validity,
    - JSON Schema validation,
    - stream merge correctness,
    - backend behavior difference.
    """

    model_config = ConfigDict(extra="forbid")

    # For a simple chat case, we may expect the final output to contain some text.
    contains_text: str | None = None

    # Whether the final structured output should be valid under a JSON schema.
    json_schema_valid: bool | None = None

    # Expected tool name, if tool calling is enabled.
    tool_name: str | None = None

    # Whether tool call arguments should match the expected schema.
    arguments_schema_valid: bool | None = None

class InferCase(BaseModel):
    """
    The complete structure of an InferMatrix case.

    A YAML case file will be parsed into this Python object.
    """

    model_config = ConfigDict(extra="forbid")

    # Unique identifier of the case.
    # Field(min_length=1) means empty case_id is not allowed.
    case_id: str = Field(min_length = 1)

    # Which backend to use.
    # For now, only "mock" is used.
    backend: str = Field(default = "mock")

    # Which model to use.
    # For now, only "mock-model" is used.
    model: str = Field(default = "mock-model")

    # Feature switches.
    # If YAML does not provide features, use default values.
    features: CaseFeatures = Field(default_factory=CaseFeatures)

    # Chat messages.
    # This is required. A case without messages is not useful.
    messages: list[Message]

    # Expected behavior.
    # If YAML does not provide expected, use an empty expected object.
    expected: CaseExpected = Field(default_factory=CaseExpected)

    # Extra metadata.
    # This can store purpose, source issue, notes, tags, etc.
    metadata: dict[str, Any] = Field(default_factory=dict)

def load_case(path: str | Path) -> InferCase:

    """
    Load one InferMatrix case from a YAML file.

    Args:
        path: Path to a YAML case file.

    Returns:
        An InferCase object.

    Raises:
        FileNotFoundError: If the case file does not exist.
        ValueError: If the YAML file is empty.
        pydantic.ValidationError: If the YAML structure is invalid.
    """

    # Convert string path to Path object.
    # Path is safer and more convenient than plain strings for file operations.
    case_path = Path(path)

    # Check whether the file exists before opening it.
    if not case_path.exists():
        raise FileNotFoundError(f"Case file not found: {case_path}")

    # Open the YAML file using UTF-8.
    # UTF-8 avoids issues with Chinese or special characters.
    with case_path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file)

    # yaml.safe_load returns None if the file is empty.
    if raw is None:
        raise ValueError(f"Case file is empty: {case_path}")

    # Convert the raw dictionary into a validated InferCase object.
    # This is where Pydantic checks types and required fields.
    return InferCase.model_validate(raw)