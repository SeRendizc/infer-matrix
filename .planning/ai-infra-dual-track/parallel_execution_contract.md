# 双线并行执行契约

## 目标

InferMatrix 与 Model Lab 从同一天开始并行推进，但采用不同授权模式：

- **Model Lab：教学优先、用户拥有核心。**
- **InferMatrix：Codex 自主推进外围工程与真实 evidence，用户按里程碑验收。**

任何一条线等待另一条线完成后才启动，都属于执行偏差。

## 每轮固定节奏

| 阶段 | Model Lab | InferMatrix |
|---|---|---|
| 计划 | 只选择一个概念与一个小实验 | 选择一个 P0 工程闭环 |
| 执行 | 先讲解，再由用户亲手写核心 | Codex 自主实现、测试、诊断、记录 |
| 验收 | 用户能解释机制与 shape | 测试、真实 wire/evidence、复现命令 |
| 汇报 | 学到了什么、下一小步 | 完成了什么、证据、下一 P0 |

## Model Lab 边界

Codex 可以自主处理：

- WSL/PyTorch 环境；
- config、CLI、测试夹具、日志、artifact writer；
- 用户完成核心后的测试补充、Code Review 和重构。

Codex 不得在教学与用户第一次尝试之前实现：

- attention、MHA、Transformer block、Decoder；
- training step 的核心 loss/data flow；
- generation、KV Cache；
- Profiler 结论和实验解释。

Lab 每一节采用：`概念 → 可观察例子 → 用户尝试 → Codex Review → 实验 → 用户复盘`。

## InferMatrix 边界

Codex 可持续自主推进：

- HTTP/SSE、protocol adapter、report、schema、CLI、测试和文档；
- vLLM/SGLang 环境与 smoke/evidence；
- semantic invariant、failure minimization、regression；
- 不涉及公司保密内容的项目整理。

用户只需在里程碑理解：系统目标、主要数据流、真实故障与结论，不要求逐行掌握外围代码。

## 当前并行状态（2026-07-19）

- Lab：D1 环境完成；D2 外围代码视为待讲解材料，暂停继续扩建；下一步从 next-token prediction 开始教学。
- InferMatrix：恢复 `phase-e1d`，先审计现有 streaming/report 未提交差异和测试，再继续真实 Chat streaming evidence。
