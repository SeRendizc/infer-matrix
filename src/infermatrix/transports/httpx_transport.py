"""HTTPX-backed raw HTTP transports."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from time import perf_counter

import httpx

from infermatrix.cases import TimeoutConfig
from infermatrix.transports.errors import (
    HttpTransportError,
)
from infermatrix.transports.models import (
    HttpExchange,
    HttpRequestRecord,
    HttpResponseRecord,
    TransportFailureKind,
    TransportFailureRecord,
    WireBody,
)
from infermatrix.transports.redaction import (
    redact_header_items,
    redact_url,
)


def build_httpx_timeout(
    config: TimeoutConfig,
) -> httpx.Timeout:
    """将领域 TimeoutConfig 转换成 HTTPX Timeout。"""

    return httpx.Timeout(
        timeout=None,
        connect=config.connect,
        read=config.read,
        write=config.write,
        pool=config.pool,
    )


def _content_to_bytes(
    content: bytes | str | None,
) -> bytes:
    """把 Transport 输入统一转换成 bytes。"""

    if content is None:
        return b""

    if isinstance(content, str):
        return content.encode("utf-8")

    return content


def _capture_request(
    request: httpx.Request,
) -> HttpRequestRecord:
    """捕获并脱敏已经构造完成的 HTTPX Request。"""

    content_type = request.headers.get(
        "content-type"
    )

    return HttpRequestRecord(
        method=request.method,
        url=redact_url(str(request.url)),
        headers=redact_header_items(
            request.headers.multi_items()
        ),
        body=WireBody.from_bytes(
            request.content,
            content_type=content_type,
        ),
    )


def _capture_input_request(
    *,
    method: str,
    url: str,
    headers: Mapping[str, str] | None,
    content: bytes | str | None,
) -> HttpRequestRecord:
    """在 HTTPX 无法构造 Request 时保存调用输入。"""

    header_items = list(
        (headers or {}).items()
    )

    content_type = next(
        (
            value
            for name, value in header_items
            if name.lower() == "content-type"
        ),
        None,
    )

    return HttpRequestRecord(
        method=method.upper(),
        url=redact_url(url),
        headers=redact_header_items(
            header_items
        ),
        body=WireBody.from_bytes(
            _content_to_bytes(content),
            content_type=content_type,
        ),
    )


def _capture_response(
    response: httpx.Response,
) -> HttpResponseRecord:
    """捕获完整 HTTP Response。"""

    raw_http_version = response.extensions.get(
        "http_version",
        b"HTTP/1.1",
    )

    if isinstance(raw_http_version, bytes):
        http_version = raw_http_version.decode(
            "ascii",
            errors="replace",
        )
    else:
        http_version = str(raw_http_version)

    return HttpResponseRecord(
        status_code=response.status_code,
        reason_phrase=response.reason_phrase,
        http_version=http_version,
        headers=redact_header_items(
            response.headers.multi_items()
        ),
        body=WireBody.from_bytes(
            response.content,
            content_type=response.headers.get(
                "content-type"
            ),
        ),
    )


def _classify_request_error(
    error: httpx.RequestError,
) -> TransportFailureKind:
    """把 HTTPX 异常转换成稳定的领域错误分类。"""

    if isinstance(error, httpx.ConnectTimeout):
        return "connect_timeout"

    if isinstance(error, httpx.ReadTimeout):
        return "read_timeout"

    if isinstance(error, httpx.WriteTimeout):
        return "write_timeout"

    if isinstance(error, httpx.PoolTimeout):
        return "pool_timeout"

    if isinstance(error, httpx.ConnectError):
        return "connect_error"

    if isinstance(error, httpx.ReadError):
        return "read_error"

    if isinstance(error, httpx.WriteError):
        return "write_error"

    if isinstance(error, httpx.CloseError):
        return "close_error"

    if isinstance(error, httpx.LocalProtocolError):
        return "local_protocol_error"

    if isinstance(error, httpx.RemoteProtocolError):
        return "remote_protocol_error"

    if isinstance(error, httpx.ProxyError):
        return "proxy_error"

    if isinstance(error, httpx.UnsupportedProtocol):
        return "unsupported_protocol"

    if isinstance(error, httpx.DecodingError):
        return "decoding_error"

    if isinstance(error, httpx.TooManyRedirects):
        return "too_many_redirects"

    return "request_error"


def _safe_error_message(
    error: Exception,
    *,
    original_url: str,
    redacted_url_value: str,
) -> str:
    """避免错误信息重新泄漏 URL 中的敏感值。"""

    return str(error).replace(
        original_url,
        redacted_url_value,
    )


def _raise_transport_error(
    *,
    error: Exception,
    kind: TransportFailureKind,
    request: HttpRequestRecord,
    started: float,
    original_url: str,
) -> None:
    """构造统一 Transport 错误。"""

    failure = TransportFailureRecord(
        kind=kind,
        message=_safe_error_message(
            error,
            original_url=original_url,
            redacted_url_value=request.url,
        ),
        elapsed_ms=round(
            (perf_counter() - started) * 1000,
            3,
        ),
        request=request,
    )

    raise HttpTransportError(
        failure
    ) from error


class HttpxTransport:
    """同步、连接池复用的 HTTPX Transport。"""

    def __init__(
        self,
        *,
        timeout: TimeoutConfig,
        transport: httpx.BaseTransport | None = None,
        trust_env: bool = False,
    ) -> None:
        actual_transport = (
            transport
            if transport is not None
            else httpx.HTTPTransport(
                retries=0
            )
        )

        self._client = httpx.Client(
            timeout=build_httpx_timeout(timeout),
            transport=actual_transport,
            follow_redirects=False,
            trust_env=trust_env,
        )

    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str] | None = None,
        content: bytes | str | None = None,
    ) -> HttpExchange:
        """发送原始同步 HTTP 请求。"""

        started = perf_counter()
        started_at = datetime.now(timezone.utc)

        fallback_request = _capture_input_request(
            method=method,
            url=url,
            headers=headers,
            content=content,
        )

        try:
            request = self._client.build_request(
                method=method,
                url=url,
                headers=headers,
                content=content,
            )

            captured_request = _capture_request(
                request
            )

            response = self._client.send(
                request
            )

        except httpx.InvalidURL as error:
            _raise_transport_error(
                error=error,
                kind="invalid_url",
                request=fallback_request,
                started=started,
                original_url=url,
            )

        except httpx.RequestError as error:
            error_request = (
                _capture_request(error.request)
                if error.request is not None
                else fallback_request
            )

            _raise_transport_error(
                error=error,
                kind=_classify_request_error(error),
                request=error_request,
                started=started,
                original_url=url,
            )

        return HttpExchange(
            started_at=started_at,
            elapsed_ms=round(
                (perf_counter() - started) * 1000,
                3,
            ),
            request=captured_request,
            response=_capture_response(response),
        )

    def close(self) -> None:
        """关闭连接池。"""

        self._client.close()

    def __enter__(self) -> "HttpxTransport":
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()


class AsyncHttpxTransport:
    """异步、连接池复用的 HTTPX Transport。"""

    def __init__(
        self,
        *,
        timeout: TimeoutConfig,
        transport: (
            httpx.AsyncBaseTransport
            | None
        ) = None,
        trust_env: bool = False,
    ) -> None:
        actual_transport = (
            transport
            if transport is not None
            else httpx.AsyncHTTPTransport(
                retries=0
            )
        )

        self._client = httpx.AsyncClient(
            timeout=build_httpx_timeout(timeout),
            transport=actual_transport,
            follow_redirects=False,
            trust_env=trust_env,
        )

    async def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str] | None = None,
        content: bytes | str | None = None,
    ) -> HttpExchange:
        """发送原始异步 HTTP 请求。"""

        started = perf_counter()
        started_at = datetime.now(timezone.utc)

        fallback_request = _capture_input_request(
            method=method,
            url=url,
            headers=headers,
            content=content,
        )

        try:
            request = self._client.build_request(
                method=method,
                url=url,
                headers=headers,
                content=content,
            )

            captured_request = _capture_request(
                request
            )

            response = await self._client.send(
                request
            )

        except httpx.InvalidURL as error:
            _raise_transport_error(
                error=error,
                kind="invalid_url",
                request=fallback_request,
                started=started,
                original_url=url,
            )

        except httpx.RequestError as error:
            error_request = (
                _capture_request(error.request)
                if error.request is not None
                else fallback_request
            )

            _raise_transport_error(
                error=error,
                kind=_classify_request_error(error),
                request=error_request,
                started=started,
                original_url=url,
            )

        return HttpExchange(
            started_at=started_at,
            elapsed_ms=round(
                (perf_counter() - started) * 1000,
                3,
            ),
            request=captured_request,
            response=_capture_response(response),
        )

    async def aclose(self) -> None:
        """关闭异步连接池。"""

        await self._client.aclose()

    async def __aenter__(
        self,
    ) -> "AsyncHttpxTransport":
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        await self.aclose()