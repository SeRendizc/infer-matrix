"""
Parser for OpenAI-compatible chat completion responses.

阶段 C 的目标：
把 OpenAI-compatible chat completion response 里的 assistant message
从嵌套 dict 中解析出来，变成一个结构清晰、可测试的 Python 对象。

阶段 C 暂时只解析普通非流式 content response。
后续阶段会继续扩展：
- tool_calls
- streaming chunks
- structured output
- multi-choice comparison
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatCompletionParseError(ValueError):
    """Raised when a chat completion response cannot be parsed.

    这是 InferMatrix 自己定义的解析错误。

    为什么不用普通 ValueError？
    因为后续上层代码可以专门捕获 ChatCompletionParseError，
    从而区分“响应解析失败”和其他普通 Python 错误。
    """

class ParsedAssistantMessage(BaseModel):
    """Parsed assistant message from a chat completion response.

    这个对象是 parser 的输出。

    它把原始 response 中最重要的信息整理出来：
    - model: 使用的模型名
    - choice_index: 第几个候选回复
    - role: 消息角色，目前只支持 assistant
    - content: assistant 的文本内容
    - finish_reason: 模型停止原因
    """

    model_config = ConfigDict(extra = "forbid")

    model: str | None = None
    choice_index: int = 0
    role: Literal["assistant"] = "assistant"
    content: str = Field(min_length = 1)
    finish_reason : str | None = None

def parse_chat_completion_response(response: dict[str, Any]) -> ParsedAssistantMessage:
    """Parse an OpenAI-compatible chat completion response.

    Args:
        response: Raw backend response dict.

    Returns:
        ParsedAssistantMessage extracted from choices[0].message.content.

    Raises:
        ChatCompletionParseError: If the response shape is invalid or unsupported.
    """

    model = _optional_string(response, "model")
    choices = _required_list(response, "choices")

    if not choices:
        raise ChatCompletionParseError("Response field 'choices' must not be empty.")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ChatCompletionParseError("Response choices[0] must be an object.")

    choice_index = first_choice.get("index", 0)
    if not isinstance(choice_index, int):
        raise ChatCompletionParseError("Response choices[0].index must be an integer.")

    finish_reason = first_choice.get("finish_reason")
    if finish_reason is not None and not isinstance(finish_reason, str):
        raise ChatCompletionParseError("Response choices[0].finish_reason must be a string or null.")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise ChatCompletionParseError("Response choices[0].message must be an object.")

    role = message.get("role")
    if role != "assistant":
        raise ChatCompletionParseError("Response choices[0].role must be 'assistant'.")

    # 阶段 C 暂时只支持普通文本 content。
    # tool_calls 会在后续阶段单独处理。
    if "tool_calls" in message and message.get("content") in (None, ""):
        raise ChatCompletionParseError("Tool call responses are not supported by the Phase C parser.")

    content = message.get("content")
    if not isinstance(content, str):
        raise ChatCompletionParseError("Response choices[0].message.content must be a string.")

    if not content.strip():
        raise ChatCompletionParseError("Response choices[0].message.content must not be empty.")

    return ParsedAssistantMessage(
        model = model,
        choice_index = choice_index,
        role = "assistant",
        content = content,
        finish_reason = finish_reason,
    )


def _required_list(data: dict[str, Any], key: str) -> list[Any]:
    """Return a required list field from a dict."""

    value =  data.get(key)
    if not isinstance(value, list):
        raise ChatCompletionParseError(f"Response field {key} must be a list.")
    return value


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    """Return an optional string field from a dict."""

    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ChatCompletionParseError(f"Response field {key} must be a string.")
    return value