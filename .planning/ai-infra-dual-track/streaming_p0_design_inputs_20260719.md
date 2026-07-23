# Streaming P0 Design Inputs

## Live repo evidence

- Branch: `phase-e1d`.
- Fresh baseline: `149 passed`; Ruff clean.
- Existing dirty changes are concentrated in protocol error evidence, pipeline failure preservation, reports, and `examples/real_chat_smoke.yaml`.
- `runner.run_case()` explicitly raises `NotImplementedError` for real OpenAI-compatible streaming.
- `OpenAICompatibleClient.run_case()` only supports non-streaming request/response.
- `build_chat_completions_request()` currently rejects streaming cases and hardcodes `stream=False`.
- Incremental SSE wire decoder and streaming chunk parser already exist and have tests.

## P0 design boundary

- Use the existing synchronous `request()` transport and its captured full response body.
- Decode the complete SSE body after HTTP completion; parse JSON data events into Chat Completion chunks; recognize and exclude `[DONE]` from chunks.
- Preserve the redacted `HttpExchange` as raw wire evidence.
- Return `RunResult(response_type="chat_completion_chunks", chunks=...)` for real streaming.
- Do not claim TTFT/ITL or incremental arrival timing in P0; a future transport P1 must expose byte/event arrival timestamps.

## Non-goals

- No Responses API.
- No streaming tool-call normalization.
- No asynchronous generator API.
- No broad report schema refactor beyond what the P0 result requires.
