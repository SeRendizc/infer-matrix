"""Sensitive HTTP metadata redaction."""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

from agent_eval_lab.transports.models import (
    HeaderEntry,
)


REDACTED_VALUE = "[REDACTED]"

SENSITIVE_HEADER_NAMES = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
    }
)

SENSITIVE_QUERY_NAMES = frozenset(
    {
        "api_key",
        "apikey",
        "access_token",
        "token",
        "key",
    }
)


def redact_header_items(
    items: Iterable[tuple[str, str]],
) -> list[HeaderEntry]:
    """对 Header 名称执行大小写不敏感的脱敏。"""

    redacted: list[HeaderEntry] = []

    for name, value in items:
        safe_value = (
            REDACTED_VALUE
            if name.lower() in SENSITIVE_HEADER_NAMES
            else value
        )

        redacted.append(
            HeaderEntry(
                name=name,
                value=safe_value,
            )
        )

    return redacted


def redact_url(url: str) -> str:
    """脱敏 URL Query 中常见的密钥参数。"""

    parts = urlsplit(url)

    query_items = parse_qsl(
        parts.query,
        keep_blank_values=True,
    )

    safe_query_items = [
        (
            name,
            (
                REDACTED_VALUE
                if name.lower()
                in SENSITIVE_QUERY_NAMES
                else value
            ),
        )
        for name, value in query_items
    ]

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(safe_query_items),
            parts.fragment,
        )
    )