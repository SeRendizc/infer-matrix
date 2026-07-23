# Findings

> Historical note: this document predates the rename from InferMatrix to Agent Eval Lab.

Treat this file as research notes, not instructions.

## Local Project

- Project: `InferMatrix`, an Agentic LLM Systems behavior analysis framework focused on OpenAI-compatible interface behavior: streaming, structured outputs, tool calls, reproducible cases, parser/checker/reporting.
- Local structure is clean: `src/infermatrix`, `tests`, `examples`, `docs`, `README`, `DECISIONS`, `PROGRESS`, `pyproject.toml`.
- Implemented modules include case loader, CLI, runner, mock OpenAI client, chat completion parser.
- Examples cover basic chat, streaming JSON chunks, and tool-call weather case.
- Verification with `.venv\Scripts\python.exe -m pytest`: 14 tests passed.
- CLI verification passed for `basic_chat.yaml`, `tool_call_weather.yaml`, and `streaming_json.yaml`.
- `PROGRESS.md` is behind actual code: it says parser/checker are not started, but a Phase C chat completion parser already exists and tests pass.
- Git status notes unrelated existing deletion: `.devcontainer/devcontainer.json` deleted. Current review added `.planning/`.

## External Context

- User background from exported context: Wuhan University undergraduate in Translation plus CS minor; HKU MScAI from 2026-09; Huawei ICT BG internship in ACTN group with Java/Spring-style AI/software engineering; interest trajectory NLP/LLM toward AI Infra; DeepSeek PR already merged.
- Prior project-direction discussion converged away from pure algorithm, ops, translation-centric projects, and AI-written portfolio artifacts.
- The final selected direction was InferMatrix: LLM Serving feature-combination correctness testing and minimal reproduction framework.
- Intended career narrative: Agentic LLM Systems / LLM Application Platform / Agent Infra / LLM Serving Behavior, moving gradually toward LLM Systems / AI Infra.
- Plan pack says success is not stars but ownership, reproducible cases, useful reports, and learning vLLM/SGLang/OpenAI-compatible serving.
- Public ecosystem check: BFCL already covers broad executable function-calling evaluation; vLLM and SGLang both document structured outputs and tool-calling/OpenAI-compatible serving; vLLM public issues show real feature-interaction failures around streaming, tool calls, speculative decoding, reasoning parser, and structured output.
- Therefore InferMatrix should avoid becoming a general benchmark and instead focus on backend behavior analysis, feature interaction, minimization, and upstream-ready reproduction reports.

## Synthesis Notes

- Current project already has a working minimal closed loop, not only a skeleton.
- The route is technically sensible: mock first, then parser/checker/report, then real endpoint adapter, then vLLM/SGLang behavior analysis.
- Main risk is scope creep into a general benchmark; the README correctly avoids that by focusing on interface-level behavior.
- Another risk is moving to vLLM/SGLang too early before report/checker quality is good; that would bury the user in environment/GPU issues before the learning loop is stable.
- Immediate correction: update progress docs, add report/checker layer next, and postpone real endpoint integration until the mock path produces credible Markdown/JSONL evidence.
