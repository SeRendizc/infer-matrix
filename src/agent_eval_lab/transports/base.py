"""Protocol-independent HTTP transport interfaces."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from agent_eval_lab.transports.models import (
    HttpExchange,
)


@runtime_checkable
class SyncHttpTransport(Protocol):
    """同步 HTTP Transport 契约。"""

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str] | None = None,
        content: bytes | str | None = None,
    ) -> HttpExchange:
        """发送一个原始 HTTP 请求。"""

    def close(self) -> None:
        """释放 Transport 资源。"""


@runtime_checkable
class AsyncHttpTransport(Protocol):
    """异步 HTTP Transport 契约。"""

    async def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str] | None = None,
        content: bytes | str | None = None,
    ) -> HttpExchange:
        """异步发送一个原始 HTTP 请求。"""

    async def aclose(self) -> None:
        """异步释放 Transport 资源。"""