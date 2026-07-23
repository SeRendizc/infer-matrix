# 小型开源模型调试桥接计划

> Historical note: this document predates the rename from InferMatrix to Agent Eval Lab.

## 结论

后半程应加入小型开源模型调试，但它不是第三个独立项目，而是 Model Lab 与 InferMatrix 的桥：

```text
手写最小 Transformer / KV Cache
→ 在小型真实模型上观察相同机制
→ 用 vLLM 提供真实服务
→ InferMatrix 固化 wire、semantic invariant 和 failure evidence
```

## 模型选择

### 第一选择：Qwen3-0.6B

- 用于第一轮真实 decoder-only 模型调试。
- 规模适合 RTX 3060 6GB，架构与手写 Transformer/KV Cache 的知识迁移更直接。
- 目标：Transformers eager 推理、module hook、hidden/QKV shape、cached/uncached logits、Profiler。

### 第二选择：Qwen3.5-0.8B（可选 frontier case）

- 官方模型约 0.8B，权重仓库约 1.77GB，支持 Transformers、vLLM、SGLang。
- 架构含 Gated DeltaNet、Gated Attention、MTP 和 vision encoder，不适合作为第一个“对照手写 Transformer”的模型。
- 官方当前说明要求 vLLM main/nightly；因此只在稳定 Qwen3-0.6B 链路之后使用。
- 6GB 显存必须使用 text-only/`--language-model-only`、短 `--max-model-len`，不能照抄 262K context 示例。

## 插入综合计划的位置

- D1–D7：不下载真实模型；先完成最小 Transformer、训练与 overfit。
- D8–D14：在手写 KV Cache 正确性通过后，加入 Qwen3-0.6B cached/uncached 对照和 layer/shape inspection。
- D15–D21：对 Qwen3-0.6B 做 PyTorch Profiler；同时由 vLLM serve，InferMatrix 收集真实 non-streaming/streaming evidence。
- D22–D28：若稳定链路已完成，再尝试 Qwen3.5-0.8B 作为新架构/新 backend compatibility case。

## 用户必须亲手理解

- Hugging Face config 如何映射到 layers、hidden size、heads、KV heads；
- prompt 的 prefill 与逐 token decode；
- `past_key_values` 的 shape 和 cached/uncached 语义一致性；
- hook/Profiler 观察到的现象与手写 Lab 的对应关系；
- 为什么缩短 context 会降低 KV cache 显存，而不会减少模型权重显存。

## Codex 接管

- 模型下载/cache 路径、环境隔离和显存 smoke；
- hook/trace/metrics 脚手架、图表和证据落盘；
- vLLM 启动命令、健康检查、InferMatrix cases；
- OOM/依赖冲突诊断、回归测试和文档。

## 明确不做

- 现在立即下载模型；
- 一上来 fine-tune/LoRA；
- 同时接入多个模型家族；
- 把调用 `generate()` 包装成新的 Demo 项目；
- 为追求长上下文在 6GB 显存上硬撑官方最大 context。

## 官方来源（2026-07-19 核对）

- https://huggingface.co/Qwen/Qwen3-0.6B
- https://huggingface.co/Qwen/Qwen3.5-0.8B
- https://qwenlm.github.io/blog/qwen3/
