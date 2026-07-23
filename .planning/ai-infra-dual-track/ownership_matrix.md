# 人机分工与 Ownership Gate

> Historical note: this document predates the rename from InferMatrix to Agent Eval Lab.

## 1. 标签定义

| 标签 | 含义 | Codex 可以做什么 | 本人必须做什么 |
|---|---|---|---|
| `U` | User-owned core | 给原理、接口、提示、Code Review、测试建议 | 先写核心实现，解释算法，处理关键 bug |
| `P` | Pair-owned | 搭骨架、提出实验方案、协助诊断和重构 | 选择方案、运行实验、判断结果、写结论 |
| `C` | Codex-owned support | 直接实现、补测试、整理文档和自动化 | 理解接口、验证输出、能说明它为何存在 |
| `F` | Frozen | 仅修阻塞性 bug | 不投入新增学习或开发时间 |

## 2. 模块分工

### 必须本人亲手（U）

- scaled dot-product causal attention；
- multi-head reshape 与 tensor shape；
- Decoder block/forward 的核心数据流；
- language-model loss 与 train step；
- autoregressive generation 主循环；
- KV Cache 的存储、更新和增量 decode；
- cached/uncached correctness 判断；
- TTFT、TPOT、ITL、throughput、peak memory 的定义；
- Profiler trace 的瓶颈归因；
- 最终 failure root-cause 和实验结论。

Codex 不应在本人第一次尝试前直接贴出这些模块的完整答案。卡住超过 45 分钟后，按“概念提示 → 伪代码 → 局部补丁”逐级帮助。

### 结对完成（P）

- WSL/PyTorch/CUDA 环境选择与验证；
- SDPA、mixed precision、`torch.compile` 对照设计；
- Profiler harness 的观测范围；
- vLLM 启动参数和显存约束；
- prefix caching、chunked prefill、concurrency 实验矩阵；
- InferMatrix semantic invariant；
- 真实 failure 的最小化与分层定位；
- 技术复盘的结构和简历叙事。

### Codex 可直接代写（C）

- `pyproject.toml`、配置 dataclass/Pydantic、CLI；
- tokenizer/data loader 的非研究性实现；
- checkpoint、日志、seed、artifact writer；
- HTTP/SSE 适配、序列化、脱敏、环境指纹；
- pytest fixtures、参数化测试、边界样例；
- benchmark orchestration、重复实验、统计汇总；
- JSONL/Markdown/CSV 输出与画图；
- CI、README 框架、复现命令和文档排版；
- 不涉及核心算法判断的重构和类型修复。

### 冻结（F）

- Web UI、数据库、在线 dashboard；
- 新的通用 Agent workflow；
- Ollama、LM Studio 等额外 backend；
- Responses API 扩展，直到真实 Chat/streaming evidence 完成；
- 自研通用性能 benchmark；
- 完整 RFC 级 SSE 扩展；
- 只增加视觉效果、不增加证据质量的报告功能。

## 3. Ownership Gate

一个任务只有同时满足以下条件，才可以被计为“本人掌握”或写入简历：

1. **Draw**：不看代码画出数据流、关键 shape 或组件关系。
2. **Explain**：解释为什么这样设计，以及一个替代方案的 trade-off。
3. **Predict**：修改一个变量前，先预测正确性、速度或显存变化。
4. **Debug**：能根据失败现象提出至少两个候选原因和排查顺序。
5. **Trace**：简历中的数字能追溯到命令、环境和 artifact。

若任一项失败，该模块可以标为“项目已实现”，但不能标为“本人深入掌握”。

## 4. 每次协作流程

1. Codex 提供一张 Concept Card：目标、原理、接口、验收、常见坑。
2. 本人先口述方案；`U` 任务由本人完成第一次实现。
3. Codex 做 Code Review，补外围代码、测试和小范围修复。
4. Codex 生成可重复实验；本人亲自运行并先写观察。
5. Codex 质疑结论、检查混杂变量，双方迭代。
6. 本人用 5 句话记录：做了什么、为什么、数据、结论、限制。

## 5. Git 与证据规则

- 不自动 commit；每个 Gate 后由本人决定是否提交。
- 不把当前 `phase-e1d` 的未提交修改与新实验机械混在同一提交。
- 每次实验必须保存：commit/hash 或 working-tree 状态、命令、配置、环境、原始指标、结论。
- Codex 生成的代码正常进入仓库，但简历不按“代码行数”声明个人贡献。
