"""Analyzer for parsed tool calls.

阶段 C-5 的目标：
检查 ParsedToolCallMessage 是否符合 InferCase 中声明的预期。

当前执行两个相互独立的检查：

1. tool_name
   检查模型实际调用的工具名，是否等于 expected.tool_name。

2. tool_arguments_schema
   检查已经解析成 Python dict 的 arguments，
   是否符合 tools[*].function.parameters 中定义的 JSON Schema。

职责边界：

ToolCallParser 负责：
    raw function.arguments JSON string
        ↓
    Python dict

ToolCallAnalyzer 负责：
    Python dict + expected / tool parameters schema
        ↓
    pass / fail / skip

这个模块不再调用 json.loads()，因为 JSON 语法解析已经由 parser 完成。
"""

from __future__ import annotations

from typing import Any, Literal

from jsonschema import SchemaError, ValidationError, validate
from pydantic import BaseModel, ConfigDict, Field

from infermatrix.cases import InferCase
from infermatrix.parsers import (
    ParsedToolCall,
    ParsedToolCallMessage,
)


class ToolCallCheckError(ValueError):
    """Tool Call 检查过程本身无法正常执行。

    这个错误不表示模型输出不符合预期。

    它表示调用 analyzer 的代码有问题，例如：
    - tool_call_index 是负数
    - tool_call_index 超出 tool_calls 列表范围

    模型输出不符合 expected 时，应该返回 status="fail"，
    而不是抛出这个异常。
    """


class ToolCallCheckResult(BaseModel):
    """单个 Tool Call 检查结果。

    一个 tool call 当前会产生两个结果：

    - name="tool_name"
    - name="tool_arguments_schema"

    字段说明：

    name:
        当前检查项名称。

    status:
        pass：执行了检查并通过。
        fail：执行了检查但不符合预期。
        skip：case 没要求执行这个检查。

    expected_tool_name:
        case.expected.tool_name 中配置的预期工具名。

    actual_tool_name:
        模型实际返回的工具名。

    expected_schema:
        从 tools[*].function.parameters 中找到的参数 Schema。

    actual_arguments:
        ToolCallParser 已经解析好的 Python dict。

    reason:
        人可以直接阅读的检查原因。
    """

    model_config = ConfigDict(extra="forbid")

    name: Literal["tool_name", "tool_arguments_schema"]
    status: Literal["pass", "fail", "skip"]

    expected_tool_name: str | None = None
    actual_tool_name: str | None = None

    expected_schema: dict[str, Any] | None = None
    actual_arguments: dict[str, Any] | None = None

    reason: str = Field(min_length=1)

    @property
    def passed(self) -> bool:
        """当前检查是否通过。"""
        return self.status == "pass"

    @property
    def failed(self) -> bool:
        """当前检查是否失败。"""
        return self.status == "fail"

    @property
    def skipped(self) -> bool:
        """当前检查是否跳过。"""
        return self.status == "skip"


def check_tool_call(
    case: InferCase,
    parsed_message: ParsedToolCallMessage,
    tool_call_index: int = 0,
) -> list[ToolCallCheckResult]:
    """检查一条已经解析完成的 tool call。

    Args:
        case:
            当前执行的 InferCase。

        parsed_message:
            ToolCallParser 返回的 ParsedToolCallMessage。

        tool_call_index:
            要检查 parsed_message.tool_calls 中的第几个调用。
            阶段 C-5 默认检查第一个，也就是下标 0。

    Returns:
        两个 ToolCallCheckResult：

        1. tool_name 检查结果
        2. tool_arguments_schema 检查结果

    Raises:
        ToolCallCheckError:
            tool_call_index 超出有效范围。

    为什么返回 list？

        因为工具名称和参数 Schema 是两个独立检查。

        可能出现：

        - 名称通过，参数失败
        - 名称失败，参数通过
        - 名称跳过，参数通过

        如果只返回一个 bool，就看不出到底是哪一步出了问题。
    """

    tool_call = _get_tool_call(
        parsed_message=parsed_message,
        tool_call_index=tool_call_index,
    )

    return [
        _check_tool_name(
            case=case,
            tool_call=tool_call,
        ),
        _check_tool_arguments_schema(
            case=case,
            tool_call=tool_call,
        ),
    ]


def _get_tool_call(
    parsed_message: ParsedToolCallMessage,
    tool_call_index: int,
) -> ParsedToolCall:
    """从 ParsedToolCallMessage 中取得指定 tool call。

    parser 已经保证 tool_calls 非空，但 analyzer 仍然检查 index，
    防止调用方传入无效下标。
    """

    if tool_call_index < 0:
        raise ToolCallCheckError("tool_call_index must be greater than or equal to 0.")

    if tool_call_index >= len(parsed_message.tool_calls):
        raise ToolCallCheckError(
            "tool_call_index is out of range: "
            f"received {tool_call_index}, "
            f"but message contains {len(parsed_message.tool_calls)} tool call(s)."
        )

    return parsed_message.tool_calls[tool_call_index]


def _check_tool_name(case: InferCase, tool_call: ParsedToolCall) -> ToolCallCheckResult:
    """检查实际 tool name 是否符合 expected.tool_name。"""

    expected_name = case.expected.tool_name
    actual_name = tool_call.name

    # expected.tool_name 没有配置，说明当前 case 没要求检查工具名称。
    if expected_name is None:
        return ToolCallCheckResult(
            name="tool_name",
            status="skip",
            expected_tool_name=None,
            actual_tool_name=actual_name,
            actual_arguments=tool_call.arguments,
            reason=(
                "No expected.tool_name configured; "
                "skipped tool name check."
            ),
        )

    if actual_name != expected_name:
        return ToolCallCheckResult(
            name="tool_name",
            status="fail",
            expected_tool_name=expected_name,
            actual_tool_name=actual_name,
            actual_arguments=tool_call.arguments,
            reason=(
                "Tool name does not match expected value: "
                f"expected '{expected_name}', received '{actual_name}'."
            ),
        )

    return ToolCallCheckResult(
        name="tool_name",
        status="pass",
        expected_tool_name=expected_name,
        actual_tool_name=actual_name,
        actual_arguments=tool_call.arguments,
        reason=f"Tool name matches expected value '{expected_name}'.",
    )


def _check_tool_arguments_schema(
    case: InferCase,
    tool_call: ParsedToolCall,
) -> ToolCallCheckResult:
    """检查 tool call arguments 是否符合工具参数 Schema。

    Schema 来源：

        case.tools[*].function.parameters

    例如：

        tools:
          - type: function
            function:
              name: get_weather
              parameters:
                type: object
                properties:
                  city:
                    type: string
                required:
                  - city
    """

    expected_name = case.expected.tool_name
    actual_name = tool_call.name

    # 没要求校验 arguments schema 时，该检查项应该是 skip，
    # 而不是自动判定为 pass。
    if not case.expected.arguments_schema_valid:
        return ToolCallCheckResult(
            name="tool_arguments_schema",
            status="skip",
            expected_tool_name=expected_name,
            actual_tool_name=actual_name,
            actual_arguments=tool_call.arguments,
            reason=(
                "expected.arguments_schema_valid is not true; "
                "skipped tool arguments Schema check."
            ),
        )

    tool_definition = _find_tool_definition(
        case=case,
        tool_name=actual_name,
    )

    if tool_definition is None:
        return ToolCallCheckResult(
            name="tool_arguments_schema",
            status="fail",
            expected_tool_name=expected_name,
            actual_tool_name=actual_name,
            actual_arguments=tool_call.arguments,
            reason=(
                f"No function tool definition found for '{actual_name}' "
                "in case.tools."
            ),
        )

    function_definition = tool_definition.get("function")

    if not isinstance(function_definition, dict):
        return ToolCallCheckResult(
            name="tool_arguments_schema",
            status="fail",
            expected_tool_name=expected_name,
            actual_tool_name=actual_name,
            actual_arguments=tool_call.arguments,
            reason=(
                f"Tool definition for '{actual_name}' does not contain "
                "a valid function object."
            ),
        )

    parameters_schema = function_definition.get("parameters")

    if not isinstance(parameters_schema, dict):
        return ToolCallCheckResult(
            name="tool_arguments_schema",
            status="fail",
            expected_tool_name=expected_name,
            actual_tool_name=actual_name,
            actual_arguments=tool_call.arguments,
            reason=(
                f"Tool definition for '{actual_name}' does not contain "
                "a valid function.parameters JSON Schema."
            ),
        )

    try:
        validate(
            instance=tool_call.arguments,
            schema=parameters_schema,
        )
    except SchemaError as error:
        # SchemaError 表示 case 自己配置的 Schema 不合法。
        # 这不是模型输出错误，而是测试用例定义错误。
        return ToolCallCheckResult(
            name="tool_arguments_schema",
            status="fail",
            expected_tool_name=expected_name,
            actual_tool_name=actual_name,
            expected_schema=parameters_schema,
            actual_arguments=tool_call.arguments,
            reason=(
                "Configured tool parameters Schema is invalid: "
                f"{error.message}"
            ),
        )
    except ValidationError as error:
        # ValidationError 表示 Schema 本身合法，
        # 但模型实际生成的 arguments 不符合 Schema。
        return ToolCallCheckResult(
            name="tool_arguments_schema",
            status="fail",
            expected_tool_name=expected_name,
            actual_tool_name=actual_name,
            expected_schema=parameters_schema,
            actual_arguments=tool_call.arguments,
            reason=(
                "Tool arguments do not match function.parameters Schema: "
                f"{error.message}"
            ),
        )

    return ToolCallCheckResult(
        name="tool_arguments_schema",
        status="pass",
        expected_tool_name=expected_name,
        actual_tool_name=actual_name,
        expected_schema=parameters_schema,
        actual_arguments=tool_call.arguments,
        reason=(f"Tool arguments match the parameters Schema for '{actual_name}'."),
    )


def _find_tool_definition(
    case: InferCase,
    tool_name: str,
) -> dict[str, Any] | None:
    """在 case.tools 中查找指定名称的 function tool。

    case.tools 当前使用 list[dict[str, Any]]，所以这里需要手动检查结构。

    后续如果工具定义变复杂，可以再把它重构成独立 Pydantic 模型。
    当前阶段先保持最小实现。
    """

    for tool_definition in case.tools:
        if not isinstance(tool_definition, dict):
            continue

        if tool_definition.get("type") != "function":
            continue

        function_definition = tool_definition.get("function")
        if not isinstance(function_definition, dict):
            continue

        if function_definition.get("name") == tool_name:
            return tool_definition

    return None