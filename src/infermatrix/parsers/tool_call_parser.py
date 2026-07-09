"""Parser for OpenAI-compatible tool call responses.

阶段 C-1 的目标：
把 OpenAI-compatible chat completion response 里的 tool_calls
从原始嵌套 dict 解析成结构清晰、可测试的 Python 对象。

为什么要单独写 tool call parser？

因为 tool calling response 和普通文本 response 不一样。

普通文本 response 的核心字段是：

    choices[0].message.content

tool call response 的核心字段是：

    choices[0].message.tool_calls

而且 tool call 里最容易出问题的是：

    tool_calls[0].function.arguments

注意：
OpenAI-compatible tool call 里的 function.arguments 通常是 JSON string，
不是 Python dict。

也就是说，原始响应里通常长这样：

    "arguments": "{\\"city\\": \\"Shenzhen\\"}"

parser 要做的是：

    JSON string → json.loads(...) → Python dict

阶段 C-1 暂时只解析 non-streaming tool call response。
streaming tool call parser 会后续单独处理。
"""

from __future__ import annotations

import json
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class ToolCallParseError(ValueError):
    """工具调用响应解析失败。

    这个错误表示：
    backend 返回了一个看起来应该是 tool call 的 response，
    但它的结构不符合我们当前支持的 OpenAI-compatible tool call 格式。

    例如：
    - 没有 choices
    - choices 为空
    - message 不是 object
    - tool_calls 不是 list
    - function.arguments 不是合法 JSON string
    """

class ParsedToolCall(BaseModel):
    """解析后的单个 tool call。

    一个 assistant message 里可能包含多个 tool call。
    阶段 C-1 先支持解析多个，但测试重点放在一个 tool call。

    字段说明：
    - id: tool call 的唯一 ID，例如 call_mock_001
    - type: tool call 类型，目前只支持 function
    - name: 函数/工具名，例如 get_weather
    - raw_arguments: 原始 JSON 字符串
    - arguments: json.loads(raw_arguments) 后得到的 Python dict
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: Literal["function"] = "function"
    name: str = Field(min_length=1)
    raw_arguents: str
    arguments: dict[str, Any]


class ParsedToolCallMessage(BaseModel):
    """解析后的 assistant tool call message。

    这是 parse_tool_call_response() 的返回对象。

    它不是单个 tool call，而是“一条 assistant 消息”。
    这条 assistant 消息里可能有一个或多个 tool calls。
    """

    model_config = ConfigDict(extra="forbid")

    model: str | None = None
    choice_index: int = 0
    role: Literal["assistant"] = "assistant"
    finish_reason: str | None = None
    tool_calls: list[ParsedToolCall] = Field(min_length=1)


def parse_tool_call_response(response: dict[str, Any]) -> ParsedToolCallMessage:
    """解析 OpenAI-compatible non-streaming tool call response。

    Args:
        response: backend 返回的原始 response dict。

    Returns:
        ParsedToolCallMessage: 解析后的 tool call message。

    Raises:
        ToolCallParseError: 当响应结构不符合阶段 C-1 支持的格式。

    阶段 C-1 的解析边界：
        - 只解析 choices[0]
        - 只支持 assistant message
        - 只支持 message.tool_calls
        - 只支持 type == "function"
        - function.arguments 必须是合法 JSON string
        - arguments 解析后必须是 JSON object，也就是 Python dict
    """

    model = _optinal_string(response, "model")
    choices = _required_list(response, "choices")

    if not choices:
        raise ToolCallParseError("Response field 'choices' must not be empty.")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ToolCallParseError("Response field 'choices' must be an object.")

    choice_index = first_choice.get("index", 0)
    if not isinstance(choice_index, int):
        raise ToolCallParseError("Response choices[0].index must be an integer.")

    finish_reason = first_choice.get("finish_reason")
    if finish_reason is not None and not isinstance(finish_reason, str):
        raise ToolCallParseError("Response choices[0].finish_reason must be a string or null.")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise ToolCallParseError("Response choices[0].message must be an object.")

    role = message.get("role")
    if role != "assistant":
        raise ToolCallParseError("Response choices[0].message.role must be 'assistant'.")

    tool_calls = _required_list(message, "tool_calls")
    if not tool_calls:
        raise ToolCallParseError("Response choices[0].message.tool_calls must not be empty.")

    parsed_tool_calls = [
        _parse_single_tool_call(tool_call, index=index)
        for index, tool_call in enumerate(tool_calls)
    ]

    return ParsedToolCallMessage(
        model = model,
        choice_index = choice_index,
        role = "assistant",
        finish_reason = finish_reason,
        tool_calls = parsed_tool_calls,
    )


def _parse_single_tool_call(tool_call: Any, index: int) -> ParsedToolCall:
    """解析 tool_calls 列表中的单个 tool call。

    Args:
        tool_call: 原始 tool_call 对象。
        index: 当前 tool_call 在 tool_calls 列表中的位置。

    Returns:
        ParsedToolCall: 解析后的单个 tool call。

    Raises:
        ToolCallParseError: 当前 tool call 结构不合法。

    为什么传 index？
        为了让错误信息更清楚。
        例如 tool_calls[0] 坏了，还是 tool_calls[1] 坏了。
    """