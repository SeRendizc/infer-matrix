"""Mock OpenAI-compatible client.

这个 client 不会调用真实模型。

阶段 B-1：
- 支持普通非流式 chat completion。

阶段 B-2：
- 支持模拟 tool call response。
- 支持模拟 streaming chunks。

注意：
这里的目标是“模拟 OpenAI-compatible 响应形状”，不是验证响应。
验证和分析会放到后续 parser / analyzer 阶段。
"""

from __future__ import annotations

import json
from typing import Any

from infermatrix.cases import InferCase
from infermatrix.clients.base import BaseClient


class MockOpenAIClient(BaseClient):
    """一个假的 OpenAI-compatible client。

    它的职责是根据 InferCase 生成稳定、可预测的 mock response。

    当前支持：
    - 普通 chat completion response
    - tool call response
    - streaming chunk response

    它不负责：
    - 解析 response
    - 判断 response 是否满足 expected
    - 生成正式 report
    """

    def run_case(self, case: InferCase) -> dict[str, Any]:
        """运行一个非流式 case，并返回 mock chat completion response。

        Args:
            case: 已经通过校验的 InferCase 对象。

        Returns:
            一个结构类似 OpenAI Chat Completion 的 dict。

        Raises:
            NotImplementedError: 如果 case 是 streaming case。
        """

        if case.features.streaming:
            raise NotImplementedError(
                "Use stream_case() for streaming cases in Phase B-2."
            )

        if case.features.tool_calling:
            return self._build_tool_call_response(case)

        return self._build_text_response(case)

    def stream_case(self, case: InferCase) -> list[dict[str, Any]]:
        """运行一个 streaming case，并返回 mock streaming chunks。

        Args:
            case: features.streaming=True 的 InferCase。

        Returns:
            一个 chunk 列表，每个 chunk 都模拟 OpenAI streaming response 的一段。

        Raises:
            NotImplementedError: 如果 case 不是 streaming case。
        """

        if not case.features.streaming:
            raise NotImplementedError(
                "stream_case() only supports cases with features.streaming=true."
            )

        chunks = self._get_stream_content_chunks(case)

        stream_id = f"chatcmpl-mock-stream-{case.case_id}"

        response_chunks: list[dict[str, Any]] = [
            {
                "id": stream_id,
                "object": "chat.completion.chunk",
                "created": 0,
                "model": case.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                        },
                        "finish_reason": None,
                    }
                ],
            }
        ]

        for chunk in chunks:
            response_chunks.append(
                {
                    "id": stream_id,
                    "object": "chat.completion.chunk",
                    "created": 0,
                    "model": case.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": chunk,
                            },
                            "finish_reason": None,
                        }
                    ],
                }
            )

        response_chunks.append(
            {
                "id": stream_id,
                "object": "chat.completion.chunk",
                "created": 0,
                "model": case.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
        )

        return response_chunks

    def _build_text_response(self, case: InferCase) -> dict[str, Any]:
        """构造普通文本 chat completion response。"""

        content = self._build_text_content(case)

        return {
            "id": f"chatcmpl-mock-{case.case_id}",
            "object": "chat.completion",
            "created": 0,
            "model": case.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

    def _build_tool_call_response(self, case: InferCase) -> dict[str, Any]:
        """构造 tool call chat completion response。

        阶段 B-2 只负责模拟 tool_calls 的响应形状。

        tool name 来源优先级：
        1. case.expected.tool_name
        2. metadata.mock_tool_name
        3. 默认 "mock_tool"

        arguments 来源：
        - metadata.mock_tool_arguments
        """

        tool_name = (
            case.expected.tool_name
            or self._optional_metadata_string(case, "mock_tool_name")
            or "mock_tool"
        )

        raw_arguments = case.metadata.get("mock_tool_arguments", {})
        if not isinstance(raw_arguments, dict):
            raw_arguments = {}

        arguments = json.dumps(raw_arguments, ensure_ascii=False)

        tool_call_id = (
            self._optional_metadata_string(case, "mock_tool_call_id")
            or "call_mock_001"
        )

        return {
            "id": f"chatcmpl-mock-{case.case_id}",
            "object": "chat.completion",
            "created": 0,
            "model": case.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_call_id,
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": arguments,
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

    def _build_text_content(self, case: InferCase) -> str:
        """构造普通文本回复内容。"""

        mock_response = case.metadata.get("mock_response")

        if isinstance(mock_response, str) and mock_response.strip():
            return mock_response

        return "InferMatrix is an Agentic LLM Systems behavior analysis framework."

    def _get_stream_content_chunks(self, case: InferCase) -> list[str]:
        """读取或构造 streaming content chunks。

        优先使用 metadata.mock_stream_chunks。
        如果没有配置，就把普通 mock_response 当成一个 chunk。
        """

        raw_chunks = case.metadata.get("mock_stream_chunks")

        if isinstance(raw_chunks, list):
            chunks = [chunk for chunk in raw_chunks if isinstance(chunk, str)]
            if chunks:
                return chunks

        return [self._build_text_content(case)]

    def _optional_metadata_string(self, case: InferCase, key: str) -> str | None:
        """从 metadata 中读取一个可选字符串。"""

        value = case.metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value
        return None