# Chat Completions Full-Body Streaming P0 Implementation Plan

> **Execution rule:** Follow TDD for every behavior: add one failing test, verify the failure reason, add the minimum implementation, then rerun the focused test.

**Goal:** Execute real `openai_compatible` Chat Completions cases with `features.streaming=true`, parse buffered SSE response bodies into chunks, and retain the sanitized `HttpExchange` as evidence.

**Boundary:** Reuse the existing synchronous HTTP transport and full response body. This milestone does not implement incremental delivery, frame timestamps, TTFT, ITL, Responses API, or a real vLLM smoke run.

**Compatibility:** Preserve all existing non-streaming behavior and all current in-progress protocol/report changes. Do not commit automatically.

---

## Task 1: Request and streaming protocol adapter

**Files:**
- Create: `tests/test_chat_completions_stream_protocol.py`
- Create: `src/infermatrix/protocols/chat_completions_stream.py`
- Modify: `src/infermatrix/protocols/chat_completions.py`
- Modify: `src/infermatrix/protocols/__init__.py`

1. Add a focused test proving a streaming case produces `"stream": true`.
2. Run `python -m pytest tests/test_chat_completions_stream_protocol.py -q` and verify it fails because the existing request adapter rejects streaming.
3. Change `build_chat_completions_request()` to serialize `case.features.streaming` while preserving the protocol-type guard.
4. Rerun the focused test and verify it passes.
5. Add tests for parsing two `data:` JSON events followed by `[DONE]`, excluding `[DONE]` from chunks.
6. Run the focused test and verify it fails because the streaming adapter does not exist.
7. Add a small streaming module with:
   - an immutable result model containing `chunks` and `observations`;
   - decode/shape error types that retain `HttpExchange`;
   - `parse_chat_completions_stream_response(exchange)` using the existing SSE decoder;
   - HTTP success validation, JSON-object validation, `choices: list` validation, and a non-empty chunk requirement.
8. Export the new public protocol symbols and rerun the focused tests.
9. Add and pass focused tests for invalid JSON retaining the exchange and missing `[DONE]` producing a non-fatal `missing_done` observation.

## Task 2: OpenAI-compatible streaming client

**Files:**
- Create: `tests/test_openai_compatible_stream_client.py`
- Modify: `src/infermatrix/clients/openai_compatible.py`

1. Add an `httpx.MockTransport` test for `client.stream_case(case)` proving:
   - the URL is `/chat/completions`;
   - the body contains `"stream": true`;
   - `Accept` is `text/event-stream`;
   - parsed chunks, observations, and the sanitized exchange are returned.
2. Run the focused test and verify it fails because `stream_case()` is absent.
3. Add an immutable streaming call result and the minimum `stream_case()` implementation, reusing backend validation, serialization, authentication, URL construction, and transport ownership.
4. Make header construction choose the `Accept` value from `case.features.streaming` without changing non-streaming behavior.
5. Rerun the focused streaming-client test and the existing client test file.

## Task 3: Runner integration

**Files:**
- Create: `tests/test_real_streaming_runner.py`
- Modify: `src/infermatrix/runner.py`

1. Add a runner test proving a real streaming case returns:
   - `response_type="chat_completion_chunks"`;
   - `response is None`;
   - parsed chunks;
   - the retained exchange;
   - protocol observations.
2. Run the focused test and verify it fails on the existing E-1D2 `NotImplementedError`.
3. Remove the early rejection and branch in `_execute_with_transport()` between `client.stream_case()` and `client.run_case()`.
4. Preserve the existing rule: injected transports are not closed; runner-owned transports are closed.
5. Rerun the focused runner test and existing runner tests.

## Task 4: Regression verification and milestone evidence

**Files:**
- Create: `.planning/ai-infra-dual-track/streaming_p0_completion_20260719.md`

1. Run `python -m pytest -q` from `D:\infermatrix`.
2. Run `python -m ruff check .` from `D:\infermatrix`.
3. Inspect `git diff --check` and `git status --short`.
4. Record only verified capabilities and exact test/lint results in the completion checkpoint.
5. Do not claim incremental streaming, TTFT/ITL, or real vLLM/SGLang evidence.
