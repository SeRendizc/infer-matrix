# Agent Eval Lab

Evaluation infrastructure for agentic LLM systems, starting from reproducible
model-interface behavior and extending to agent traces, recovery, and failure
attribution.

Agent Eval Lab currently focuses on the model-interface layer between agentic
applications and OpenAI-compatible inference backends. It turns compact YAML
evaluation cases into requests, preserves protocol evidence, classifies parser
and checker failures, and writes reproducible reports.

The repository does not claim to be a general model benchmark, an agent
framework, or a serving-performance suite.

## Current status

Implemented on `main`:

- YAML evaluation cases validated with Pydantic.
- Separate backend and protocol configuration.
- Deterministic in-process mock backend.
- OpenAI-compatible non-streaming HTTP client.
- OpenAI-compatible streaming client and Chat Completions chunk adapter.
- Synchronous and asynchronous HTTPX transport.
- Raw request/response evidence with URL, header, and body redaction.
- Incremental SSE wire decoding across arbitrary byte boundaries.
- Chat message, tool-call, streaming, and structured-output parsers.
- JSON Schema and tool-call analyzers.
- Structured `RunReport` assembly.
- Markdown and append-only JSONL reports.
- End-to-end pipeline and `agent-eval` CLI.

The current test suite contains 154 passing tests. Real vLLM/SGLang evidence,
Responses API support, cross-backend comparison, agent-trace evaluation,
recovery experiments, and failure attribution across full agent runs remain
roadmap work.

## Evaluation flow

```text
YAML EvalCase
    -> Pipeline
       -> Runner
          -> Mock or OpenAI-compatible client
          -> HTTP/SSE evidence
       -> Parser
       -> Analyzer
    -> RunReport
       -> Markdown
       -> JSONL
```

The layers intentionally keep wire evidence, parsed objects, and evaluation
results separate. This makes it possible to distinguish backend behavior,
protocol-shape errors, parser failures, and expectation failures.

## Installation

Agent Eval Lab requires Python 3.11 or newer.

```powershell
git clone https://github.com/SeRendizc/agent-eval-lab.git
cd agent-eval-lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Run an evaluation case

Mock non-streaming case:

```powershell
agent-eval run examples/basic_chat.yaml
```

Mock structured streaming case:

```powershell
agent-eval run examples/streaming_json.yaml
```

Tool-calling case:

```powershell
agent-eval run examples/tool_call_weather.yaml
```

Real OpenAI-compatible smoke case:

```powershell
$env:AGENT_EVAL_API_KEY = "<backend-api-key>"
agent-eval run examples/real_chat_smoke.yaml
```

The case selects an `openai_compatible` backend and names the environment
variable containing its API key. Do not store secrets in YAML.

Each run writes:

```text
runs/
|-- <run_id>.md
`-- runs.jsonl
```

Use `--report-dir` to choose another output directory.

## Case shape

```yaml
case_id: basic-chat
backend:
  provider: mock
protocol:
  type: chat_completions
model: mock-model
features:
  streaming: false
  tool_calling: false
  structured_output: false
messages:
  - role: user
    content: Say hello.
expected:
  contains_text: hello
```

Cases describe the backend, protocol, model, enabled interface features,
messages, tools, expected behavior, and optional metadata. Loading a case
produces an `EvalCase`.

## Development verification

```powershell
python -m pytest -q
python -m ruff check .
```

Build distributions:

```powershell
python -m build
```

## Package structure

```text
src/agent_eval_lab/
|-- analyzers/
|-- clients/
|-- parsers/
|-- protocols/
|-- reports/
|-- transports/
|-- cases.py
|-- cli.py
|-- pipeline.py
`-- runner.py
```

## Roadmap

The next high-value milestone is one reproducible real-backend evidence chain:

```text
backend/version/config
    -> deterministic EvalCase
    -> raw wire evidence
    -> classified failure
    -> minimal reproduction
    -> upstream-ready issue or fix
```

Responses API and agent-trace evaluation should build on that evidence model
rather than expanding mock-only surface area.
