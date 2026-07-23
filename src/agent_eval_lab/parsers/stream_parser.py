"""Parser for OpenAI-compatible streaming chat completion chunks.

阶段 C-2 的目标：
把 OpenAI-compatible streaming chunks 解析成一个结构化对象。

普通 non-streaming response 是一个完整 dict：

    response["choices"][0]["message"]["content"]

但是 streaming response 是一组 chunk：

    chunks[0]
    chunks[1]
    chunks[2]
    ...

每个 chunk 里通常只有一小段 delta：

    chunk["choices"][0]["delta"]

常见结构：

1. 第一个 chunk 可能只告诉你 role：

    {"delta": {"role": "assistant"}}

2. 中间 chunk 通常提供 content 片段：

    {"delta": {"content": "hello"}}
    {"delta": {"content": " world"}}

3. 最后 chunk 通常没有 content，但有 finish_reason：

    {"delta": {}, "finish_reason": "stop"}

所以 stream parser 的工作是：

    多个 chunk
        ↓
    收集 role
        ↓
    收集所有 delta.content
        ↓
    拼接 merged_content
        ↓
    找到 finish_reason
        ↓
    返回 ParsedStreamMessage

阶段 C-2 暂时只处理普通 streaming content。
streaming tool calls 暂不处理。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StreamParseError(ValueError):
    """streaming chunks 解析失败。

    这个错误表示：
    backend 返回了一组看起来像 streaming chunks 的数据，
    但它们不符合阶段 C-2 支持的 OpenAI-compatible streaming 格式。

    例如：
    - chunks 不是 list
    - chunks 是空列表
    - chunk["choices"] 缺失
    - choice["delta"] 不是 object
    - delta.role 不是 assistant
    - delta.content 不是 string
    - 没有任何 content chunk
    - 没有 finish_reason
    """


class ParsedStreamMessage(BaseModel):
    """解析后的 streaming assistant message。

    字段说明：
    - model: 模型名，可能不存在
    - choice_index: 当前解析第几个 choice，阶段 C-2 只解析 0
    - role: assistant 角色
    - content_chunks: 从多个 delta.content 收集到的文本片段
    - merged_content: 把 content_chunks 拼起来后的完整文本
    - finish_reason: 最后停止原因，例如 stop
    """

    model_config = ConfigDict(extra="forbid")

    model: str | None = None
    choice_index: int = 0
    role: Literal["assistant"] = "assistant"
    content_chunks: list[str] = Field(min_length=1)
    merged_content: str = Field(min_length=1)
    finish_reason: str


def parse_streaming_chunks(chunks: list[dict[str, Any]]) -> ParsedStreamMessage:
    """解析 OpenAI-compatible streaming chunks。

    Args:
        chunks: MockOpenAIClient.stream_case() 或真实 backend streaming 得到的 chunks。

    Returns:
        ParsedStreamMessage: 合并后的 assistant message。

    Raises:
        StreamParseError: chunks 结构不符合阶段 C-2 支持的格式。

    阶段 C-2 的解析边界：
        - chunks 必须是非空 list
        - 每个 chunk 必须是 dict
        - 每个 chunk 必须有 choices list
        - 阶段 C-2 只读取 choices[0]
        - delta.role 如果出现，必须是 assistant
        - delta.content 如果出现，必须是 string
        - 至少要有一个 content chunk
        - 必须能找到 finish_reason
    """

    if not isinstance(chunks, list):
        raise StreamParseError("Streaming chunks must be a list.")

    if not chunks:
        raise StreamParseError("Streaming chunks must not be empty.")

    model: str | None = None
    role: str | None = None
    choice_index = 0
    content_chunks: list[str] = []
    finish_reason: str | None = None

    for chunk_index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict):
            raise StreamParseError(f"Chunk {chunk_index} must be an object.")

        chunk_model = chunk.get("model")
        if model is None and isinstance(chunk_model, str):
            model = chunk_model

        choices = chunk.get("choices")
        if not isinstance(choices, list):
            raise StreamParseError(f"Chunk {chunk_index}.choices must be a list.")

        if not choices:
            raise StreamParseError(f"Chunk {chunk_index}.choices must not be empty.")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise StreamParseError(f"Chunk {chunk_index}.choices[0] must be an object.")

        current_choice_index = first_choice.get("index", 0)
        if not isinstance(current_choice_index, int):
            raise StreamParseError(f"Chunk {chunk_index}.choices[0].index must be an integer.")

        # 阶段 C-2 只解析第一个 choice。
        # 如果后续 chunk 的 index 不是 0，说明响应形状超出当前支持范围。
        if current_choice_index != 0:
            raise StreamParseError(f"Chunk {chunk_index}.choices[0].index must be 0 in Phase C-2.")

        delta = first_choice.get("delta")
        if not isinstance(delta, dict):
            raise StreamParseError(f"Chunk {chunk_index}.choices[0].delta must be an object.")

        delta_role = delta.get("role")
        if delta_role is not None:
            if delta_role != "assistant":
                raise StreamParseError(f"Chunk {chunk_index}.choices[0].delta.role must be 'assistant'.")
            role = "assistant"

        delta_content = delta.get("content")
        if delta_content is not None:
            if not isinstance(delta_content, str):
                raise StreamParseError(f"Chunk {chunk_index}.choices[0].delta.content must be a string.")

            if delta_content:
                content_chunks.append(delta_content)

        current_finish_reason = first_choice.get("finish_reason")
        if current_finish_reason is not None:
            if not isinstance(current_finish_reason, str):
                raise StreamParseError(f"Chunk {chunk_index}.choices[0].finish_reason must be a string or null.")
            finish_reason = current_finish_reason

    if role != "assistant":
        raise StreamParseError("Streaming chunks must include assistant role.")

    if not content_chunks:
        raise StreamParseError("Streaming chunks must include at least one content chunk.")

    if finish_reason is None:
        raise StreamParseError("Streaming chunks must include finish_reason.")

    merged_content = "".join(content_chunks)

    if not merged_content.strip():
        raise StreamParseError("Merged streaming content must not be empty.")

    return ParsedStreamMessage(
        model=model,
        choice_index=choice_index,
        role="assistant",
        content_chunks=content_chunks,
        merged_content=merged_content,
        finish_reason=finish_reason,
    )