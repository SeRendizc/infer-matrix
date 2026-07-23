"""Tests for the incremental SSE wire decoder."""

import codecs

import pytest

from agent_eval_lab.transports import (
    SseDecoder,
    SseDecoderClosedError,
    SseIncompleteFrameError,
    SseUtf8DecodeError,
    decode_sse_chunks,
)


def test_decodes_basic_message_event() -> None:
    frames = decode_sse_chunks(
        [b"data: hello\n\n"]
    )

    assert len(frames) == 1

    frame = frames[0]

    assert frame.has_event
    assert frame.event is not None
    assert frame.event.event_type == "message"
    assert frame.event.data == "hello"
    assert frame.raw_text == "data: hello\n\n"


def test_joins_multiple_data_lines() -> None:
    frames = decode_sse_chunks(
        [
            b"data: first\n",
            b"data: second\n\n",
        ]
    )

    event = frames[0].event

    assert event is not None
    assert event.data == "first\nsecond"


def test_supports_event_id_and_retry() -> None:
    frames = decode_sse_chunks(
        [
            (
                b"event: tool_call\n"
                b"id: call-42\n"
                b"retry: 1500\n"
                b"data: {}\n\n"
                b"data: next\n\n"
            )
        ]
    )

    first = frames[0]
    second = frames[1]

    assert first.event is not None
    assert first.event.event_type == (
        "tool_call"
    )
    assert first.event.last_event_id == (
        "call-42"
    )
    assert first.id_updated
    assert first.retry_ms == 1500

    assert second.event is not None
    assert second.event.last_event_id == (
        "call-42"
    )


def test_preserves_comments_and_unknown_fields() -> None:
    frames = decode_sse_chunks(
        [
            (
                b": heartbeat\n"
                b"x-vendor: abc\n"
                b"data: ok\n\n"
            )
        ]
    )

    frame = frames[0]

    assert frame.comments == [" heartbeat"]

    vendor_field = next(
        field
        for field in frame.fields
        if field.name == "x-vendor"
    )

    assert vendor_field.value == "abc"

    assert frame.event is not None
    assert frame.event.data == "ok"


def test_accepts_arbitrary_byte_boundaries() -> None:
    payload = "data: 你好\r\n\r\n".encode(
        "utf-8"
    )

    chunks = [
        bytes([byte])
        for byte in payload
    ]

    frames = decode_sse_chunks(chunks)

    assert len(frames) == 1
    assert frames[0].event is not None
    assert frames[0].event.data == "你好"
    assert frames[0].raw_text == (
        "data: 你好\r\n\r\n"
    )


def test_supports_cr_lf_and_crlf() -> None:
    frames = decode_sse_chunks(
        [
            (
                b"data: one\r"
                b"\r"
                b"data: two\n"
                b"\n"
                b"data: three\r\n"
                b"\r\n"
            )
        ]
    )

    assert [
        frame.event.data
        for frame in frames
        if frame.event is not None
    ] == [
        "one",
        "two",
        "three",
    ]


def test_ignores_one_leading_utf8_bom() -> None:
    frames = decode_sse_chunks(
        [
            codecs.BOM_UTF8,
            b"data: hello\n\n",
        ]
    )

    assert frames[0].event is not None
    assert frames[0].event.data == "hello"
    assert not frames[0].raw_text.startswith(
        "\ufeff"
    )


def test_field_parsing_uses_first_colon_only() -> None:
    frames = decode_sse_chunks(
        [
            (
                b"data:  leading-space\n"
                b"data:value:with:colons\n\n"
            )
        ]
    )

    event = frames[0].event

    assert event is not None
    assert event.data == (
        " leading-space\n"
        "value:with:colons"
    )


def test_field_names_are_case_sensitive() -> None:
    frames = decode_sse_chunks(
        [
            (
                b"Data: ignored\n"
                b"data: accepted\n\n"
            )
        ]
    )

    event = frames[0].event

    assert event is not None
    assert event.data == "accepted"


def test_id_with_null_character_is_ignored() -> None:
    frames = decode_sse_chunks(
        [
            (
                b"id: valid\n"
                b"data: first\n\n"
                b"id: invalid\x00id\n"
                b"data: second\n\n"
            )
        ]
    )

    assert frames[0].event is not None
    assert frames[0].event.last_event_id == (
        "valid"
    )

    assert frames[1].event is not None
    assert frames[1].event.last_event_id == (
        "valid"
    )
    assert not frames[1].id_updated


def test_retry_requires_ascii_digits() -> None:
    decoder = SseDecoder()

    frames = decoder.feed(
        (
            "retry: 1000\n\n"
            "retry: ١٢\n\n"
        ).encode("utf-8")
    )

    frames.extend(decoder.finish())

    assert frames[0].retry_ms == 1000
    assert frames[1].retry_ms is None
    assert decoder.reconnection_time_ms == 1000


def test_done_sentinel_is_preserved() -> None:
    frames = decode_sse_chunks(
        [b"data: [DONE]\n\n"]
    )

    event = frames[0].event

    assert event is not None
    assert event.data == "[DONE]"
    assert event.is_done


def test_comment_only_frame_has_no_event() -> None:
    frames = decode_sse_chunks(
        [b": keep-alive\n\n"]
    )

    assert len(frames) == 1
    assert frames[0].comments == [
        " keep-alive"
    ]
    assert frames[0].event is None


def test_id_only_frame_updates_stream_state() -> None:
    frames = decode_sse_chunks(
        [
            (
                b"id: next-id\n\n"
                b"data: payload\n\n"
            )
        ]
    )

    assert frames[0].event is None
    assert frames[0].id_updated
    assert frames[0].last_event_id == (
        "next-id"
    )

    assert frames[1].event is not None
    assert (
        frames[1].event.last_event_id
        == "next-id"
    )


def test_incomplete_frame_raises_by_default() -> None:
    decoder = SseDecoder()

    assert decoder.feed(
        b"data: unfinished\n"
    ) == []

    with pytest.raises(
        SseIncompleteFrameError,
    ) as error_info:
        decoder.finish()

    assert "unfinished" in (
        error_info.value.partial_raw_text
    )


def test_incomplete_frame_can_be_discarded() -> None:
    decoder = SseDecoder()

    decoder.feed(
        b"data: unfinished\n"
    )

    frames = decoder.finish(
        require_complete_frame=False
    )

    assert frames == []
    assert decoder.is_closed


def test_invalid_utf8_is_rejected() -> None:
    decoder = SseDecoder()

    with pytest.raises(
        SseUtf8DecodeError
    ):
        decoder.feed(
            b"data: \xff\n\n"
        )


def test_feed_after_finish_is_rejected() -> None:
    decoder = SseDecoder()

    decoder.finish()

    with pytest.raises(
        SseDecoderClosedError
    ):
        decoder.feed(
            b"data: late\n\n"
        )