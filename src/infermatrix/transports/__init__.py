"""Protocol-independent HTTP transports."""

from infermatrix.transports.base import (
    AsyncHttpTransport,
    SyncHttpTransport,
)
from infermatrix.transports.errors import (
    HttpStatusError,
    HttpTransportError,
    require_success,
)
from infermatrix.transports.httpx_transport import (
    AsyncHttpxTransport,
    HttpxTransport,
    build_httpx_timeout,
)
from infermatrix.transports.models import (
    HeaderEntry,
    HttpExchange,
    HttpRequestRecord,
    HttpResponseRecord,
    TransportFailureRecord,
    WireBody,
)

__all__ = [
    "SyncHttpTransport",
    "AsyncHttpTransport",
    "HttpxTransport",
    "AsyncHttpxTransport",
    "build_httpx_timeout",
    "HttpTransportError",
    "HttpStatusError",
    "require_success",
    "WireBody",
    "HeaderEntry",
    "HttpRequestRecord",
    "HttpResponseRecord",
    "HttpExchange",
    "TransportFailureRecord",
]