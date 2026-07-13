"""Tests for InferMatrix case loading."""

from pathlib import Path

from infermatrix.cases import load_case


def test_load_basic_chat_case() -> None:
    """The example basic chat YAML should be loaded correctly."""

    # Arrange: prepare the path to the example case.
    case_path = Path("examples/basic_chat.yaml")

    # Act: load the case.
    case = load_case(case_path)

    # Assert: check that fields are parsed as expected.
    assert case.case_id == "basic_chat_001"
    assert case.backend.provider == "mock"
    assert case.model == "mock-model"

    assert case.features.streaming is False
    assert case.features.tool_calling is False
    assert case.features.structured_output is False

    assert len(case.messages) == 1
    assert case.messages[0].role == "user"
    assert "InferMatrix" in case.messages[0].content

    assert case.expected.contains_text == "InferMatrix"
    assert case.metadata["purpose"] == (
        "Validate that the case loader can parse a minimal chat case."
    )