"""Tests for the mock OpenAI-compatible client."""

from pathlib import Path

import pytest

from agent_eval_lab.cases import CaseFeatures, load_case
from agent_eval_lab.clients.mock_openai import MockOpenAIClient


def test_mock_client_returns_chat_completion_response() -> None:
    """MockOpenAIClient should return an OpenAI-compatible chat response."""

    # Arrange: load a validated case and create a mock client.
    case = load_case(Path("examples/basic_chat.yaml"))
    client = MockOpenAIClient()

    # Act: run the case against the mock backend.
    response = client.run_case(case)

    # Assert: check top-level response fields.
    assert response["id"] == "chatcmpl-mock-basic_chat_001"
    assert response["object"] == "chat.completion"
    assert response["created"] == 0
    assert response["model"] == "mock-model"

    # Assert: check choices.
    assert len(response["choices"]) == 1

    choice = response["choices"][0]
    assert choice["index"] == 0
    assert choice["finish_reason"] == "stop"

    # Assert: check assistant message.
    message = choice["message"]
    assert message["role"] == "assistant"
    assert message["content"] == case.metadata["mock_response"]
    assert "Agent Eval Lab" in message["content"]

    # Assert: check usage placeholder.
    assert response["usage"] == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def test_mock_client_rejects_streaming_case() -> None:
    """Phase B mock client should fail clearly when streaming is enabled."""

    # Arrange: load a normal case, then create a modified copy with streaming enabled.
    case = load_case(Path("examples/basic_chat.yaml"))
    streaming_case = case.model_copy(
        update={
            "features": CaseFeatures(
                streaming=True,
                tool_calling=False,
                structured_output=False,
            )
        }
    )

    client = MockOpenAIClient()

    # Act + Assert: streaming is not supported in Phase B.
    with pytest.raises(NotImplementedError, match="streaming"):
        client.run_case(streaming_case)