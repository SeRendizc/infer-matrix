# InferMatrix Streaming P0 Completion Checkpoint

Date: 2026-07-19

## Verified capability

- Real `openai_compatible` Chat Completions cases can send `stream=true`.
- The client requests `text/event-stream` and preserves the sanitized `HttpExchange`.
- The protocol adapter decodes the complete buffered HTTP response body with the existing SSE decoder.
- JSON chunk objects are returned through `RunResult.chunks` with `response_type="chat_completion_chunks"`.
- `[DONE]` is excluded from chunks; a missing sentinel creates a non-fatal `missing_done` observation.
- Invalid SSE/JSON/shape errors retain the originating `HttpExchange`.
- Existing non-streaming execution remains covered by regression tests.

## Fresh verification

- `python -m pytest -q`: `154 passed in 1.37s`
- `python -m ruff check .`: `All checks passed!`
- `git diff --check`: exit code 0; only a line-ending warning for `runner.py`

## Explicit non-claims

- This is buffered full-body SSE parsing, not incremental token delivery.
- No byte/event arrival timestamps are captured.
- No TTFT or ITL metrics are produced.
- No real vLLM or SGLang backend evidence has been collected yet.
