# InferMatrix 范围与双项目证据契约

## 1. 当前事实基线（2026-07-18）

- 分支：`phase-e1d`。
- 工作区已有未提交业务修改，主要位于 streaming protocol、pipeline、report 和 real smoke case；新规划不得覆盖它们。
- 当前实现已经包括 case、mock、parser/analyzer、Markdown/JSONL report、HTTPX transport、redaction、SSE wire decoder、OpenAI-compatible client。
- 当前唯一应该继续完成的协议任务：Chat Completions streaming integration。
- 旧 `.planning/project-feasibility-review` 反映的是早期 14 tests 阶段，仅保留作历史记录。

## 2. InferMatrix 在双项目中的定位

InferMatrix 不是 Model Lab 的训练框架，也不是新的 serving engine。它只承担四件事：

1. 以统一 case 调用真实 OpenAI-compatible backend；
2. 保留 request、HTTP、SSE、protocol、parsed output 的分层证据；
3. 检查 streaming/tool/structured output 等语义 invariant；
4. 把实验环境、结果和故障最小复现组织为可分享 evidence bundle。

Model Lab 负责回答“模型和推理机制为什么如此”；InferMatrix 负责回答“真实服务到底发生了什么，如何复现并证明”。

## 3. 四周允许新增的范围

### P0

- 完成当前 E-1D2 streaming adapter；
- vLLM non-streaming 和 streaming smoke；
- backend/model/engine/CUDA/PyTorch/GPU 等 environment fingerprint；
- semantic trace 与基础 invariant；
- evidence bundle index 和 reproduction command；
- 一个真实 failure chain 和 regression case。

### P1

- prefix caching 实验元数据接入；
- 将 Model Lab 指标作为附件纳入 evidence index；
- vLLM/SGLang 相同 case 的一次最小对照。

### P2

- 更细粒度的错误分类；
- 自动生成 issue 草稿；
- 额外的结果图表。

### 明确冻结

- Responses/Open Responses；
- 更多 backend 集合；
- 自己实现完整 load benchmark；
- Web、数据库、在线监控；
- 与真实证据无关的抽象、异步接口复制和报告美化。

## 4. 松耦合 artifact contract

两个仓库不直接互相 import。Model Lab 通过目录 artifact 与 InferMatrix 对接：

```text
artifacts/<experiment_id>/
├── manifest.json       # 实验名称、代码版本、配置、时间
├── environment.json    # OS、Python、PyTorch、CUDA、GPU
├── metrics.jsonl       # 原始逐次测量，不只保存汇总
├── summary.json        # 聚合指标与单位
├── trace.json          # 可选：Profiler Chrome trace
├── notes.md            # 本人观察、结论、限制
└── figures/            # 派生图表，可重新生成
```

最低 schema 约定：

- 所有时间显式标注单位；
- 区分 warmup、compile、steady-state；
- 记录 batch、prompt length、generated length、dtype、device；
- 记录 seed 和重复次数；
- summary 不代替 raw metrics；
- `notes.md` 的结论必须引用具体 metric/trace。

InferMatrix 可以读取或链接这些 artifact，但不负责更改原始数据。

## 5. 完成定义

InferMatrix 四周阶段完成，不以 feature 数量判断，而以以下检查为准：

- 一条命令重放真实 non-streaming case；
- 一条命令重放真实 streaming case；
- 报告能从 raw wire 定位到 semantic verdict；
- 敏感 header/query 已脱敏；
- 环境足以解释主要差异；
- 至少一个失败有稳定复现、根因证据和 regression；
- README 当前状态与代码一致。
