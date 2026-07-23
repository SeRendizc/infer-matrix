"""Parser for structured output text.

阶段 C-3 的目标：
把模型输出中的 JSON 文本解析成 Python dict。

为什么要单独写 structured output parser？

因为“模型输出了一段文本”和“这段文本是合法结构化 JSON”
是两件不同的事。

例如模型可能输出：

    {"status": "ok"}

这是合法 JSON object。

但模型也可能输出：

    Sure, here is the JSON:
    {"status": "ok"}

这不是纯 JSON，json.loads() 会失败。

模型还可能输出：

    ["ok"]

这是合法 JSON，但不是 JSON object。

阶段 C-3 的职责是：
    raw text
        ↓
    json.loads(...)
        ↓
    Python dict

注意：
阶段 C-3 只检查 JSON 语法和 JSON 顶层类型。
它不检查 required fields，也不检查 JSON Schema。
JSON Schema 校验属于后续 analyzer/checker。
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StructuredOutputParseError(ValueError):
    """结构化输出解析失败。

    这个错误表示：
    模型输出的文本不能被解析成阶段 C-3 支持的 structured output。

    常见原因：
    - 输出为空
    - 输出不是字符串
    - 输出不是合法 JSON
    - 输出是合法 JSON，但顶层不是 object
    """


class ParsedStructuredOutput(BaseModel):
    """解析后的结构化输出。

    字段说明：
    - raw_text: 原始模型输出文本
    - data: json.loads(raw_text) 后得到的 Python dict

    为什么保留 raw_text？
        因为后续 report 需要展示原始输出，方便复现和排查。

    为什么保留 data？
        因为后续 schema checker 要基于 data 做字段校验。
    """

    model_config = ConfigDict(extra="forbid")

    raw_text: str = Field(min_length=1)
    data: dict[str, Any]


def parse_structured_output_text(raw_text: str) -> ParsedStructuredOutput:
    """把结构化输出文本解析成 ParsedStructuredOutput。

    Args:
        raw_text: 模型输出的原始文本。

    Returns:
        ParsedStructuredOutput: 解析后的结构化输出对象。

    Raises:
        StructuredOutputParseError:
            - raw_text 不是字符串
            - raw_text 是空文本
            - raw_text 不是合法 JSON
            - raw_text 解析后不是 JSON object

    阶段 C-3 的解析边界：
        - 输入必须是字符串
        - 去掉首尾空白后不能为空
        - 必须能被 json.loads() 解析
        - 解析结果必须是 dict，也就是 JSON object
    """

    if not isinstance(raw_text, str):
        raise StructuredOutputParseError("Structured output text must be a string.")

    stripped_text = raw_text.strip()

    if not stripped_text:
        raise StructuredOutputParseError("Structured output text must not be empty.")

    try:
        parsed = json.loads(stripped_text)
    except json.JSONDecodeError as error:
        raise StructuredOutputParseError(
            "Structured output text must be valid JSON: "
            f"{error.msg} at line {error.lineno}, column {error.colno}."
        ) from error

    if not isinstance(parsed, dict):
        raise StructuredOutputParseError("Structured output text must decode to a JSON object.")

    return ParsedStructuredOutput(
        raw_text=raw_text,
        data=parsed,
    )