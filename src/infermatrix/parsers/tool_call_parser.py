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

class ParseToolCall(BaseModel):
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