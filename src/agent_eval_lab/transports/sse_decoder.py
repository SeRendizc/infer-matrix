"""Incremental UTF-8 Server-Sent Events decoder."""

from __future__ import annotations

import codecs
from collections.abc import Iterable

from agent_eval_lab.transports.errors import (
    SseDecoderClosedError,
    SseIncompleteFrameError,
    SseUtf8DecodeError,
)
from agent_eval_lab.transports.sse_models import (
    SseEvent,
    SseField,
    SseFrame,
)


class SseDecoder:
    """把任意边界的 byte chunks 解码成完整 SSE Frames。

    网络 Chunk 边界与以下边界没有必然关系：

    - UTF-8 字符边界
    - SSE 行边界
    - SSE Frame 边界
    - JSON 文本边界

    因此 Decoder 必须保持跨 feed() 调用的内部状态。
    """

    def __init__(self) -> None:
        # utf-8-sig 会且只会去掉流开头的 UTF-8 BOM。
        self._utf8_decoder = codecs.getincrementaldecoder(
            "utf-8-sig"
        )(errors="strict")

        self._text_buffer = ""
        self._closed = False

        self._frame_raw_parts: list[str] = []
        self._frame_fields: list[SseField] = []
        self._frame_comments: list[str] = []
        self._data_lines: list[str] = []

        self._event_type_buffer = ""
        self._last_event_id = ""
        self._reconnection_time_ms: int | None = None

        self._frame_id_updated = False
        self._frame_retry_ms: int | None = None

    @property
    def last_event_id(self) -> str:
        """当前持久化的 Last Event ID。"""

        return self._last_event_id

    @property
    def reconnection_time_ms(self) -> int | None:
        """最近一次有效 retry 字段设置的重连时间。"""

        return self._reconnection_time_ms

    @property
    def is_closed(self) -> bool:
        """Decoder 是否已经执行 finish()。"""

        return self._closed

    def feed(
        self,
        chunk: bytes,
    ) -> list[SseFrame]:
        """输入一段原始网络 bytes。

        一个 Chunk 可以：

        - 包含多个 Frame
        - 只包含半行
        - 在 UTF-8 多字节字符中间结束
        - 在 CRLF 的 CR 与 LF 之间结束
        """

        self._ensure_open()

        if not isinstance(chunk, bytes):
            raise TypeError(
                "SseDecoder.feed() requires bytes."
            )

        if not chunk:
            return []

        try:
            decoded = self._utf8_decoder.decode(
                chunk,
                final=False,
            )
        except UnicodeDecodeError as error:
            self._closed = True

            raise SseUtf8DecodeError(
                start=error.start,
                end=error.end,
                reason=error.reason,
            ) from error

        self._text_buffer += decoded

        return self._drain_complete_lines(
            final=False
        )

    def finish(
        self,
        *,
        require_complete_frame: bool = True,
    ) -> list[SseFrame]:
        """通知 Decoder：网络流已经结束。

        标准 SSE 行为会丢弃没有最终空行的未完整事件。

        Agent Eval Lab 默认使用更严格的 Evidence 模式：
        检测到未完整 Frame 时抛出异常，避免悄悄丢失数据。

        将 require_complete_frame 设为 False，可使用标准的
        “丢弃未完整 Frame”行为。
        """

        self._ensure_open()

        frames: list[SseFrame] = []

        try:
            self._text_buffer += (
                self._utf8_decoder.decode(
                    b"",
                    final=True,
                )
            )
        except UnicodeDecodeError as error:
            self._closed = True

            raise SseUtf8DecodeError(
                start=error.start,
                end=error.end,
                reason=error.reason,
            ) from error

        frames.extend(
            self._drain_complete_lines(
                final=True
            )
        )

        partial_raw_text = (
            "".join(self._frame_raw_parts)
            + self._text_buffer
        )

        has_incomplete_frame = bool(
            partial_raw_text
        )

        self._closed = True

        if (
            has_incomplete_frame
            and require_complete_frame
        ):
            raise SseIncompleteFrameError(
                partial_raw_text
            )

        # 标准 SSE EOF 行为：丢弃未完整数据。
        self._text_buffer = ""
        self._reset_frame_state()

        return frames

    def _ensure_open(self) -> None:
        if self._closed:
            raise SseDecoderClosedError()

    def _drain_complete_lines(
        self,
        *,
        final: bool,
    ) -> list[SseFrame]:
        """处理当前 Buffer 中所有完整 SSE 行。"""

        frames: list[SseFrame] = []

        while True:
            line_result = self._pop_complete_line(
                final=final
            )

            if line_result is None:
                break

            line, line_ending = line_result

            frame = self._process_line(
                line=line,
                line_ending=line_ending,
            )

            if frame is not None:
                frames.append(frame)

        return frames

    def _pop_complete_line(
        self,
        *,
        final: bool,
    ) -> tuple[str, str] | None:
        """弹出一个完整行，并保留原始换行符。"""

        for index, character in enumerate(
            self._text_buffer
        ):
            if character == "\n":
                line = self._text_buffer[:index]
                line_ending = "\n"

                self._text_buffer = (
                    self._text_buffer[index + 1 :]
                )

                return line, line_ending

            if character == "\r":
                # Chunk 可能刚好结束在 CR，下一 Chunk
                # 的第一个字符可能是 LF。
                if (
                    index + 1
                    == len(self._text_buffer)
                    and not final
                ):
                    return None

                if (
                    index + 1
                    < len(self._text_buffer)
                    and self._text_buffer[index + 1]
                    == "\n"
                ):
                    line = self._text_buffer[:index]
                    line_ending = "\r\n"

                    self._text_buffer = (
                        self._text_buffer[index + 2 :]
                    )

                    return line, line_ending

                line = self._text_buffer[:index]
                line_ending = "\r"

                self._text_buffer = (
                    self._text_buffer[index + 1 :]
                )

                return line, line_ending

        return None

    def _process_line(
        self,
        *,
        line: str,
        line_ending: str,
    ) -> SseFrame | None:
        """按照 SSE 字段规则处理一行。"""

        self._frame_raw_parts.append(
            line + line_ending
        )

        # 空行结束当前 Frame。
        if line == "":
            return self._dispatch_frame()

        # 以冒号开头的是注释。
        if line.startswith(":"):
            self._frame_comments.append(
                line[1:]
            )
            return None

        field_name: str
        field_value: str

        if ":" in line:
            field_name, field_value = line.split(
                ":",
                maxsplit=1,
            )

            # 标准只移除冒号后的一个空格。
            if field_value.startswith(" "):
                field_value = field_value[1:]
        else:
            field_name = line
            field_value = ""

        self._frame_fields.append(
            SseField(
                name=field_name,
                value=field_value,
                raw_line=line,
            )
        )

        self._process_field(
            name=field_name,
            value=field_value,
        )

        return None

    def _process_field(
        self,
        *,
        name: str,
        value: str,
    ) -> None:
        """应用标准 SSE 字段语义。

        字段名称大小写敏感：
        data 与 Data 不是同一个字段。
        """

        if name == "event":
            self._event_type_buffer = value
            return

        if name == "data":
            self._data_lines.append(value)
            return

        if name == "id":
            if "\x00" not in value:
                self._last_event_id = value
                self._frame_id_updated = True
            return

        if name == "retry":
            if self._contains_only_ascii_digits(
                value
            ):
                retry_ms = int(value)

                self._reconnection_time_ms = (
                    retry_ms
                )
                self._frame_retry_ms = retry_ms

    def _dispatch_frame(self) -> SseFrame:
        """结束当前 Frame，并在存在 data 字段时生成 Event。"""

        event: SseEvent | None = None

        # 即使 data 值为空，只要出现过 data 字段，
        # 标准仍会生成 data="" 的事件。
        if self._data_lines:
            data = "\n".join(
                self._data_lines
            )

            event_type = (
                self._event_type_buffer
                or "message"
            )

            event = SseEvent(
                event_type=event_type,
                data=data,
                last_event_id=(
                    self._last_event_id
                ),
                is_done=data == "[DONE]",
            )

        frame = SseFrame(
            raw_text="".join(
                self._frame_raw_parts
            ),
            fields=list(
                self._frame_fields
            ),
            comments=list(
                self._frame_comments
            ),
            event=event,
            last_event_id=(
                self._last_event_id
            ),
            id_updated=(
                self._frame_id_updated
            ),
            retry_ms=self._frame_retry_ms,
        )

        self._reset_frame_state()

        return frame

    def _reset_frame_state(self) -> None:
        """重置只属于一个 Frame 的状态。

        Last Event ID 与 Reconnection Time 是流级状态，
        因此不会在这里重置。
        """

        self._frame_raw_parts = []
        self._frame_fields = []
        self._frame_comments = []
        self._data_lines = []

        self._event_type_buffer = ""
        self._frame_id_updated = False
        self._frame_retry_ms = None

    @staticmethod
    def _contains_only_ascii_digits(
        value: str,
    ) -> bool:
        """retry 只接受非空 ASCII 十进制数字。"""

        return bool(value) and all(
            "0" <= character <= "9"
            for character in value
        )


def decode_sse_chunks(
    chunks: Iterable[bytes],
    *,
    require_complete_frame: bool = True,
) -> list[SseFrame]:
    """一次性解码一组 byte chunks。"""

    decoder = SseDecoder()
    frames: list[SseFrame] = []

    for chunk in chunks:
        frames.extend(
            decoder.feed(chunk)
        )

    frames.extend(
        decoder.finish(
            require_complete_frame=(
                require_complete_frame
            )
        )
    )

    return frames