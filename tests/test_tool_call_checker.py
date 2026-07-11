"""Tests for tool call analyzer."""

from infermatrix.analyzers.tool_call_checker import check_tool_call
from infermatrix.cases import CaseExpected, load_case
from infermatrix.clients.mock_openai import MockOpenAIClient
from infermatrix.parsers.tool_call_parser import (
    ParsedToolCall,
    ParsedToolCallMessage,
    parse_tool_call_response,
)


def _parsed_weather_tool_call():
    """构造当前项目中的标准 weather tool call。

    完整链路：

    tool_call_weather.yaml
        ↓
    load_case()
        ↓
    MockOpenAIClient.run_case()
        ↓
    raw tool call response
        ↓
    parse_tool_call_response()
        ↓
    ParsedToolCallMessage
    """

    case = load_case("examples/tool_call_weather.yaml")
    response = MockOpenAIClient().run_case(case)
    parsed_message = parse_tool_call_response(response)

    return case, parsed_message


def test_check_tool_call_passes_for_weather_case() -> None:
    """标准 weather tool call 的名称和参数都应该通过。"""

    case, parsed_message = _parsed_weather_tool_call()

    results = check_tool_call(case, parsed_message)

    assert len(results) == 2

    name_result = results[0]
    arguments_result = results[1]

    assert name_result.name == "tool_name"
    assert name_result.status == "pass"
    assert name_result.passed is True
    assert name_result.expected_tool_name == "get_weather"
    assert name_result.actual_tool_name == "get_weather"

    assert arguments_result.name == "tool_arguments_schema"
    assert arguments_result.status == "pass"
    assert arguments_result.passed is True
    assert arguments_result.actual_arguments == {
        "city": "Shenzhen",
        "unit": "celsius",
    }


def test_tool_name_check_fails_when_name_does_not_match() -> None:
    """实际工具名与 expected.tool_name 不同时应该失败。"""

    case, parsed_message = _parsed_weather_tool_call()

    wrong_tool_call = ParsedToolCall(
        id="call_wrong_001",
        type="function",
        name="get_temperature",
        raw_arguments='{"city": "Shenzhen"}',
        arguments={
            "city": "Shenzhen",
        },
    )

    wrong_message = parsed_message.model_copy(
        update={
            "tool_calls": [wrong_tool_call],
        }
    )

    results = check_tool_call(case, wrong_message)
    name_result = results[0]

    assert name_result.status == "fail"
    assert name_result.failed is True
    assert name_result.expected_tool_name == "get_weather"
    assert name_result.actual_tool_name == "get_temperature"
    assert "does not match" in name_result.reason


def test_arguments_schema_check_fails_when_required_city_is_missing() -> None:
    """缺少 required city 时，arguments Schema 检查应该失败。"""

    case, parsed_message = _parsed_weather_tool_call()
    original_call = parsed_message.tool_calls[0]

    broken_call = original_call.model_copy(
        update={
            "raw_arguments": '{"unit": "celsius"}',
            "arguments": {
                "unit": "celsius",
            },
        }
    )

    broken_message = parsed_message.model_copy(
        update={
            "tool_calls": [broken_call],
        }
    )

    results = check_tool_call(case, broken_message)
    arguments_result = results[1]

    assert arguments_result.status == "fail"
    assert arguments_result.failed is True
    assert "required" in arguments_result.reason


def test_arguments_schema_check_fails_when_city_type_is_wrong() -> None:
    """city 不是 string 时，arguments Schema 检查应该失败。"""

    case, parsed_message = _parsed_weather_tool_call()
    original_call = parsed_message.tool_calls[0]

    broken_call = original_call.model_copy(
        update={
            "raw_arguments": '{"city": 123}',
            "arguments": {
                "city": 123,
            },
        }
    )

    broken_message = parsed_message.model_copy(
        update={
            "tool_calls": [broken_call],
        }
    )

    results = check_tool_call(case, broken_message)
    arguments_result = results[1]

    assert arguments_result.status == "fail"
    assert arguments_result.failed is True
    assert "not of type" in arguments_result.reason or "type" in arguments_result.reason


def test_tool_name_check_skips_when_expected_name_is_missing() -> None:
    """没有 expected.tool_name 时，名称检查应该跳过。"""

    case, parsed_message = _parsed_weather_tool_call()

    skip_case = case.model_copy(
        update={
            "expected": CaseExpected(
                tool_name=None,
                arguments_schema_valid=True,
            )
        }
    )

    results = check_tool_call(skip_case, parsed_message)
    name_result = results[0]

    assert name_result.status == "skip"
    assert name_result.skipped is True


def test_arguments_schema_check_skips_when_flag_is_not_true() -> None:
    """arguments_schema_valid 不是 true 时应该跳过参数校验。"""

    case, parsed_message = _parsed_weather_tool_call()

    skip_case = case.model_copy(
        update={
            "expected": CaseExpected(
                tool_name="get_weather",
                arguments_schema_valid=False,
            )
        }
    )

    results = check_tool_call(skip_case, parsed_message)
    arguments_result = results[1]

    assert arguments_result.status == "skip"
    assert arguments_result.skipped is True
    assert "arguments_schema_valid is not true" in arguments_result.reason


def test_arguments_schema_check_fails_when_tool_definition_is_missing() -> None:
    """case.tools 没有实际工具定义时，参数检查应该明确失败。"""

    case, parsed_message = _parsed_weather_tool_call()

    broken_case = case.model_copy(
        update={
            "tools": [],
        }
    )

    results = check_tool_call(broken_case, parsed_message)
    arguments_result = results[1]

    assert arguments_result.status == "fail"
    assert arguments_result.failed is True
    assert "No function tool definition found" in arguments_result.reason