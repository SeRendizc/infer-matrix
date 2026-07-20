# 2026-07-19 Continuation Checkpoint

## 已确认状态

- `infermatrix_model_lab` 已由用户亲手完成第一版 multi-head causal self-attention。
- Model Lab 的 shape、causal behavior、CPU backward、CUDA forward/backward 验收通过；全量 `14 passed`，Ruff 通过。
- Model Lab 已首次推送至 public GitHub `SeRendizc/infermatrix-model-lab`，commit `f583110`。
- Lab 核心仍由用户亲手实现；Codex 继续负责测试、外围工程、实验编排和 review。

## 双线下一步

- Lab：先完成 Attention ownership gate，然后学习并实现 MLP；Normalization 与 residual block 后续接入。
- InferMatrix：优先完成真实 OpenAI-compatible SSE P0，即完整 SSE response body -> frames -> Chat Completions chunks -> `RunResult`，并保留脱敏 `HttpExchange`。
- P0 只证明真实协议闭环，不声称已经测得增量 TTFT/ITL；增量到达时间属于后续 transport P1。

## 边界

- 不扩展更多 mock-only feature。
- 不先做 Responses API 大改。
- 不把 Model Lab 的 microbenchmark 冒充 serving throughput。
- 第一条高价值证据仍是可复现的真实 vLLM/SGLang backend failure chain。
