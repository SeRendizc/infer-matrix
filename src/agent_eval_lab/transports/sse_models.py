"""Typed models for Server-Sent Events wire data.

这些模型只表达 SSE Wire 语义，不理解 Chat Completions
或 Responses API 的业务字段。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SseField(BaseModel):
    """一个非注释 SSE 字段。

    raw_line 保留去掉行结束符后的原始行。
    name/value 保存按照 SSE 规则解析后的结果。
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    name: str
    value: str
    raw_line: str


class SseEvent(BaseModel):
    """由包含 data 字段的 SSE Frame 产生的事件。"""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    event_type: str
    data: str
    last_event_id: str
    is_done: bool = False


class SseFrame(BaseModel):
    """一个由空行终止的完整 SSE Frame。

    Frame 不一定产生 Event。

    例如：

    - 只有注释的 Frame
    - 只有 id/retry 的 Frame
    - 完全为空的 Frame

    都会被保留为 SseFrame，但 event 为 None。
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    raw_text: str
    fields: list[SseField] = Field(
        default_factory=list
    )
    comments: list[str] = Field(
        default_factory=list
    )

    event: SseEvent | None = None

    last_event_id: str = ""
    id_updated: bool = False
    retry_ms: int | None = Field(
        default=None,
        ge=0,
    )

    @property
    def has_event(self) -> bool:
        """该 Frame 是否真正产生一个 SSE Event。"""

        return self.event is not None