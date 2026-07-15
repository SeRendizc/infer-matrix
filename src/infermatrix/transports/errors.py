"""Transport-level errors for InferMatrix."""

from __future__ import annotations

from infermatrix.transports.models import (
    HttpExchange,
    TransportFailureRecord,
)


class HttpTransportError(RuntimeError):
    """HTTP 请求未能形成完整响应时抛出。

    failure 中保留：

    - 错误分类
    - 脱敏后的请求
    - 已消耗时间
    - 安全错误信息
    """

    def __init__(
        self,
        failure: TransportFailureRecord,
    ) -> None:
        self.failure = failure

        super().__init__(
            f"{failure.kind}: {failure.message}"
        )


class HttpStatusError(RuntimeError):
    """HTTP 响应存在，但状态码不满足成功策略。"""

    def __init__(
        self,
        exchange: HttpExchange,
    ) -> None:
        self.exchange = exchange

        super().__init__(
            "HTTP request returned status "
            f"{exchange.response.status_code} "
            f"{exchange.response.reason_phrase}."
        )


def require_success(
    exchange: HttpExchange,
) -> HttpExchange:
    """要求 HTTP Exchange 为 2xx。

    Raw Transport 本身不会丢弃 4xx/5xx。
    调用方需要时再显式调用本函数。
    """

    if not exchange.is_success:
        raise HttpStatusError(exchange)

    return exchange


class SseDecodeError(ValueError):
    """SSE Wire 数据无法被正确解码。"""


class SseUtf8DecodeError(SseDecodeError):
    """SSE Stream 包含非法 UTF-8。"""

    def __init__(
        self,
        *,
        start: int,
        end: int,
        reason: str,
    ) -> None:
        self.start = start
        self.end = end
        self.reason = reason

        super().__init__(
            "SSE stream contains invalid UTF-8: "
            f"bytes {start}:{end}, {reason}."
        )


class SseIncompleteFrameError(SseDecodeError):
    """连接结束时仍存在未由空行终止的 SSE Frame。"""

    def __init__(
        self,
        partial_raw_text: str,
    ) -> None:
        self.partial_raw_text = partial_raw_text

        super().__init__(
            "SSE stream ended before the current "
            "frame was terminated by a blank line."
        )


class SseDecoderClosedError(SseDecodeError):
    """已完成的 Decoder 又收到了新数据。"""

    def __init__(self) -> None:
        super().__init__(
            "SSE decoder has already been finalized."
        )