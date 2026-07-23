# Progress

> Historical note: this document predates the rename from InferMatrix to Agent Eval Lab.

## 2026-07-18｜规划建立

- 用户确认采用四周 Codex-assisted 双线冲刺。
- Model Lab 为模型机制学习主线；InferMatrix 为真实 serving/evidence harness。
- 明确 `U/P/C/F` 人机分工、四周 Gate、降级规则和 artifact contract。

## 2026-07-18｜D1 环境完成

- 建立 `/root/.venvs/infermatrix-model-lab`，PyTorch `2.12.1+cu130`。
- RTX 3060 `sm_86`、CUDA forward/backward、SDPA、`torch.compile` 均通过。
- 用户理解 GPU 可见性、PyTorch wheel kernel 与系统 `nvcc` 的边界。

## 2026-07-19｜D2 执行偏差与修正

- Codex 过度解释“全部交给你”，在教学前搭建了 Lab 配置/data/tests 外围，并事后要求用户回答陌生目录。
- 用户明确指出授权重点是 InferMatrix 非核心板块；Lab 必须先教会再由用户亲手完成核心。
- 当前 Lab 未实现 attention、Transformer、training loop 或 KV Cache；现有外围保留为待讲解材料，不继续自动扩建。

## 2026-07-19｜恢复双线并行

- 新增 `parallel_execution_contract.md`：Lab 教学优先，InferMatrix 自主推进。
- 每轮必须同时报告两条线，禁止把综合计划执行成串行项目。
- Lab 当前：从 next-token prediction 开始教学。
- InferMatrix 当前：审计 `phase-e1d` 的 streaming/report 未提交差异，恢复真实 backend P0。

## Errors Encountered

- 早期 WSL 内联脚本发生跨 shell 引号和 glob 问题，已改用独立脚本。
- D2 setuptools package discovery 与 Ruff 格式问题已修复并记录在 Lab progress。
- 协作流程错误：Lab 先施工后教学。修正为教学前置，并将规则写入综合计划。
