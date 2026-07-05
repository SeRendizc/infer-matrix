# InferMatrix 项目进度

## 当前阶段

阶段 A：项目骨架与 YAML Case Loader

## 当前状态

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

`pytest`

结果：

`1 passed`

说明：

测试文件 `tests/test_case_loader.py` 已成功验证 `load_case()` 可以正确读取 `examples/basic_chat.yaml`。

### 2. 检查 YAML 是否正确解析为 Python 对象

命令：

`python -c "from infermatrix.cases import load_case; c=load_case('examples/basic_chat.yaml'); print(c.model_dump())"`

结果摘要：

`case_id`、`backend`、`model`、`features`、`messages`、`expected` 和 `metadata` 都已被正确解析。

其中：

* `features.streaming` 为 `False`
* `features.tool_calling` 为 `False`
* `features.structured_output` 为 `False`
* `expected.contains_text` 为 `"InferMatrix"`

### 3. 运行 CLI

命令：

`infermatrix run examples/basic_chat.yaml`

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

`Field 'backend' requires a type annotation`

原因：

Pydantic 模型字段必须写成“字段名 + 类型 + 默认值”的形式。

错误写法示例：

`backend = Field(default="mock")`

正确写法：

`backend: str = Field(default="mock")`

解决方式：

为 `backend`、`model`、`features`、`messages`、`expected`、`metadata` 等字段补充明确类型注解。

### 问题 2：YAML 字段名和 Pydantic 模型字段名不一致

报错摘要：

`case_id Field required`

原因：

YAML 中字段名写成了 `case-id`，但 Pydantic 模型中字段名是 `case_id`。

解决方式：

统一字段名，使用：

`case_id: basic_chat_001`

### 问题 3：`expected` 写成了列表或字段拼写错误

报错或现象：

`expected` 无法正确解析，或者 `contains_text` 结果为 `None`。

原因：

YAML 中可能写成了：

`contains_test`

或者把 `expected` 写成了列表形式。

正确写法：

`expected:`
`  contains_text: "InferMatrix"`

解决方式：

确保 YAML 中的 `expected` 是一个对象，而不是列表；并且字段名必须是 `contains_text`。

### 问题 4：`feature` 和 `features` 字段名不一致

报错摘要：

`InferCase object has no attribute 'features'`

原因：

Pydantic 模型中字段写成了 `feature`，但 YAML、测试和 CLI 中使用的是 `features`。

解决方式：

统一使用复数形式：

`features: CaseFeatures = Field(default_factory=CaseFeatures)`

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

YAML case 文件作为输入。

`cases.py` 定义这个 case 应该长什么样。

`load_case()` 负责把 YAML 文件读取成经过校验的 Python 对象。

`cli.py` 负责把这个能力暴露成命令行工具。

`pytest` 负责验证 case loader 是否按预期工作。

当前阶段完成的是 InferMatrix 的第一层能力：定义和读取实验用例。

## 下一阶段

阶段 B：Mock OpenAI-compatible Backend

## 下一阶段目标

构建一个假的 OpenAI-compatible 后端，让 InferMatrix 在不依赖真实模型、不依赖 GPU、不依赖外部 API 的情况下，也能得到一个稳定、可控的模型响应。

## 为什么要先做 Mock Backend

真实模型有很多不稳定因素：

* 模型输出不确定
* API 可能限流
* 本地模型环境可能难装
* vLLM / SGLang 可能受 CUDA、显卡、依赖影响
* streaming 输出更难调试

Mock Backend 可以先隔离这些外部不确定性，让我们专注开发 parser、checker 和 report。

## 下一步准备创建的文件

* `src/infermatrix/clients/base.py`
* `src/infermatrix/clients/mock_openai.py`
* `tests/test_mock_client.py`

## 下一步能力目标

Mock Backend 第一版需要支持：

* 返回一个普通 chat completion 响应
* 响应内容中包含预期文本
* 响应结构尽量接近 OpenAI-compatible Chat Completions API
* 可以被 pytest 稳定测试

后续再扩展：

* tool call response
* streaming chunks
* structured output response
