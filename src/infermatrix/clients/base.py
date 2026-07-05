"""
Base client interfaces for InferMatrix.

这个模块定义 InferMatrix 中所有 backend client 的共同接口。

在 InferMatrix 里，client 负责接收一个 InferCase，然后返回一个后端响应。
这个后端可以是假后端，也可以是真实的 OpenAI-compatible 服务。
"""

from abc import ABC, abstractmethod  # ABC, Abstract Base Class, 抽象基类
from typing import Any

from infermatrix.cases import InferCase

class BaseClient(ABC):
    """
    所有 InferMatrix client 的抽象基类。

    这个类不是直接拿来用的，而是拿来规定“子类必须实现什么方法”。

    例如后面会有：

    - MockOpenAIClient
    - OpenAICompatibleClient
    - VLLMClient
    - SGLangClient

    它们都应该实现 run_case(case) 方法。
    """

    @abstractmethod
    def run_case(self, case: InferCase) -> dict[str, Any]:
        """
        运行一个 InferMatrix case，并返回后端响应。

        Args:
            case: 已经通过 Pydantic 校验的 InferCase 对象。

        Returns:
            一个 dict，表示 backend response。

        注意：
            阶段 B 先用 dict。
            后面如果响应结构变复杂，可以再抽成 Pydantic response model。
        """
        raise NotImplementedError