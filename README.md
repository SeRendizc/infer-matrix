# InferMatrix

InferMatrix is an Agentic LLM Systems behavior analysis framework.

It focuses on the interface layer where OpenAI-compatible serving, streaming responses, structured outputs, and tool calling interact.

InferMatrix is not a general model benchmark. It is designed to generate reproducible cases, parse model-serving responses, validate tool-call and structured-output behavior, and produce reports that can be used for debugging, documentation, and upstream open-source contributions.

## Current Scope

Stage A focuses on:

- Python project skeleton
- YAML case definition
- CLI entrypoint
- Case loader
- Basic pytest coverage

## Roadmap

- Mock OpenAI-compatible backend
- Tool call parser
- Streaming response parser
- JSON Schema checker
- Markdown / JSONL reports
- OpenAI-compatible endpoint adapter
- vLLM / SGLang behavior analysis