"""Tests for OpenAI-compatible streaming chunk parser."""

import pytest

from infermatrix.cases import load_case
from infermatrix.clients.mock_openai import MockOpenAIClient
from infermatrix.parsers.stream_parser import (
    ParsedStreamMessage,
    StreamParseError,
    parse_streaming_chunks,
)


def _streaming_chunks():
    """构造一组稳定的 mock streaming chunks。

    这里复用 B-2 已经实现的 MockOpenAIClient.stream_case()。

    这样测试的意义更强：
    - B-2 负责生成 streaming chunks
    - C-2 负责解析 streaming chunks

    如果这个测试通过，就说明：
    B-2 的 mock streaming output
    可以被 C-2 的 stream parser 正确理解。
    """

    case = load_case("examples/streaming_json.yaml")
    chunks = MockOpenAIClient().stream_case(case)
    return case, chunks


def test_parse_mock_streaming_chunks() -> None:
    """parser 应该能解析 mock backend 生成的 streaming chunks。"""

    case, chunks = _streaming_chunks()

    parsed = parse_streaming_chunks(chunks)

    assert isinstance(parsed, ParsedStreamMessage)
    assert parsed.model == case.model
    assert parsed.choice_index == 0
    assert parsed.role == "assistant"
    assert parsed.finish_reason == "stop"

    assert parsed.content_chunks == [
        '{"status"',
        ': "ok"',
        ', "answer"',
        ': "InferMatrix streaming mock"',
        "}",
    ]

    assert (
        parsed.merged_content
        == '{"status": "ok", "answer": "InferMatrix streaming mock"}'
    )


def test_parse_streaming_chunks_rejects_empty_chunks() -> None:
    """chunks 是空列表时，应该明确失败。"""

    with pytest.raises(StreamParseError, match="must not be empty"):
        parse_streaming_chunks([])


def test_parse_streaming_chunks_rejects_missing_choices() -> None:
    """chunk 缺少 choices 时，应该明确失败。"""

    chunks = [
        {
            "id": "chatcmpl-mock-stream-broken",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "mock-model",
        }
    ]

    with pytest.raises(StreamParseError, match="choices"):
        parse_streaming_chunks(chunks)


def test_parse_streaming_chunks_rejects_empty_choices() -> None:
    """choices 是空列表时，应该明确失败。"""

    chunks = [
        {
            "id": "chatcmpl-mock-stream-broken",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "mock-model",
            "choices": [],
        }
    ]

    with pytest.raises(StreamParseError, match="must not be empty"):
        parse_streaming_chunks(chunks)


def test_parse_streaming_chunks_rejects_invalid_delta() -> None:
    """delta 不是 object 时，应该明确失败。"""

    chunks = [
        {
            "id": "chatcmpl-mock-stream-broken",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "delta": "not-an-object",
                    "finish_reason": None,
                }
            ],
        }
    ]

    with pytest.raises(StreamParseError, match="delta"):
        parse_streaming_chunks(chunks)


def test_parse_streaming_chunks_rejects_missing_assistant_role() -> None:
    """没有任何 chunk 提供 assistant role 时，应该明确失败。"""

    chunks = [
        {
            "id": "chatcmpl-mock-stream-broken",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": "hello",
                    },
                    "finish_reason": None,
                }
            ],
        },
        {
            "id": "chatcmpl-mock-stream-broken",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
        },
    ]

    with pytest.raises(StreamParseError, match="assistant role"):
        parse_streaming_chunks(chunks)


def test_parse_streaming_chunks_rejects_missing_content() -> None:
    """没有任何 content chunk 时，应该明确失败。"""

    chunks = [
        {
            "id": "chatcmpl-mock-stream-broken",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                    },
                    "finish_reason": None,
                }
            ],
        },
        {
            "id": "chatcmpl-mock-stream-broken",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
        },
    ]

    with pytest.raises(StreamParseError, match="content chunk"):
        parse_streaming_chunks(chunks)


def test_parse_streaming_chunks_rejects_missing_finish_reason() -> None:
    """没有 finish_reason 时，应该明确失败。"""

    chunks = [
        {
            "id": "chatcmpl-mock-stream-broken",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "role": "assistant",
                    },
                    "finish_reason": None,
                }
            ],
        },
        {
            "id": "chatcmpl-mock-stream-broken",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": "hello",
                    },
                    "finish_reason": None,
                }
            ],
        },
    ]

    with pytest.raises(StreamParseError, match="finish_reason"):
        parse_streaming_chunks(chunks)