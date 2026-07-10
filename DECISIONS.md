# InferMatrix 设计决策记录

这个文件用于记录 InferMatrix 的关键设计决策，避免项目在开发过程中来回摇摆。

---

## Decision 001：InferMatrix 不是通用 benchmark

日期：2026-07

决定：

InferMatrix 不做 MMLU、HumanEval 等通用模型能力排行榜。

它关注 OpenAI-compatible serving、tool calling、structured output、streaming response 等接口层行为。

理由：

项目目标是帮助我从 LLM 应用开发 / Agent 工程向 LLM Systems / AI Infra 靠近，而不是做一个泛泛的模型评测工具。

---

## Decision 002：先做 mock backend，再接真实 backend

日期：2026-07

决定：

v0.1 先实现 mock backend，不急着接 vLLM、SGLang 或真实 OpenAI-compatible endpoint。

理由：

mock backend 能保证：

- 不依赖 GPU
- 不依赖外部 API key
- 不受网络环境影响
- 响应稳定
- 测试可复现

这有利于先把 case schema、runner、parser、analyzer、report 的框架搭稳。

---

## Decision 003：使用 YAML 定义 case

日期：2026-07

决定：

InferMatrix 使用 YAML 文件定义可复现 case。

理由：

YAML 对人类更友好，适合手写和阅读。case 是项目的核心输入，应该尽量易读、易改、易版本管理。

---

## Decision 004：使用 Pydantic 校验 case schema

日期：2026-07

决定：

YAML 读取后使用 Pydantic 模型校验，生成 `InferCase` 对象。

理由：

YAML 本身只是松散数据。Pydantic 可以让 case 在进入执行流程前完成结构校验，减少后续模块处理脏数据的复杂度。

---

## Decision 005：使用 `extra="forbid"`

日期：2026-07

决定：

核心 Pydantic 模型使用 `ConfigDict(extra="forbid")`。

理由：

在项目早期，宁可严格一点。如果 YAML 里出现未定义字段，应尽早失败，避免拼写错误或字段误用被悄悄吞掉。

---

## Decision 006：CLI 只做入口，不承载核心逻辑

日期：2026-07

决定：

`cli.py` 只负责接收命令、调用核心模块、打印结果。

理由：

CLI 如果承担太多逻辑，会导致后续 runner、parser、analyzer、report 难以复用。核心逻辑应该放在可测试的普通 Python 模块中。

---

## Decision 007：引入 client 层

日期：2026-07

决定：

backend 调用逻辑放在 `clients/` 目录下。

理由：

当前是 mock backend，后续会接 OpenAI-compatible endpoint、vLLM、SGLang 等。client 层可以隔离 backend 差异，避免污染 runner、parser 和 CLI。

---

## Decision 008：使用 runner 作为 case 执行中枢

日期：2026-07

决定：

新增 `src/infermatrix/runner.py`，由 runner 负责把 `InferCase` 交给合适的 client 执行，并返回 `RunResult`。

理由：

CLI 不应该直接承担 backend 选择、client 创建、case 执行等流程控制逻辑。runner 可以让 CLI、测试、未来报告系统复用同一套执行入口。

---

## Decision 009：RunResult 保留 raw response / chunks

日期：2026-07

决定：

`RunResult` 直接保存 `response` 或 `chunks`，不在 runner 内做深度 parser / analyzer。

理由：

runner 的职责是执行，不是分析。后续 parser、analyzer、reports 可以基于同一份 raw output 做不同处理。

---

## Decision 010：阶段 B 只模拟 tool_calls 和 streaming chunks，不做完整解析

日期：2026-07

决定：

`MockOpenAIClient` 在阶段 B-2 只负责生成 OpenAI-compatible 风格的 raw response 或 chunks。

理由：

阶段 B 的目标是 mock backend 与最小闭环。tool call 解析、streaming 合并、structured output 校验应放到阶段 C，避免阶段边界混乱。

---

## Decision 011：普通 chat completion parser 单独成文件

日期：2026-07

决定：

新增 `src/infermatrix/parsers/chat_completion.py`，专门解析普通 non-streaming chat completion response。

理由：

普通文本 response 的核心字段是 `choices[0].message.content`。把解析逻辑从 CLI 中拆出来，可以减少硬编码路径，并提供清晰的 parse failure reason。

---

## Decision 012：tool call parser 单独成文件

日期：2026-07

决定：

新增 `src/infermatrix/parsers/tool_call_parser.py`，不把 tool call 解析塞进 `chat_completion.py`。

理由：

普通文本 response 和 tool call response 的核心字段不同。普通文本关注 `message.content`，tool call 关注 `message.tool_calls[*].function.arguments`。分开文件可以保持 parser 边界清晰。

---

## Decision 013：function.arguments 在 parser 中解析成 dict

日期：2026-07

决定：

`ParsedToolCall` 同时保留：

- `raw_arguments`: 原始 JSON string
- `arguments`: `json.loads()` 后的 Python dict

理由：

原始字符串有利于复现和报告，解析后的 dict 有利于后续 schema checker 使用。

---

## Decision 014：阶段 C-1 不做 tool arguments schema validation

日期：2026-07

决定：

阶段 C-1 只检查 `function.arguments` 是否是合法 JSON object，不检查 required fields 或 JSON Schema。

理由：

JSON 解析属于 parser 职责；schema validation 属于 analyzer/checker 职责。两者分开可以避免阶段 C 内部边界混乱。

---

## Decision 015：streaming chunks 单独使用 stream_parser.py

日期：2026-07

决定：

新增 `src/infermatrix/parsers/stream_parser.py`，专门处理 OpenAI-compatible streaming chunks。

理由：

streaming response 不是一个完整 message，而是一组 chunk。它的核心逻辑是合并 `delta.content`、识别 `delta.role` 和 `finish_reason`，与普通 chat completion parser、tool call parser 的结构不同。

---

## Decision 016：阶段 C-2 只合并文本，不解析 JSON

日期：2026-07

决定：

`parse_streaming_chunks()` 只负责输出 `merged_content`，不负责 `json.loads()` 或 JSON Schema 校验。

理由：

stream parser 的职责是把 chunks 合并成文本。structured output parser 和 schema checker 应该在后续阶段完成，避免职责混乱。

---

## Decision 017：阶段 C-2 暂时要求 assistant role 和 finish_reason

日期：2026-07

决定：

阶段 C-2 暂时要求 chunks 中必须出现 `delta.role == "assistant"`，并且必须出现非空 `finish_reason`。

理由：

这是当前 mock backend 的稳定格式，也有利于初期 parser 行为清晰。后续接真实 backend 时，如果发现兼容性差异，再根据真实样本调整。

---

## Decision 018：structured output parser 只做 JSON 解析，不做 schema validation

日期：2026-07

决定：

新增 `src/infermatrix/parsers/structured_output_parser.py`，只负责把 JSON 文本解析成 Python dict。

理由：

JSON 解析和 JSON Schema 校验是两个不同层次的问题。JSON 解析回答“是不是合法 JSON object”，schema checker 回答“字段是否满足预期 schema”。分开实现可以让 failure reason 更清晰。

---

## Decision 019：ParsedStructuredOutput 同时保留 raw_text 和 data

日期：2026-07

决定：

`ParsedStructuredOutput` 保留：

- `raw_text`: 原始模型输出
- `data`: 解析后的 Python dict

理由：

raw_text 用于复现和报告，data 用于后续 analyzer/checker。

---

## Decision 020：阶段 C-3 暂时只接受 JSON object

日期：2026-07

决定：

`parse_structured_output_text()` 要求 `json.loads()` 的结果必须是 dict。

理由：

InferMatrix 当前的 structured output case 主要面向 object-style JSON schema。array、string、number 虽然是合法 JSON，但暂时不作为阶段 C-3 支持对象。

---

## Decision 021：引入 analyzers 层，而不是 checkers 目录

日期：2026-07

决定：

按照主计划使用 `src/infermatrix/analyzers/` 存放检查和分析逻辑。

理由：

项目主计划中定义的是 `analyzers/tool_call_checker.py`、`analyzers/schema_checker.py`。为了避免目录结构摇摆，采用 analyzers 作为统一目录。

---

## Decision 022：schema checker 只处理 ParsedStructuredOutput.data

日期：2026-07

决定：

`check_json_schema()` 接收 `InferCase` 和 `ParsedStructuredOutput`，不接收 raw response、raw chunks 或 raw text。

理由：

schema checker 属于 analyzer 层，只应该处理 parser 之后的结构化对象。raw response 的解析应该由 parser 完成。

---

## Decision 023：json_schema 放在 expected 中

日期：2026-07

决定：

在 `CaseExpected` 中新增 `json_schema` 字段。

理由：

JSON Schema 描述的是模型输出应满足的结构，属于 expected 的一部分，而不是 metadata 或 tools 的一部分。

---

## Decision 024：schema checker 输出 pass / fail / skip

日期：2026-07

决定：

`SchemaCheckResult.status` 使用三种状态：

- `pass`
- `fail`
- `skip`

理由：

schema check 不应该只返回 bool。  
如果 case 没有要求 schema validation，或者没有配置 schema，应返回 skip，而不是 pass 或 fail。

---

## Decision 025：阶段 C-4 不处理 tool arguments schema

日期：2026-07

决定：

阶段 C-4 只处理 structured output 的 JSON Schema 校验，不处理 tool call arguments 的 schema 校验。

理由：

structured output schema 和 tool arguments schema 虽然都用 JSON Schema，但输入来源不同。前者来自模型文本输出，后者来自 tool call arguments。分开实现有利于保持学习和工程边界清晰。