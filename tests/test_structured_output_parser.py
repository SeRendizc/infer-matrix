"""Tests for structured output parser."""

import pytest

from agent_eval_lab.cases import load_case
from agent_eval_lab.clients.mock_openai import MockOpenAIClient
from agent_eval_lab.parsers.stream_parser import parse_streaming_chunks
from agent_eval_lab.parsers.structured_output_parser import (
    ParsedStructuredOutput,
    StructuredOutputParseError,
    parse_structured_output_text,
)


def test_parse_structured_output_text_from_plain_json_object() -> None:
    """parser 应该能解析普通 JSON object 文本。"""

    raw_text = '{"status": "ok", "answer": "hello"}'

    parsed = parse_structured_output_text(raw_text)

    assert isinstance(parsed, ParsedStructuredOutput)
    assert parsed.raw_text == raw_text
    assert parsed.data == {
        "status": "ok",
        "answer": "hello",
    }


def test_parse_structured_output_text_allows_outer_whitespace() -> None:
    """JSON 文本前后有空白时，应该仍然可以解析。"""

    raw_text = '  \n{"status": "ok"}\n  '

    parsed = parse_structured_output_text(raw_text)

    assert parsed.raw_text == raw_text
    assert parsed.data == {
        "status": "ok",
    }


def test_parse_structured_output_from_streaming_case() -> None:
    """structured parser 应该能解析 streaming parser 合并出的 JSON 文本。

    这个测试验证完整链路：

    streaming_json.yaml
        ↓
    MockOpenAIClient.stream_case()
        ↓
    parse_streaming_chunks()
        ↓
    parse_structured_output_text()
    """

    case = load_case("examples/streaming_json.yaml")
    chunks = MockOpenAIClient().stream_case(case)

    stream_message = parse_streaming_chunks(chunks)
    structured_output = parse_structured_output_text(stream_message.merged_content)

    assert structured_output.data == {
        "status": "ok",
        "answer": "Agent Eval Lab streaming mock",
    }


def test_parse_structured_output_rejects_empty_text() -> None:
    """空文本应该解析失败。"""

    with pytest.raises(StructuredOutputParseError, match="must not be empty"):
        parse_structured_output_text("   ")


def test_parse_structured_output_rejects_invalid_json() -> None:
    """不是合法 JSON 时，应该解析失败。"""

    raw_text = '{"status": "ok"'

    with pytest.raises(StructuredOutputParseError, match="valid JSON"):
        parse_structured_output_text(raw_text)


def test_parse_structured_output_rejects_json_array() -> None:
    """合法 JSON array 不是 JSON object，所以阶段 C-3 应该拒绝。"""

    raw_text = '["ok", "hello"]'

    with pytest.raises(StructuredOutputParseError, match="JSON object"):
        parse_structured_output_text(raw_text)


def test_parse_structured_output_rejects_plain_text() -> None:
    """普通自然语言文本不是 JSON，应该解析失败。"""

    raw_text = "Sure, here is the answer."

    with pytest.raises(StructuredOutputParseError, match="valid JSON"):
        parse_structured_output_text(raw_text)