"""Tests for InferMatrix raw HTTP transports."""

import asyncio

import httpx
import pytest

from urllib.parse import parse_qs, urlsplit
from infermatrix.cases import TimeoutConfig
from infermatrix.transports import (
    AsyncHttpxTransport,
    HttpStatusError,
    HttpTransportError,
    HttpxTransport,
    build_httpx_timeout,
    require_success,
)


def _timeout() -> TimeoutConfig:
    return TimeoutConfig(
        connect=1.0,
        read=2.0,
        write=3.0,
        pool=4.0,
    )


def test_timeout_config_maps_to_httpx() -> None:
    timeout = build_httpx_timeout(
        _timeout()
    )

    assert timeout.connect == 1.0
    assert timeout.read == 2.0
    assert timeout.write == 3.0
    assert timeout.pool == 4.0


def test_sync_transport_captures_exchange() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["authorization"] == (
            "Bearer real-secret"
        )
        assert request.content == b'{"model":"test"}'

        return httpx.Response(
            200,
            headers={
                "content-type": "application/json",
                "x-request-id": "req-001",
            },
            content=b'{"ok":true}',
        )

    with HttpxTransport(
        timeout=_timeout(),
        transport=httpx.MockTransport(handler),
    ) as transport:
        exchange = transport.request(
            method="POST",
            url=(
                "https://example.test/v1/test"
                "?access_token=secret-token"
            ),
            headers={
                "Authorization": (
                    "Bearer real-secret"
                ),
                "Content-Type": (
                    "application/json"
                ),
            },
            content=b'{"model":"test"}',
        )

    assert exchange.is_success
    assert exchange.response.status_code == 200
    assert exchange.response.body.to_bytes() == (
        b'{"ok":true}'
    )

    authorization = next(
        header
        for header in exchange.request.headers
        if header.name.lower()
        == "authorization"
    )

    assert authorization.value == "[REDACTED]"
    assert "secret-token" not in exchange.request.url

    query = parse_qs(urlsplit(exchange.request.url).query)

    assert query["access_token"] == ["[REDACTED]"]


def test_transport_preserves_binary_body() -> None:
    binary_data = b"\xff\x00\xfe"

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            content=binary_data,
        )

    with HttpxTransport(
        timeout=_timeout(),
        transport=httpx.MockTransport(handler),
    ) as transport:
        exchange = transport.request(
            method="GET",
            url="https://example.test/binary",
        )

    assert exchange.response.body.encoding == (
        "base64"
    )
    assert (
        exchange.response.body.to_bytes()
        == binary_data
    )


def test_transport_keeps_non_success_response() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            429,
            headers={
                "retry-after": "10",
            },
            json={
                "error": "rate_limit",
            },
        )

    with HttpxTransport(
        timeout=_timeout(),
        transport=httpx.MockTransport(handler),
    ) as transport:
        exchange = transport.request(
            method="POST",
            url="https://example.test/v1/test",
        )

    assert exchange.response.status_code == 429
    assert not exchange.is_success
    assert b"rate_limit" in (
        exchange.response.body.to_bytes()
    )


def test_require_success_raises_with_exchange() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            500,
            text="backend failed",
        )

    with HttpxTransport(
        timeout=_timeout(),
        transport=httpx.MockTransport(handler),
    ) as transport:
        exchange = transport.request(
            method="GET",
            url="https://example.test/failure",
        )

    with pytest.raises(
        HttpStatusError,
        match="500",
    ) as error_info:
        require_success(exchange)

    assert (
        error_info.value.exchange.response.body
        .to_bytes()
        == b"backend failed"
    )


@pytest.mark.parametrize(
    ("error_type", "expected_kind"),
    [
        (
            httpx.ConnectTimeout,
            "connect_timeout",
        ),
        (
            httpx.ReadTimeout,
            "read_timeout",
        ),
        (
            httpx.ConnectError,
            "connect_error",
        ),
        (
            httpx.RemoteProtocolError,
            "remote_protocol_error",
        ),
    ],
)
def test_transport_classifies_request_errors(
    error_type,
    expected_kind: str,
) -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise error_type(
            "simulated failure",
            request=request,
        )

    with HttpxTransport(
        timeout=_timeout(),
        transport=httpx.MockTransport(handler),
    ) as transport:
        with pytest.raises(
            HttpTransportError,
        ) as error_info:
            transport.request(
                method="POST",
                url=(
                    "https://example.test/test"
                    "?api_key=secret"
                ),
                headers={
                    "Authorization": "Bearer secret",
                },
            )

    failure = error_info.value.failure

    assert failure.kind == expected_kind
    assert "secret" not in failure.request.url

    authorization = next(
        header
        for header in failure.request.headers
        if header.name.lower()
        == "authorization"
    )

    assert authorization.value == "[REDACTED]"


def test_transport_does_not_retry_failure() -> None:
    call_count = 0

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal call_count
        call_count += 1

        raise httpx.ConnectError(
            "simulated failure",
            request=request,
        )

    with HttpxTransport(
        timeout=_timeout(),
        transport=httpx.MockTransport(handler),
    ) as transport:
        with pytest.raises(
            HttpTransportError
        ):
            transport.request(
                method="GET",
                url="https://example.test/test",
            )

    assert call_count == 1


def test_async_transport_captures_exchange() -> None:
    async def run_test() -> None:
        def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "result": "ok",
                },
            )

        async with AsyncHttpxTransport(
            timeout=_timeout(),
            transport=httpx.MockTransport(
                handler
            ),
        ) as transport:
            exchange = await transport.request(
                method="POST",
                url="https://example.test/test",
                content='{"input":"hello"}',
                headers={
                    "Content-Type": (
                        "application/json"
                    )
                },
            )

        assert exchange.is_success
        assert b'"result":"ok"' in (
            exchange.response.body.to_bytes()
        )

    asyncio.run(run_test())


def test_async_transport_classifies_timeout() -> None:
    async def run_test() -> None:
        def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            raise httpx.PoolTimeout(
                "pool unavailable",
                request=request,
            )

        async with AsyncHttpxTransport(
            timeout=_timeout(),
            transport=httpx.MockTransport(
                handler
            ),
        ) as transport:
            with pytest.raises(
                HttpTransportError,
            ) as error_info:
                await transport.request(
                    method="GET",
                    url=(
                        "https://example.test/test"
                    ),
                )

        assert (
            error_info.value.failure.kind
            == "pool_timeout"
        )

    asyncio.run(run_test())