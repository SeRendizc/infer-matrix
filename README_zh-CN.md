# InferMatrix

InferMatrix 是一个 Agentic LLM Systems 行为分析框架。

它关注 OpenAI-compatible 服务、流式响应、结构化输出和工具调用相互作用的接口层。

InferMatrix 不是一个通用模型基准。它旨在生成可复现案例、解析模型服务响应、验证工具调用和结构化输出行为，并生成可用于调试、文档编写和上游开源贡献的报告。

## 当前范围

Stage A 关注：

* Python 项目骨架
* YAML 案例定义
* CLI 入口点
* 案例加载器
* 基础 pytest 覆盖

## 路线图

* Mock OpenAI-compatible 后端
* 工具调用解析器
* 流式响应解析器
* JSON Schema 检查器
* Markdown / JSONL 报告
* OpenAI-compatible 端点适配器
* vLLM / SGLang 行为分析
