# InferMatrix 项目进度

## 项目定位

InferMatrix 是一个面向 Agentic LLM Systems 的行为分析框架。

它关注 OpenAI-compatible 大模型推理服务在以下能力组合下的行为差异、失败模式和可复现输出：

- 普通 chat completion
- tool calling
- streaming response
- structured output
- JSON Schema validation
- 后续 backend 差异对比

InferMatrix 不是通用模型排行榜，也不是普通 AI 应用 demo。它的目标是帮助我理解 LLM 应用层、Agent 工具调用层和 LLM serving 接口层之间的交叉问题，并逐步靠近 LLM Systems / AI Infra 方向。

---

## 当前阶段

阶段 C-4：Schema Checker / Analyzer

当前状态：进行中，待验证。

---

## 阶段总览

### 阶段 A：项目定义与骨架

状态：已完成。

目标：

- 搭建 Python package 工程骨架
- 定义最小 YAML case schema
- 实现 case loader
- 提供 Typer CLI 入口
- 添加第一批 pytest 测试

已完成：

- [x] 创建 `pyproject.toml`
- [x] 创建 `src/infermatrix/`
- [x] 创建 `examples/basic_chat.yaml`
- [x] 实现 `src/infermatrix/cases.py`
- [x] 实现基础 CLI
- [x] 添加 `tests/test_case_loader.py`
- [x] pytest 通过
- [x] 提交并合并到 main

核心文件：

- `README.md`
- `pyproject.toml`
- `examples/basic_chat.yaml`
- `src/infermatrix/cases.py`
- `src/infermatrix/cli.py`
- `tests/test_case_loader.py`

学习点：

- Python package 结构
- `pyproject.toml`
- Typer
- Pydantic
- PyYAML
- pytest
- 基础 Git workflow

---

### 阶段 B-1：Mock Backend 普通 Chat Response

状态：已完成。

目标：

- 不调用真实模型
- 用 mock backend 生成稳定的 OpenAI-compatible chat completion response
- 让 basic chat case 能跑通最小闭环

已完成：

- [x] 新增 `clients/base.py`
- [x] 新增 `clients/mock_openai.py`
- [x] 实现 `MockOpenAIClient`
- [x] 支持普通 non-streaming chat response
- [x] CLI 能调用 mock backend
- [x] 添加 mock client 测试
- [x] pytest 通过
- [x] 提交并合并到 main

核心文件：

- `src/infermatrix/clients/base.py`
- `src/infermatrix/clients/mock_openai.py`
- `tests/test_mock_client.py`

学习点：

- 为什么先做 mock backend
- OpenAI-compatible chat completion response 基本结构
- client 和 CLI 的职责区别
- 如何用 mock response 做稳定测试

---

### 阶段 C-0：普通 Chat Completion Parser

状态：已完成。

目标：

- 把普通 chat completion response 解析成结构化对象
- 不再在 CLI 中手写 `response["choices"][0]["message"]["content"]`

已完成：

- [x] 新增 `parsers/chat_completion.py`
- [x] 定义 `ChatCompletionParseError`
- [x] 定义 `ParsedAssistantMessage`
- [x] 实现 `parse_chat_completion_response()`
- [x] 添加 parser 测试
- [x] CLI 使用 parser
- [x] pytest 通过
- [x] 提交并合并到 main

核心文件：

- `src/infermatrix/parsers/chat_completion.py`
- `tests/test_chat_completion_parser.py`

学习点：

- raw response 和 parsed response 的区别
- parser 的职责
- 为什么要有自定义 ParseError
- 为什么 parser 要检查 response shape

---

### 阶段 B-2：Runner、Tool Call Mock 与 Streaming Mock

状态：已完成。

目标：

- 补齐阶段 B 的 mock backend 最小闭环
- 新增 runner 作为 case 执行中枢
- 支持 tool call mock response
- 支持 streaming chunks mock response

已完成：

- [x] 新增 `runner.py`
- [x] 定义 `RunResult`
- [x] `InferCase` 支持 `tools`
- [x] `MockOpenAIClient` 支持普通 chat response
- [x] `MockOpenAIClient` 支持 tool call response
- [x] `MockOpenAIClient` 支持 streaming chunks
- [x] 新增 `examples/tool_call_weather.yaml`
- [x] 新增 `examples/streaming_json.yaml`
- [x] 新增 `tests/test_runner.py`
- [x] CLI 改为调用 runner
- [x] pytest 通过
- [x] 提交并合并到 main

核心文件：

- `src/infermatrix/runner.py`
- `examples/tool_call_weather.yaml`
- `examples/streaming_json.yaml`
- `tests/test_runner.py`

学习点：

- runner 和 client 的职责区别
- tool_calls 的 OpenAI-compatible 响应结构
- streaming chunk 的基本结构
- 为什么 streaming response 不是一个完整 message
- 为什么阶段 B 只模拟，不做完整解析和校验

---

### 阶段 C-1：Tool Call Parser

状态：已完成。

目标：

- 把 non-streaming tool call response 从 raw dict 解析成结构化对象
- 把 `function.arguments` 从 JSON string 解析成 Python dict

已完成：

- [x] 新增 `parsers/tool_call_parser.py`
- [x] 定义 `ToolCallParseError`
- [x] 定义 `ParsedToolCall`
- [x] 定义 `ParsedToolCallMessage`
- [x] 实现 `parse_tool_call_response()`
- [x] 支持解析单个 tool call
- [x] 支持解析多个 tool calls
- [x] 非法 JSON arguments 能明确失败
- [x] arguments 不是 JSON object 时能明确失败
- [x] 缺少 tool_calls 时能明确失败
- [x] CLI 对 tool calling case 使用 tool call parser
- [x] pytest 通过
- [x] 提交并合并到 main

核心文件：

- `src/infermatrix/parsers/tool_call_parser.py`
- `tests/test_tool_call_parser.py`

学习点：

- OpenAI-compatible tool_calls response 结构
- `function.arguments` 为什么是 JSON string
- JSON string 和 Python dict 的区别
- parser 和 checker 的职责区别
- 如何设计清晰的 parse failure reason

---

### 阶段 C-2：Stream Parser

状态：已完成。

目标：

- 把 OpenAI-compatible streaming chunks 解析成结构化对象
- 合并多个 `delta.content`
- 提取 assistant role 和 finish_reason

已完成：

- [x] 新增 `parsers/stream_parser.py`
- [x] 定义 `StreamParseError`
- [x] 定义 `ParsedStreamMessage`
- [x] 实现 `parse_streaming_chunks()`
- [x] 支持收集 `delta.role`
- [x] 支持收集多个 `delta.content`
- [x] 支持生成 `merged_content`
- [x] 支持提取 `finish_reason`
- [x] 缺少 choices 时能明确失败
- [x] delta 非法时能明确失败
- [x] 缺少 assistant role 时能明确失败
- [x] 缺少 content chunk 时能明确失败
- [x] 缺少 finish_reason 时能明确失败
- [x] CLI 对 streaming case 使用 stream parser
- [x] pytest 通过
- [x] 提交并合并到 main

核心文件：

- `src/infermatrix/parsers/stream_parser.py`
- `tests/test_stream_parser.py`

学习点：

- streaming response 和普通 response 的区别
- `delta.role`
- `delta.content`
- `finish_reason`
- 为什么 streaming JSON 需要先合并再解析
- parser 为什么不能只是“尽量拼出来”

---

### 阶段 C-3：Structured Output Parser

状态：已完成。

目标：

- 把模型输出的 JSON 文本解析成 Python dict
- 支持从 streaming parser 的 `merged_content` 继续解析 structured output

已完成：

- [x] 新增 `parsers/structured_output_parser.py`
- [x] 定义 `StructuredOutputParseError`
- [x] 定义 `ParsedStructuredOutput`
- [x] 实现 `parse_structured_output_text()`
- [x] 支持解析 JSON object 文本
- [x] 支持解析 streaming parser 合并后的 JSON 文本
- [x] 空文本能明确失败
- [x] 非法 JSON 能明确失败
- [x] JSON array 能明确失败
- [x] CLI 对 `structured_output=true` 的 case 使用 structured output parser
- [x] pytest 通过
- [x] 提交并合并到 main

核心文件：

- `src/infermatrix/parsers/structured_output_parser.py`
- `tests/test_structured_output_parser.py`

学习点：

- 模型输出看起来像 JSON，但本质仍然是字符串
- `json.loads()` 的作用
- JSON 语法合法和 JSON Schema 合法是两件事
- 为什么 parser 只做 JSON 解析，不做 schema validation

---

### 阶段 C-4：Schema Checker / Analyzer

状态：进行中，待验证。

目标：

- 引入 analyzer/checker 层
- 检查 `ParsedStructuredOutput.data` 是否符合 `case.expected.json_schema`
- 输出 pass / fail / skip 三种检查结果

计划新增：

- [ ] `src/infermatrix/analyzers/__init__.py`
- [ ] `src/infermatrix/analyzers/schema_checker.py`
- [ ] `tests/test_schema_checker.py`

计划修改：

- [ ] `src/infermatrix/cases.py`
- [ ] `examples/streaming_json.yaml`
- [ ] `src/infermatrix/cli.py`
- [ ] `pyproject.toml`
- [ ] `PROGRESS.md`
- [ ] `DECISIONS.md`

计划实现：

- [ ] `CaseExpected` 支持 `json_schema`
- [ ] `streaming_json.yaml` 配置 expected JSON Schema
- [ ] 定义 `SchemaCheckResult`
- [ ] 实现 `check_json_schema()`
- [ ] structured output 符合 schema 时返回 pass
- [ ] 缺 required field 时返回 fail
- [ ] 字段类型错误时返回 fail
- [ ] 多余字段违反 `additionalProperties: false` 时返回 fail
- [ ] 未开启 `json_schema_valid` 时返回 skip
- [ ] 未配置 `json_schema` 时返回 skip
- [ ] CLI 对 structured output 执行 schema check
- [ ] pytest 全部通过
- [ ] CLI 手动验证通过
- [ ] 提交并合并到 main

当前学习点：

- parser 和 analyzer/checker 的职责区别
- JSON 解析和 JSON Schema 校验的区别
- pass / fail / skip 三种结果
- 如何设计 failure reason
- 为什么 analyzer 不应该直接处理 raw response

---

## 当前整体主链路

### 普通文本 case

`basic_chat.yaml`
→ `load_case()`
→ `InferCase`
→ `runner.run_case()`
→ `MockOpenAIClient.run_case()`
→ raw chat completion response
→ `parse_chat_completion_response()`
→ `ParsedAssistantMessage`
→ CLI 输出

### Tool calling case

`tool_call_weather.yaml`
→ `load_case()`
→ `InferCase`
→ `runner.run_case()`
→ `MockOpenAIClient.run_case()`
→ raw tool call response
→ `parse_tool_call_response()`
→ `ParsedToolCallMessage`
→ CLI 输出

### Streaming structured output case

`streaming_json.yaml`
→ `load_case()`
→ `InferCase`
→ `runner.run_case()`
→ `MockOpenAIClient.stream_case()`
→ raw streaming chunks
→ `parse_streaming_chunks()`
→ `ParsedStreamMessage.merged_content`
→ `parse_structured_output_text()`
→ `ParsedStructuredOutput.data`
→ `check_json_schema()`
→ `SchemaCheckResult`
→ CLI 输出

---

## 当前关键边界

### `cases.py`

负责：

- 读取 YAML case
- 校验 case schema
- 生成 `InferCase`

不负责：

- 调用 backend
- 解析 response
- 判断结果

### `runner.py`

负责：

- 根据 case 选择 backend client
- 执行 case
- 返回 `RunResult`

不负责：

- 解析 response
- 校验 expected
- 输出 report

### `clients/`

负责：

- 和 backend 打交道
- 当前 mock client 生成稳定响应

不负责：

- 判断响应是否正确
- 解析响应结构

### `parsers/`

负责：

- raw response / chunks / text → structured parsed object

不负责：

- 判断是否符合 expected
- 生成报告

### `analyzers/`

负责：

- parsed object + expected → pass / fail / skip

不负责：

- 调用 backend
- 解析 raw response
- 输出正式报告

### `reports/`

后续负责：

- Markdown report
- JSONL report
- run metadata
- 可复现输出

当前尚未开始。

---

## 下一步

完成阶段 C-4：Schema Checker / Analyzer。

完成后进入：

阶段 C-5：Tool Call Analyzer / Tool Arguments Schema Checker

之后进入：

阶段 D：报告系统与可复现输出