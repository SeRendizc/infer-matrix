"""
Mock OpenAI-compatible client.

这个 client 不会调用真实模型。

它会返回一个稳定、可预测、结构类似 OpenAI Chat Completions API 的响应。
这样我们就可以在没有网络、没有 API key、没有 GPU 的情况下测试 InferMatrix。
"""

from typing import Any

from infermatrix.cases import InferCase
from infermatrix.clients.base import BaseClient

class MockOpenAIClient(BaseClient):
    """
    一个假的 OpenAI-compatible client。

    阶段 B 只支持最简单的普通 chat completion。

    暂时不支持：
    - streaming
    - tool calling
    - structured output

    这些功能会在后续阶段逐步加入。
    """

    def run_case(self, case: InferCase):
        """
        运行一个 case，并返回 mock chat completion response。

        Args:
            case: 已经通过校验的 InferCase 对象。

        Returns:
            一个结构类似 OpenAI Chat Completion 的 dict。
        """

        self._ensure_supported_features(case)

        content = self._build_content(case)

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

    def _ensure_supported_features(self, case: InferCase) -> None:
        """
        检查当前 case 是否属于阶段 B 支持范围。

        阶段 B 只支持普通非流式 chat case。
        如果 YAML case 开启了 streaming、tool calling 或 structured output，
        这里会直接报错。

        这样做的好处是：不支持的功能要明确失败，不要假装支持。
        """

        if case.features.streaming:
            raise NotImplementedError(
                "Phase B mock client does not support streaming yet."
            )

        if case.features.tool_calling:
            raise NotImplementedError(
                "Phase B mock client does not support tool calling yet."
            )

        if case.features.structured_output:
            raise NotImplementedError(
                "Phase B mock client does not support structured output yet."
            )
        
    def _build_content(self, case: InferCase) -> str:
        """
        构造 mock assistant 回复内容。

        优先使用 metadata.mock_response。
        如果 YAML case 没有提供 mock_response，就返回一个默认回复。

        metadata.mock_response 是阶段 B 为了测试 mock client 添加的可控响应内容。
        """

        mock_response = case.metadata.get("mock_response")

        if isinstance(mock_response, str) and mock_response.strip():
            return mock_response
        
        return "InferMatrix is an Agentic LLM Systems behavior analysis framework."