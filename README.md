# InferMatrix

InferMatrix 是一个面向 **Agentic LLM Systems** 的行为分析框架。

它聚焦于 OpenAI-compatible 大模型推理服务的接口层，分析 streaming、structured output、tool calling 等能力组合下的响应行为、失败模式与兼容性差异。

InferMatrix 不是通用模型能力排行榜，也不是普通的 AI 应用 Demo。它的目标是生成可复现 Case、执行模型请求、解析原始响应、验证接口行为，并生成可用于调试、文档记录和上游开源贡献的报告。

---

## 当前状态

目前，InferMatrix 已完成阶段 A–C 的 Mock Backend 主链路。

当前已经支持：

* 使用 YAML 定义可复现 Case
* Mock OpenAI-compatible 普通 Chat Completion
* Mock Tool Call Response
* Mock Streaming Chunks
* 通过 Runner 统一执行 Case
* 解析普通 Assistant Message
* 解析 Tool Calls
* 将 Tool Arguments 从 JSON String 解析为 Python Dict
* 合并 Streaming Chunks
* 解析 Structured Output JSON
* 使用 JSON Schema 校验 Structured Output
* 校验 Tool Name
* 使用工具定义中的 Parameters Schema 校验 Tool Arguments
* 输出结构化的 `pass`、`fail`、`skip` 检查结果

当前正在开发：

* 阶段 D：报告系统与可复现输出

---

## InferMatrix 能做什么

InferMatrix 关注 LLM 应用与模型推理 Backend 之间的接口行为。

它可以分析以下问题：

* Backend 是否返回了预期的 Tool Name
* Tool Arguments 是否为合法 JSON
* Tool Arguments 是否符合函数定义中的 Parameters Schema
* Streaming Chunks 是否能够正确合并
* 合并后的 Streaming Content 是否为合法 JSON
* Structured Output 是否符合预期 JSON Schema
* 不同 OpenAI-compatible Backend 在相同 Case 下是否存在行为差异
* 某次失败究竟属于 Parser 错误、Schema 错误，还是 Backend 行为差异

---

## InferMatrix 不做什么

InferMatrix 当前不打算成为：

* 通用模型能力排行榜
* MMLU、HumanEval 一类大而全的 Benchmark
* Web 管理后台
* 在线监控告警或 AIOps 系统
* 自动修复代码的 Agent
* 普通 Agent Workflow 平台
* CUDA 或 Kernel 优化项目
* 一开始就接入大量 Backend 的适配器集合

项目会优先保证接口行为分析、最小复现和报告输出能力，而不是快速扩张功能范围。

---

## 核心执行流程

```text
YAML Case
    ↓
load_case()
    ↓
InferCase
    ↓
runner.run_case()
    ↓
Backend Client
    ↓
Raw Response / Streaming Chunks
    ↓
Parser
    ↓
Parsed Object
    ↓
Analyzer
    ↓
Pass / Fail / Skip
    ↓
Report
```

每一层都有明确职责。

---

## 模块职责

### Case 层

`cases.py` 负责读取 YAML Case，并使用 Pydantic 校验数据结构。

```text
YAML → InferCase
```

它负责：

* 读取 YAML 文件
* 校验 Case 字段
* 校验字段类型
* 生成稳定的 `InferCase`

它不负责：

* 调用模型 Backend
* 解析 Response
* 判断输出是否正确

---

### Runner 层

`runner.py` 是 InferMatrix 的执行中枢。

```text
InferCase → RunResult
```

它负责：

* 根据 Case 选择 Backend Client
* 调用 Client 执行 Case
* 返回 Raw Response 或 Streaming Chunks
* 包装成统一的 `RunResult`

它不负责：

* 解析 Response
* 执行 Schema 校验
* 生成报告

---

### Client 层

`clients/` 负责与模型推理 Backend 交互。

当前实现：

* `MockOpenAIClient`

当前 Mock Client 可以生成：

* 普通 Chat Completion Response
* Tool Call Response
* Streaming Chunks

未来会增加：

* OpenAI-compatible HTTP Client
* vLLM Backend
* SGLang Backend
* Ollama 或 LM Studio Backend

```text
Case Request → Raw Backend Response
```

---

### Parser 层

`parsers/` 负责将外部 Raw Response 转换为 InferMatrix 内部的结构化对象。

```text
Raw Response → Parsed Object
```

当前 Parser 包括：

* `chat_completion.py`
* `tool_call_parser.py`
* `stream_parser.py`
* `structured_output_parser.py`

#### Chat Completion Parser

负责：

```text
choices[0].message.content
    ↓
ParsedAssistantMessage
```

#### Tool Call Parser

负责：

```text
message.tool_calls
    ↓
ParsedToolCallMessage
```

并将：

```text
function.arguments JSON String
    ↓
Python Dict
```

#### Stream Parser

负责：

```text
多个 Streaming Chunks
    ↓
收集 delta.content
    ↓
合并 merged_content
    ↓
ParsedStreamMessage
```

#### Structured Output Parser

负责：

```text
JSON Text
    ↓
json.loads()
    ↓
ParsedStructuredOutput
```

Parser 只判断数据是否可以被正确解析，不判断是否符合业务预期。

---

### Analyzer 层

`analyzers/` 负责判断 Parsed Object 是否符合 Case 中声明的 Expected。

```text
Parsed Object + Expected
    ↓
Pass / Fail / Skip
```

当前 Analyzer 包括：

* Structured Output JSON Schema Checker
* Tool Name Checker
* Tool Arguments Schema Checker

当前检查状态包括：

* `pass`：执行检查并通过
* `fail`：执行检查但不符合预期
* `skip`：当前 Case 没有要求执行该检查

Analyzer 不直接处理 Raw Response。Raw Response 必须先通过 Parser。

---

### Report 层

`reports/` 将负责把一次执行中的所有信息整理成可复现报告。

```text
Case
+ RunResult
+ Parsed Output
+ Analyzer Results
    ↓
Markdown Report / JSONL Record
```

阶段 D 计划支持：

* 唯一 `run_id`
* 执行时间
* Case 摘要
* Backend 与 Model 信息
* Feature 开关
* Request 摘要
* Raw Response 摘要
* Parsed Output
* Analyzer Results
* Verdict
* Failure Reasons
* Reproduction Command
* Markdown 输出
* JSONL 输出

---

## 示例 Case

### 普通 Chat Case

```bash
infermatrix run examples/basic_chat.yaml
```

该 Case 验证：

* 普通 Non-streaming Response
* Assistant Message 解析
* Content 提取

---

### Tool Calling Case

```bash
infermatrix run examples/tool_call_weather.yaml
```

该 Case 验证：

* Tool Call Response 生成
* Tool Calls 解析
* Tool Name 校验
* Tool Arguments JSON 解析
* Tool Parameters Schema 校验

核心链路：

```text
tool_call_weather.yaml
    ↓
load_case()
    ↓
InferCase
    ↓
runner.run_case()
    ↓
MockOpenAIClient.run_case()
    ↓
Raw Tool Call Response
    ↓
parse_tool_call_response()
    ↓
ParsedToolCallMessage
    ↓
check_tool_call()
    ↓
Tool Name Check
    ↓
Tool Arguments Schema Check
```

---

### Streaming Structured Output Case

```bash
infermatrix run examples/streaming_json.yaml
```

该 Case 验证：

* Streaming Chunks 生成
* Streaming Content 合并
* Structured Output JSON 解析
* JSON Schema 校验

核心链路：

```text
streaming_json.yaml
    ↓
load_case()
    ↓
InferCase
    ↓
runner.run_case()
    ↓
MockOpenAIClient.stream_case()
    ↓
Raw Streaming Chunks
    ↓
parse_streaming_chunks()
    ↓
ParsedStreamMessage.merged_content
    ↓
parse_structured_output_text()
    ↓
ParsedStructuredOutput.data
    ↓
check_json_schema()
    ↓
SchemaCheckResult
```

---

## 安装

InferMatrix 要求 Python 3.11 或更高版本。

克隆仓库：

```bash
git clone https://github.com/SeRendizc/infer-matrix.git
cd infer-matrix
```

创建虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell 激活虚拟环境：

```powershell
.venv\Scripts\Activate.ps1
```

安装项目及开发依赖：

```bash
python -m pip install -e ".[dev]"
```

---

## 运行测试

运行全部测试：

```bash
python -m pytest
```

显示每条测试名称：

```bash
python -m pytest -v
```

当前测试覆盖：

* YAML Case Loader
* Pydantic Case Validation
* Mock OpenAI Client
* Runner
* 普通 Chat Completion Parser
* Tool Call Parser
* Streaming Chunk Parser
* Structured Output Parser
* Structured Output JSON Schema Checker
* Tool Call Analyzer
* Tool Arguments Schema Checker

---

## 项目结构

```text
infer-matrix/
├── examples/
│   ├── basic_chat.yaml
│   ├── tool_call_weather.yaml
│   └── streaming_json.yaml
│
├── src/
│   └── infermatrix/
│       ├── analyzers/
│       │   ├── __init__.py
│       │   ├── schema_checker.py
│       │   └── tool_call_checker.py
│       │
│       ├── clients/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── mock_openai.py
│       │
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── chat_completion.py
│       │   ├── stream_parser.py
│       │   ├── structured_output_parser.py
│       │   └── tool_call_parser.py
│       │
│       ├── reports/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   └── markdown_renderer.py
│       │
│       ├── cases.py
│       ├── cli.py
│       └── runner.py
│
├── tests/
├── README.md
└── pyproject.toml
```

---

## 设计原则

### Mock First

InferMatrix 先实现 Mock Backend，再接入真实模型服务。

这样可以避免以下问题干扰核心框架开发：

* GPU 环境
* CUDA 依赖
* 网络限制
* API Key
* API 限流
* 模型输出随机性
* Backend 服务启动问题

Mock Backend 让 Parser、Analyzer、Runner 和 Report 可以在完全可控的环境下开发和测试。

---

### Parse Before Analyze

Raw Response 不直接进入 Analyzer。

正确流程是：

```text
Raw Response
    ↓
Parser
    ↓
Parsed Object
    ↓
Analyzer
```

这样可以区分：

* Response Shape 错误
* JSON 语法错误
* Schema Validation 错误
* Expected 不匹配
* Backend 行为差异

---

### 保留 Raw Data 和 Parsed Data

InferMatrix 同时保留：

* Raw Response
* Parsed Output

Raw Response 用于：

* 复现
* 调试
* 上游 Issue
* Backend 差异分析

Parsed Output 用于：

* Analyzer
* JSON Schema 校验
* 报告结构化输出

---

### 明确 Failure Reason

InferMatrix 不只返回一个布尔值。

检查结果至少包含：

```text
name
status
reason
```

例如：

```text
name: tool_arguments_schema
status: fail
reason: 'city' is a required property
```

这样报告可以明确告诉使用者：

* 哪项检查失败
* 为什么失败
* 是输入错误、解析错误，还是 Schema 错误

---

### 最小可复现 Case

InferMatrix 优先构造小而明确的 Case，而不是大规模 Benchmark。

一个合格的 Case 应该能够清楚说明：

* 输入是什么
* 使用哪个 Backend
* 使用哪个 Model
* 开启了哪些 Feature
* Raw Response 是什么
* Parsed Output 是什么
* 哪项检查失败
* 如何重新运行

---

### CLI 不承载核心逻辑

CLI 只负责：

* 接收命令
* 调用核心模块
* 展示结果
* 设置退出码

具体逻辑分别放在：

* Runner
* Client
* Parser
* Analyzer
* Report

这样核心能力可以被测试、脚本、未来 API 或其他工具复用。

---

## 当前限制

当前版本仍处于 Mock Backend 阶段。

暂时不支持：

* 真实 OpenAI-compatible HTTP Endpoint
* vLLM
* SGLang
* Streaming Tool Calls
* Tool Result Message
* 多 Choice 对比
* Reasoning Trace 分析
* Markdown Report
* JSONL Report
* 多 Backend 自动对比
* Batch Case Execution

这些能力会在后续阶段逐步增加。

---

## 路线图

### 阶段 A：项目定义与骨架

状态：已完成。

包括：

* Python Package
* `pyproject.toml`
* YAML Case 格式
* Pydantic 模型
* Typer CLI
* pytest

---

### 阶段 B：Mock Backend 与 Runner

状态：已完成。

包括：

* Mock Chat Completion
* Mock Tool Calls
* Mock Streaming Chunks
* Runner
* `RunResult`

---

### 阶段 C：Parser 与 Analyzer

状态：已完成。

包括：

* Chat Completion Parser
* Tool Call Parser
* Stream Parser
* Structured Output Parser
* Structured Output JSON Schema Checker
* Tool Name Checker
* Tool Arguments Schema Checker

---

### 阶段 D：报告系统与可复现输出

状态：已完成。

已实现：

- [x] 统一 `RunReport`
- [x] 唯一 `run_id`
- [x] Markdown Renderer
- [x] Markdown Writer
- [x] JSONL Writer
- [x] Report Assembler
- [x] Report Bundle Writer
- [x] End-to-End Pipeline
- [x] CLI 自动生成报告
- [x] 自定义 `--report-dir`
- [x] Analyzer 失败报告
- [x] Parser 失败报告
- [x] Runner 失败报告
- [x] UTF-8 与中文支持
- [x] 防止 Markdown 意外覆盖
- [x] JSONL 追加写入
- [x] Pipeline 与 CLI End-to-End 测试

完整链路：

```text
YAML Case
    ↓
InferCase
    ↓
Pipeline
    ├── Runner
    ├── Parser
    └── Analyzer
    ↓
RunReport
    ├── runs/<run_id>.md
    └── runs/runs.jsonl
```

---                                                                                                                                                                                                                                         

### 阶段 E：真实 Transport 与 Chat Completions

状态：进行中。

#### 已完成：E-1A Backend 与 Protocol 配置分离

* [x] 新增 `BackendConfig`
* [x] 新增 `ProtocolConfig`
* [x] Backend Provider 与 API Protocol 独立建模
* [x] 新增 Connect、Read、Write、Pool 四类 Timeout 配置
* [x] API Key 配置只保存环境变量名称
* [x] 迁移现有 Mock YAML Case
* [x] Runner 使用 `backend.provider`
* [x] Pipeline 和 Report Assembler 使用 `backend.provider`
* [x] CLI 分别展示 Backend 与 Protocol
* [x] 未知 Backend Provider 和 Protocol 在配置层被拒绝
* [x] 合法但尚未接入的 Backend 由 Runner 明确拒绝
* [x] 全量测试 103 项通过
* [x] Ruff 静态检查通过
* [x] Basic Chat、Tool Calling 和 Streaming CLI 回归通过

当前 Case 配置：

```yaml
backend:
  provider: mock

protocol:
  type: chat_completions

model: mock-model
```

真实 Endpoint 将使用：

```yaml
backend:
  provider: openai_compatible
  base_url: http://127.0.0.1:8000/v1
  api_key_env: INFERMATRIX_API_KEY
  timeout:
    connect: 5.0
    read: 120.0
    write: 30.0
    pool: 5.0

protocol:
  type: chat_completions
```

#### 当前唯一子阶段：E-1B Raw HTTP Transport

目标：

* 引入 HTTPX
* 定义协议无关的 HTTP Transport 接口
* 实现同步原始 HTTP 请求
* 实现 Connect、Read、Write 和 Pool Timeout
* 分类连接错误、超时、HTTP 状态错误和响应读取错误
* 捕获原始 Request 与 Response
* 对 Authorization 等敏感 Header 脱敏
* 默认不自动重试
* 使用 `httpx.MockTransport` 完成确定性测试

#### 后续计划

1. E-1B：Raw HTTP Transport
2. E-1C：SSE Wire Decoder
3. E-1D：Chat Completions Adapter，并将 Protocol 写入正式 RunReport
4. E-1E：真实 vLLM Smoke Test 与第一份真实 Evidence Bundle

当前不提前实现：

* Responses Adapter
* Semantic Trace
* Invariant Engine
* vLLM Cache 实验
* SGLang 对比
