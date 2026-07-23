# Chat Completions Full-Body Streaming P0 Design

> Historical note: this document predates the rename from InferMatrix to Agent Eval Lab.

## Goal

让真实 `openai_compatible` case 在 `features.streaming=true` 时完成最小协议闭环：发送 `stream=true` 请求，解析完整 HTTP response body 中的 SSE data events，输出 Chat Completions chunks，并保留脱敏后的 `HttpExchange`。

## Boundary

P0 复用现有同步 `SyncHttpTransport.request()`。Transport 仍在 HTTP 完成后一次性返回完整 body；协议层随后调用现有 SSE decoder。该设计证明真实 streaming 协议可执行和可取证，但不记录 byte/event 到达时间，不计算或声称 TTFT、ITL。

`RunResult` 继续使用现有字段：

- `response_type="chat_completion_chunks"`
- `chunks=list[dict[str, Any]]`
- `http_exchange=HttpExchange`
- `protocol_observations=list[ProtocolObservation]`

不新增 `sse_frames` 字段。原始 SSE wire data 由 `http_exchange.response.body` 完整保存。

## Components

### Request adapter

`build_chat_completions_request(case)` 不再拒绝 streaming case，而是把 `case.features.streaming` 写入 `stream`。非流式行为保持不变。

### Client

`OpenAICompatibleClient.stream_case(case)` 复用现有 backend 校验、序列化、鉴权和 URL 构造。Streaming 请求的 `Accept` 为 `text/event-stream`；非流式仍为 `application/json`。

Client 使用注入的同步 transport 获得 `HttpExchange`，再交给 streaming response adapter，返回 exchange、chunks 和非致命 observations。

### Streaming response adapter

Adapter 负责：

1. 要求 HTTP 状态成功；
2. 从 `WireBody` 取得原始 bytes；
3. 使用现有 `decode_sse_chunks()` 解码 SSE frames；
4. 忽略没有 event 的 comment/id/retry-only frames；
5. 识别 `[DONE]`，不把它加入 chunks；
6. 将其他 event data 解码为 JSON object；
7. 要求每个 chunk 的 `choices` 为 list；
8. 返回非空 chunks。

P0 不合并 content、不解释 tool calls，也不验证 chunk order/finish_reason/usage；这些由现有 stream parser 与后续 invariants 负责。

### Runner

`run_case()` 不再拒绝真实 streaming。它沿用现有 transport ownership：外部注入 transport 不关闭；内部创建的 `HttpxTransport` 在调用结束后关闭。

Runner 根据 `case.features.streaming` 调用 `client.stream_case()` 或 `client.run_case()`，并构造相应 `RunResult`。

## Error handling

- HTTP 非 2xx：沿用携带 exchange 的 `HttpStatusError`。
- SSE UTF-8/frame 解码失败：抛出携带 exchange 的 streaming response error。
- event data 不是合法 JSON object、缺少 list 类型 `choices` 或没有任何 chunk：抛出携带 exchange 的 streaming response error。
- `[DONE]` 是否缺失在 P0 中记录为 `missing_done` observation，而不阻断兼容 backend；严格 lifecycle invariant 留到后续阶段。

错误不得丢失原始 `HttpExchange`，以便 pipeline/report 保存失败证据。

## Test strategy

按 TDD 分三层推进：

1. Protocol RED：streaming case 生成 `stream=true`；SSE body 解析两个 JSON chunks、忽略 `[DONE]`。
2. Client RED：通过 `httpx.MockTransport` 验证 request headers/body，并返回 chunks、exchange、observations。
3. Runner RED：真实 streaming case 返回 `chat_completion_chunks`、chunks 和脱敏 exchange，不再抛出 E-1D2 `NotImplementedError`。

补充错误测试覆盖 invalid JSON event 和 missing `[DONE]` observation。完成后运行 InferMatrix 全量 pytest 与 Ruff。

## Non-goals

- 增量 transport/generator API；
- TTFT、ITL 或 frame arrival timestamps；
- Responses API；
- streaming tool-call normalization；
- report schema 大改；
- vLLM/SGLang 真实 smoke，本 P0 通过后单独执行。
