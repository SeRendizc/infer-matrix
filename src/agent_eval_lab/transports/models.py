"""Raw HTTP wire models for Agent Eval Lab.

这里的模型只描述 HTTP 传输事实，不理解任何 LLM API 协议。

例如它不知道：

- choices 是什么
- output item 是什么
- tool call 是什么
- response.completed 是什么

这些都属于后续 Protocol Adapter。
"""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WireBody(BaseModel):
    """无损保存 HTTP Body。

    UTF-8 文本直接保存为 text。
    非 UTF-8 二进制内容保存为 base64。

    这样既方便阅读 JSON，又不会损坏任意二进制响应。
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    encoding: Literal["utf-8", "base64"]
    data: str
    byte_length: int = Field(ge=0)
    content_type: str | None = None

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        *,
        content_type: str | None = None,
    ) -> "WireBody":
        """从原始 bytes 构造可序列化 Body。"""

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return cls(
                encoding="base64",
                data=base64.b64encode(data).decode("ascii"),
                byte_length=len(data),
                content_type=content_type,
            )

        return cls(
            encoding="utf-8",
            data=text,
            byte_length=len(data),
            content_type=content_type,
        )

    def to_bytes(self) -> bytes:
        """恢复原始 bytes。"""

        if self.encoding == "utf-8":
            return self.data.encode("utf-8")

        return base64.b64decode(self.data)


class HeaderEntry(BaseModel):
    """一条 HTTP Header。

    不使用 dict，是因为同名 Header 可以重复，例如 Set-Cookie。
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    name: str
    value: str


class HttpRequestRecord(BaseModel):
    """已经脱敏的原始 HTTP Request 记录。"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    method: str
    url: str
    headers: list[HeaderEntry]
    body: WireBody


class HttpResponseRecord(BaseModel):
    """原始 HTTP Response 记录。"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    status_code: int
    reason_phrase: str
    http_version: str
    headers: list[HeaderEntry]
    body: WireBody


class HttpExchange(BaseModel):
    """一次完整 HTTP 请求—响应交换。"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    started_at: datetime
    elapsed_ms: float = Field(ge=0)

    request: HttpRequestRecord
    response: HttpResponseRecord

    @property
    def is_success(self) -> bool:
        """是否为 2xx 响应。"""

        return 200 <= self.response.status_code < 300


TransportFailureKind = Literal[
    "connect_timeout",
    "read_timeout",
    "write_timeout",
    "pool_timeout",
    "connect_error",
    "read_error",
    "write_error",
    "close_error",
    "local_protocol_error",
    "remote_protocol_error",
    "proxy_error",
    "unsupported_protocol",
    "decoding_error",
    "too_many_redirects",
    "invalid_url",
    "request_error",
]


class TransportFailureRecord(BaseModel):
    """请求未能形成完整 HTTP Exchange 时的结构化证据。"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    kind: TransportFailureKind
    message: str
    elapsed_ms: float = Field(ge=0)
    request: HttpRequestRecord