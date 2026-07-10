# InferMatrix 项目进度

## 当前阶段

阶段 B：Mock OpenAI-compatible Backend

## 当前状态

阶段 A 已完成。
阶段 B 进行中，待验证。

## 项目当前定位

InferMatrix 是一个面向 Agentic LLM Systems 的行为分析框架，关注 OpenAI-compatible 大模型推理服务在 streaming、structured output、tool calling 等功能组合下的响应行为、失败模式和可复现报告。

当前项目仍处于早期基础建设阶段，不连接真实模型，不连接 vLLM、SGLang 或 OpenAI API。

---

# 总体阶段进度

| 阶段   | 名称                                 | 状态  |
| ---- | ---------------------------------- | --- |
| 阶段 A | 项目骨架与 YAML Case Loader             | 已完成 |
| 阶段 B | Mock OpenAI-compatible Backend     | 进行中 |
| 阶段 C | Parser 与 Checker                   | 未开始 |
| 阶段 D | Markdown / JSONL Report            | 未开始 |
| 阶段 E | OpenAI-compatible Endpoint Adapter | 未开始 |
| 阶段 F | vLLM / SGLang 行为分析                 | 未开始 |
| 阶段 G | 开源 issue / PR 贡献                   | 未开始 |
| 阶段 H | 求职化包装                              | 未开始 |

---

# 阶段 A：项目骨架与 YAML Case Loader

## 阶段状态

已完成。

## 本阶段目标

本阶段的目标是搭建 InferMatrix 的最小 Python 工程基础，包括：

* Python 项目目录结构
* 项目配置文件 `pyproject.toml`
* YAML case 文件格式
* Pydantic 数据模型
* YAML case 读取函数
* Typer 命令行入口
* 第一个 pytest 自动测试

本阶段不连接真实模型，也不连接 vLLM、SGLang 或 OpenAI API。

## 已完成事项

* [x] 创建项目仓库
* [x] 创建 Python package 目录结构
* [x] 添加 `pyproject.toml`
* [x] 添加 `README.md`
* [x] 添加 `examples/basic_chat.yaml`
* [x] 实现 `src/infermatrix/cases.py`
* [x] 使用 `ConfigDict(extra="forbid")` 启用严格字段校验
* [x] 实现 `src/infermatrix/cli.py`
* [x] 添加 `tests/test_case_loader.py`
* [x] 成功运行 pytest
* [x] 成功运行 CLI 命令

## 已验证命令

### 1. 运行测试

命令：

```bash
pytest
```

结果：

```text
1 passed
```

说明：

测试文件 `tests/test_case_loader.py` 已成功验证 `load_case()` 可以正确读取 `examples/basic_chat.yaml`。

### 2. 检查 YAML 是否正确解析为 Python 对象

命令：

```bash
python -c "from infermatrix.cases import load_case; c=load_case('examples/basic_chat.yaml'); print(c.model_dump())"
```

结果摘要：

`case_id`、`backend`、`model`、`features`、`messages`、`expected` 和 `metadata` 都已被正确解析。

其中：

* `features.streaming` 为 `False`
* `features.tool_calling` 为 `False`
* `features.structured_output` 为 `False`
* `expected.contains_text` 为 `"InferMatrix"`

### 3. 运行 CLI

命令：

```bash
infermatrix run examples/basic_chat.yaml
```

结果摘要：

CLI 成功读取并显示了 case 的基本信息，包括：

* Case ID
* Backend
* Model
* Streaming
* Tool calling
* Structured output
* Messages
* Expected text

## 本阶段遇到的问题

### 问题 1：Pydantic 字段缺少类型注解

报错摘要：

```text
Field 'backend' requires a type annotation
```

原因：

Pydantic 模型字段必须写成“字段名 + 类型 + 默认值”的形式。

错误写法示例：

```python
backend = Field(default="mock")
```

正确写法：

```python
backend: str = Field(default="mock")
```

解决方式：

为 `backend`、`model`、`features`、`messages`、`expected`、`metadata` 等字段补充明确类型注解。

### 问题 2：YAML 字段名和 Pydantic 模型字段名不一致

报错摘要：

```text
case_id Field required
```

原因：

YAML 中字段名写成了 `case-id`，但 Pydantic 模型中字段名是 `case_id`。

解决方式：

统一字段名，使用：

```yaml
case_id: basic_chat_001
```

### 问题 3：`expected` 写成列表或字段拼写错误

报错或现象：

`expected` 无法正确解析，或者 `contains_text` 结果为 `None`。

原因：

YAML 中可能写成了：

```yaml
contains_test
```

或者把 `expected` 写成了列表形式。

正确写法：

```yaml
expected:
  contains_text: "InferMatrix"
```

解决方式：

确保 YAML 中的 `expected` 是一个对象，而不是列表；并且字段名必须是 `contains_text`。

### 问题 4：`feature` 和 `features` 字段名不一致

报错摘要：

```text
InferCase object has no attribute 'features'
```

原因：

Pydantic 模型中字段写成了 `feature`，但 YAML、测试和 CLI 中使用的是 `features`。

解决方式：

统一使用复数形式：

```python
features: CaseFeatures = Field(default_factory=CaseFeatures)
```

### 问题 5：Typer CLI 解析异常

现象：

CLI 运行时出现参数解析问题。

解决方式：

* 将 Typer 升级到 `0.16.0`
* 在 `cli.py` 中添加 `@app.callback()`，让 `infermatrix` 明确作为命令组工作

## 本阶段学到的概念

* Python 项目目录结构
* `src layout`
* `pyproject.toml`
* 虚拟环境
* editable install
* YAML 配置文件
* Pydantic 数据模型
* 类型注解
* 严格字段校验
* Typer 命令行工具
* pytest 自动测试
* Git 阶段性提交

## 当前理解总结

InferMatrix 的基础流程是：

```text
YAML case 文件
  ↓
cases.py 定义 case 应该长什么样
  ↓
load_case() 把 YAML 读取成经过校验的 Python 对象
  ↓
cli.py 把这个能力暴露成命令行工具
  ↓
pytest 验证 case loader 是否按预期工作
```

当前阶段完成的是 InferMatrix 的第一层能力：**定义和读取实验用例**。

---

# 阶段 B：Mock OpenAI-compatible Backend

## 阶段状态

进行中，待验证。

## 本阶段目标

本阶段目标是实现一个假的 OpenAI-compatible backend，使 InferMatrix 在不依赖真实模型、不依赖网络、不依赖 GPU、不依赖 API key 的情况下，也能运行一个 case 并得到稳定、可控的模型响应。

阶段 B 的核心流程是：

```text
YAML case
  ↓
InferCase 对象
  ↓
MockOpenAIClient
  ↓
OpenAI-compatible 风格响应
```

## 为什么要先做 Mock Backend

真实模型有很多不稳定因素：

* 模型输出不确定
* API 可能限流
* 本地模型环境可能难装
* vLLM / SGLang 可能受 CUDA、显卡、依赖影响
* streaming 输出更难调试

Mock Backend 可以先隔离这些外部不确定性，让我们专注开发：

* client 抽象
* response 结构
* parser
* checker
* report
* runner

## 新增文件

* [ ] `src/infermatrix/clients/__init__.py`
* [ ] `src/infermatrix/clients/base.py`
* [ ] `src/infermatrix/clients/mock_openai.py`
* [ ] `tests/test_mock_client.py`

## 修改文件

* [ ] `examples/basic_chat.yaml`
* [ ] `src/infermatrix/cli.py`

## 本阶段计划实现能力

* [ ] 定义 `BaseClient` 抽象基类
* [ ] 实现 `MockOpenAIClient`
* [ ] 返回类似 OpenAI Chat Completion 的响应结构
* [ ] 支持从 `metadata.mock_response` 控制 mock 回复内容
* [ ] 对 streaming / tool calling / structured output 暂不支持的功能明确报错
* [ ] 添加 mock client 单元测试
* [ ] CLI 能调用 mock backend 并打印 mock response
* [ ] pytest 全部通过
* [ ] CLI 手动验证通过

## 当前支持范围

阶段 B 第一版只支持普通非流式 chat case。

以下功能暂不支持：

* streaming
* tool calling
* structured output

这些功能会在后续阶段逐步加入。

## 本阶段学习点

* client / backend 的区别
* mock 的作用
* 抽象基类 `ABC`
* `abstractmethod`
* 继承
* OpenAI-compatible response 基本结构
* fail fast 思想
* 用 pytest 验证正常路径和异常路径

## 本阶段核心概念解释

### client 是什么？

在 InferMatrix 中，client 是负责和某个模型后端交互的对象。

例如：

* `MockOpenAIClient`：假的模型后端客户端
* `OpenAICompatibleClient`：未来用于请求真实 OpenAI-compatible API 的客户端
* `VLLMClient`：未来可能用于适配 vLLM
* `SGLangClient`：未来可能用于适配 SGLang

现阶段的 `MockOpenAIClient` 不会真的请求模型，只会返回一个稳定、可控的假响应。

### backend 是什么？

backend 是模型服务后端。

例如：

* mock backend
* OpenAI API
* vLLM server
* SGLang server
* Ollama
* LM Studio
* 公司内部模型服务

client 是“去和 backend 打交道的代码对象”。

### mock 是什么？

mock 是假的、模拟的对象。

Mock Backend 的作用是：

* 不依赖真实模型
* 不依赖网络
* 不依赖 API key
* 不依赖 GPU
* 能稳定返回我们预设的响应
* 方便测试 parser、checker 和 report

### 为什么要 fail fast？

fail fast 的意思是：暂时不支持的功能，不要假装支持，而是直接明确报错。

例如阶段 B 暂不支持 streaming。如果 YAML 中写：

```yaml
features:
  streaming: true
```

Mock client 应该直接报错：

```text
MockOpenAIClient does not support streaming yet.
```

这样可以避免错误被隐藏到后面的流程里。

## 本阶段完成标准

阶段 B 完成时，应该满足：

* `pytest` 全部通过
* `infermatrix run examples/basic_chat.yaml` 可以通过 MockOpenAIClient 得到响应
* CLI 能显示 mock response 的主要内容
* 如果 case 启用了暂不支持的功能，程序能明确报错
* 你能解释 `BaseClient` 和 `MockOpenAIClient` 的关系
* 你能解释为什么先 mock，而不是直接接真实模型

---

# 阶段 C：OpenAI-compatible Response Parser

## 当前状态

待实现与验证。

## 本阶段目标

阶段 C 的目标是实现一个专门的 response parser，用于解析 OpenAI-compatible Chat Completion 响应。

阶段 B 中，CLI 直接通过下面这种方式读取模型文本：

`response["choices"][0]["message"]["content"]`

这种写法在最小闭环里可以接受，但随着后续加入 tool calling、streaming、structured output 和异常响应，CLI 会变得越来越乱。

阶段 C 要把这部分逻辑抽出来，形成专门的 parser：

`Mock response → parse_chat_completion_response() → ParsedAssistantMessage`

## 新增文件

- `src/infermatrix/parsers/__init__.py`
- `src/infermatrix/parsers/chat_completion.py`
- `tests/test_chat_completion_parser.py`

## 修改文件

- `src/infermatrix/cli.py`

## 本阶段已实现能力

- [ ] 定义 `ParsedAssistantMessage` 解析结果对象
- [ ] 定义 `ChatCompletionParseError` 解析错误类型
- [ ] 实现 `parse_chat_completion_response()`
- [ ] 从 `choices[0].message.content` 提取 assistant 文本
- [ ] 解析 `model`
- [ ] 解析 `choice_index`
- [ ] 解析 `finish_reason`
- [ ] 对缺失 `choices` 的响应明确报错
- [ ] 对空 `choices` 的响应明确报错
- [ ] 对缺失 `message` 的响应明确报错
- [ ] 对非 assistant role 明确报错
- [ ] 对空 content 明确报错
- [ ] 对 tool call response 暂时明确拒绝
- [ ] CLI 改为调用 parser，而不是手动访问嵌套 dict
- [ ] pytest 全部通过
- [ ] CLI 手动验证通过

## 本阶段学习点

- OpenAI-compatible response 的嵌套结构
- `choices[0]` 的含义
- `message.role` 与 `message.content`
- parser 和 CLI 的职责分离
- 自定义异常
- 解析结果对象
- fail fast 思想
- 正常路径测试和异常路径测试

## 当前注意事项

阶段 C 只解析普通非流式 assistant content response。

以下能力暂时不做：

- tool_calls 解析
- streaming chunk 解析
- structured output / JSON Schema 校验
- 多个 choices 的对比分析

这些能力会在后续阶段继续扩展。

---

# 阶段 B-2：Runner、Tool Call Mock 与 Streaming Mock

## 当前状态

进行中，待验证。

## 本阶段归属

本阶段仍然属于阶段 B：Mock Backend 与最小闭环。

它不是阶段 C，也不是阶段 D。

## 本阶段目标

补齐阶段 B 里尚未完成的最小闭环能力：

YAML case → InferCase → runner → MockOpenAIClient → raw response / streaming chunks → RunResult

---

# 阶段 C-2：Stream Parser

## 当前状态

进行中，待验证。

## 本阶段归属

本阶段属于阶段 C：Parser 与 Checker。

## 本阶段目标

把 OpenAI-compatible streaming chunks 解析成结构化的 `ParsedStreamMessage`。

当前链路：

`streaming_json.yaml`
→ `load_case()`
→ `InferCase`
→ `runner.run_case()`
→ `MockOpenAIClient.stream_case()`
→ raw streaming chunks
→ `parse_streaming_chunks()`
→ `ParsedStreamMessage`

## 新增文件

- `src/infermatrix/parsers/stream_parser.py`
- `tests/test_stream_parser.py`

## 修改文件

- `src/infermatrix/parsers/__init__.py`
- `src/infermatrix/cli.py`
- `PROGRESS.md`

## 已实现能力

- [ ] 定义 `StreamParseError`
- [ ] 定义 `ParsedStreamMessage`
- [ ] 实现 `parse_streaming_chunks()`
- [ ] 支持收集 `delta.role`
- [ ] 支持收集多个 `delta.content`
- [ ] 支持合并 `merged_content`
- [ ] 支持提取 `finish_reason`
- [ ] 缺少 choices 时能明确失败
- [ ] delta 非法时能明确失败
- [ ] 缺少 assistant role 时能明确失败
- [ ] 缺少 content chunk 时能明确失败
- [ ] 缺少 finish_reason 时能明确失败
- [ ] CLI 对 streaming case 使用 stream parser
- [ ] pytest 全部通过
- [ ] CLI 手动验证通过

## 当前限制

阶段 C-2 只处理普通文本 streaming chunks。

暂不处理：

- streaming tool calls
- structured output JSON 解析
- JSON Schema 校验
- analyzer/checker
- Markdown / JSONL report

---

# 下一次进度更新模板

````markdown
## 进度记录：阶段 B - Mock Backend

### 日期

待填写

### 本次完成

- 

### 本次遇到的问题

- 

### 本次学到的概念

- 

### 已验证命令

```bash
pytest
infermatrix run examples/basic_chat.yaml
````

### 当前阻塞

*

### 下一步

*

```
```
