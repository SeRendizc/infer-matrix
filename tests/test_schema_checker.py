"""Tests for JSON Schema checker."""

from infermatrix.analyzers.schema_checker import (
    SchemaCheckResult,
    check_json_schema,
)
from infermatrix.cases import CaseExpected, load_case
from infermatrix.clients.mock_openai import MockOpenAIClient
from infermatrix.parsers.stream_parser import parse_streaming_chunks
from infermatrix.parsers.structured_output_parser import (
    ParsedStructuredOutput,
    parse_structured_output_text,
)


def _structured_output_from_streaming_case():
    """从 streaming_json.yaml 构造 ParsedStructuredOutput。

    这条 helper 串起当前完整链路：

    YAML case
        ↓
    load_case()
        ↓
    MockOpenAIClient.stream_case()
        ↓
    parse_streaming_chunks()
        ↓
    parse_structured_output_text()
        ↓
    ParsedStructuredOutput
    """

    case = load_case("examples/streaming_json.yaml")
    chunks = MockOpenAIClient().stream_case(case)
    stream_message = parse_streaming_chunks(chunks)
    structured_output = parse_structured_output_text(stream_message.merged_content)
    return case, structured_output


def test_check_json_schema_passes_for_streaming_json_case() -> None:
    """streaming_json.yaml 的 structured output 应该符合 expected.json_schema。"""

    case, structured_output = _structured_output_from_streaming_case()

    result = check_json_schema(case, structured_output)

    assert isinstance(result, SchemaCheckResult)
    assert result.name == "json_schema"
    assert result.status == "pass"
    assert result.passed is True
    assert result.failed is False
    assert result.skipped is False
    assert result.expected_schema == case.expected.json_schema
    assert result.actual_data == {
        "status": "ok",
        "answer": "InferMatrix streaming mock",
    }
    assert "matches expected JSON Schema" in result.reason


def test_check_json_schema_fails_when_required_field_is_missing() -> None:
    """缺少 required field 时，schema check 应该失败。"""

    case, _ = _structured_output_from_streaming_case()

    broken_output = ParsedStructuredOutput(
        raw_text='{"status": "ok"}',
        data={
            "status": "ok",
        },
    )

    result = check_json_schema(case, broken_output)

    assert result.status == "fail"
    assert result.passed is False
    assert result.failed is True
    assert result.skipped is False
    assert "required property" in result.reason or "required" in result.reason


def test_check_json_schema_fails_when_field_type_is_wrong() -> None:
    """字段类型错误时，schema check 应该失败。"""

    case, _ = _structured_output_from_streaming_case()

    broken_output = ParsedStructuredOutput(
        raw_text='{"status": "ok", "answer": 123}',
        data={
            "status": "ok",
            "answer": 123,
        },
    )

    result = check_json_schema(case, broken_output)

    assert result.status == "fail"
    assert result.failed is True
    assert "not of type" in result.reason or "type" in result.reason


def test_check_json_schema_fails_when_additional_property_exists() -> None:
    """additionalProperties=false 时，多余字段应该导致失败。"""

    case, _ = _structured_output_from_streaming_case()

    broken_output = ParsedStructuredOutput(
        raw_text='{"status": "ok", "answer": "hello", "extra": true}',
        data={
            "status": "ok",
            "answer": "hello",
            "extra": True,
        },
    )

    result = check_json_schema(case, broken_output)

    assert result.status == "fail"
    assert result.failed is True
    assert "Additional properties" in result.reason or "additional" in result.reason


def test_check_json_schema_skips_when_flag_is_not_true() -> None:
    """expected.json_schema_valid 不是 true 时，应该跳过 schema check。"""

    case, structured_output = _structured_output_from_streaming_case()
    skip_case = case.model_copy(
        update={
            "expected": CaseExpected(
                json_schema_valid=False,
                json_schema=case.expected.json_schema,
            )
        }
    )

    result = check_json_schema(skip_case, structured_output)

    assert result.status == "skip"
    assert result.skipped is True
    assert "json_schema_valid is not true" in result.reason


def test_check_json_schema_skips_when_schema_is_missing() -> None:
    """没有 expected.json_schema 时，应该跳过 schema check。"""

    case, structured_output = _structured_output_from_streaming_case()
    skip_case = case.model_copy(
        update={
            "expected": CaseExpected(
                json_schema_valid=True,
                json_schema=None,
            )
        }
    )

    result = check_json_schema(skip_case, structured_output)

    assert result.status == "skip"
    assert result.skipped is True
    assert "No expected.json_schema configured" in result.reason