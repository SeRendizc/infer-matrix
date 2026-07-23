# InferMatrix × Model Lab：四周 AI Infra 双线冲刺

> Historical note: this document predates the rename from InferMatrix to Agent Eval Lab.

> 状态：执行中（D2 技术验收通过，Ownership Gate 待完成）
> 周期：2026-07-19 ～ 2026-08-15（28 天）
> 主线：Model Lab 学习与实验；InferMatrix 负责真实 serving、诊断与证据固化

## 1. 成功标准

四周结束时必须拿到四类可验证产物，而不是只完成代码量：

1. **模型原理闭环**：本人实现最小 Decoder-only Transformer、causal attention、训练循环、autoregressive generation 和 KV Cache。
2. **推理优化闭环**：完成 eager、SDPA、混合精度、`torch.compile` 的受控对照，并用 PyTorch Profiler 解释至少一个瓶颈。
3. **真实 serving 闭环**：InferMatrix 对真实 vLLM 完成 non-streaming、streaming、原始 wire evidence、环境指纹和 semantic invariant 检查。
4. **故障证据闭环**：形成至少一个 `failure → reproduction → diagnosis → fix/workaround → regression test` 案例。

最终可交付：

- 一个可复现的 Model Lab 仓库；
- 一个带真实 backend evidence 的 InferMatrix；
- 一份 5～8 页技术复盘；
- 一组可以本人完整答辩的简历 bullet；
- 如遇到真实上游问题，形成 issue 或 PR 草稿，不强求为了数量提交。

## 2. 时间与优先级

- 建议投入：工作日 2～3 小时，周末 4～6 小时；总计约 80～100 小时。
- 本人时间分配：Model Lab 核心 60%，真实引擎实验 25%，InferMatrix 架构理解与验收 15%。
- Codex 的代码量可以主要落在 InferMatrix 和实验外围，但不能代替本人完成核心学习门禁。
- 若某日未完成，不整体顺延：先删除 P2 任务，保证每周 Gate 按时完成。

优先级：

- **P0**：本周 Gate 所需，必须完成。
- **P1**：增强证据质量，时间允许就完成。
- **P2**：可选，不得阻塞 P0/P1。

## 3. 四周日历

### Week 1｜7/19–7/25：模型正确性 + 真实 non-streaming

| Day | Model Lab | InferMatrix | 主责 | 当日验收 |
|---|---|---|---|---|
| D1 | **完成**：建立现代 WSL PyTorch/CUDA 环境；验证 CUDA tensor、版本和显存 | 冻结当前脏工作区基线，记录 149 tests 状态 | P | 本人能解释 driver、CUDA runtime、PyTorch wheel 三者关系 |
| D2 | **技术验收通过；Ownership Gate 待完成**：建目录、配置、byte tokenizer、shape tests | 整理真实 endpoint 所需配置 | C | Lab `pytest` 跑通；本人能说明每个目录职责 |
| D3 | 手写 scaled dot-product causal attention | Codex 补测试和 shape/property fixtures | U | 对照朴素 reference，forward/backward 数值与 shape 正确 |
| D4 | 手写 MHA、MLP、Block、Decoder forward | Codex 补配置、初始化和测试外围 | U/P | 本人画出 `[B,T] → [B,T,V]` 全链路 |
| D5 | 手写 loss、optimizer、train/eval step | Codex 写 CLI、checkpoint、日志 | U/P | 小 batch loss 连续下降，无 device 假设 |
| D6 | tiny corpus overfit；保存基线指标 | Codex 自动生成曲线和环境记录 | P | 固定样本过拟合；能解释 train/eval 与 seed |
| D7 | 复盘模型与 tensor shape | 跑真实 vLLM non-streaming smoke/evidence | P | 生成可重放请求、raw response、report、environment |

**Week 1 Gate**：本人独立讲清 attention、causal mask、残差、训练目标；Lab 能 overfit；InferMatrix 留下一份真实 non-streaming evidence bundle。

### Week 2｜7/26–8/1：KV Cache + streaming 语义

| Day | Model Lab | InferMatrix | 主责 | 当日验收 |
|---|---|---|---|---|
| D8 | 手写无 cache autoregressive generation | Codex 写稳定 benchmark harness | U/C | greedy 输出可复现；定义首 token 与后续 token 的计时边界 |
| D9 | 手写每层 KV Cache 数据结构和增量 decode | Codex 只给接口、测试和 review，不直接给完整算法 | U | 能说明 cache shape、增长维度和显存复杂度 |
| D10 | cached/uncached logits 与 token 序列一致性测试 | Codex 补随机化和边界测试 | U/C | 多组 seed、prompt 长度下通过 tolerance |
| D11 | 测 prefill/decode latency、tokens/s、peak memory | Codex 写采集、warmup、重复实验与汇总 | P/C | 能解释同步、warmup、均值/P50/P95 的影响 |
| D12 | 阅读 streaming 对用户可见延迟的意义 | 完成 Chat Completions streaming adapter | P/C | raw SSE frame、chunk、merged output 均保留 |
| D13 | 将 prefill/decode 事件映射到 serving 观察 | 增加 `[DONE]`、finish_reason、usage、chunk order 等 invariant | P | 至少一个人为破坏 case 能稳定失败并指出原因 |
| D14 | KV Cache 口头答辩与周复盘 | 固化 streaming evidence bundle | U/P | 不看代码解释为何 cache 改变计算量但不应改变语义 |

**Week 2 Gate**：本人实现并答辩 KV Cache；有 cached/uncached 正确性和性能证据；InferMatrix 真实 streaming 链路闭环。

### Week 3｜8/2–8/8：优化、Profiler 与 serving 特性

| Day | Model Lab | InferMatrix | 主责 | 当日验收 |
|---|---|---|---|---|
| D15 | 朴素 attention 对照 PyTorch SDPA | Codex 生成参数矩阵和结果表 | U/P | 正确性一致；能解释 SDPA backend dispatch |
| D16 | FP32、FP16/BF16 对照 | Codex 处理实验编排、显存和日志 | P/C | 区分数值误差、速度、显存变化；不虚构硬件不支持结果 |
| D17 | eager 对照 `torch.compile`，分离冷启动与稳态 | Codex 加 compile/warmup 标签 | P/C | 报告 compile cost、steady-state，不只报单次耗时 |
| D18 | PyTorch Profiler trace 与 top operators | Codex 写 profiler harness 和 trace 导出 | P | 本人指出一个瓶颈，并用 trace 证据而非猜测解释 |
| D19 | 学习 prefix caching 的命中条件 | vLLM prefix caching 开/关对照 | P | 固定 prompt 设计可重复实验，记录 cache/latency 指标 |
| D20 | 学习 batch/concurrency 对 prefill/decode 的影响 | chunked prefill 或 concurrency 对照，二选一 | P | 只改变一个主变量，有环境与命令记录 |
| D21 | 汇总结论、列出混杂变量 | Codex 生成图表初稿和 evidence index | U/C | 本人写 5 条“数据—结论—限制”陈述 |

**Week 3 Gate**：至少一份 profiler trace、一个经过证据支持的瓶颈结论、一组 vLLM serving 特性对照实验。

### Week 4｜8/9–8/15：真实故障、跨层证据与作品包装

| Day | Model Lab | InferMatrix | 主责 | 当日验收 |
|---|---|---|---|---|
| D22 | 选择一个语义或性能异常 | 构造最小 failure case | U/P | failure 可连续复现 3 次，输入和环境固定 |
| D23 | 分析模型侧/运行时侧可能原因 | 定位 parser、protocol、backend 或配置层 | U/P | 写出已排除项、根因证据、修复或 workaround |
| D24 | 补回归实验 | 增加 regression test 与 evidence | P/C | 修复前失败、修复后通过，证据不被覆盖 |
| D25 | 若 vLLM 已稳定，跑最小 SGLang 对照；否则深挖 vLLM | 统一 invariant 结果 | P | 不以“接入更多 backend”代替深度 |
| D26 | 整理实验卡片与关键图 | Codex 生成 evidence index、复现命令和报告框架 | C/P | 新环境按 README 能找到完整复现入口 |
| D27 | 本人写技术复盘初稿与项目解释 | Codex 编辑文档、精炼简历 bullet | U/C | 所有数字可追溯到 artifacts；无不可答辩表述 |
| D28 | 30 分钟模拟答辩、补知识缺口 | 冻结 v0.1 evidence release 范围 | U/P | 通过最终 Ownership Gate，列出后续而非继续加功能 |

**Week 4 Gate**：完成一个真实 failure chain、一个可复现 evidence release 和一次本人独立项目答辩。

## 4. 降级规则

若时间或环境受阻，按以下顺序降级：

1. 取消 SGLang 对照，继续把 vLLM failure chain 做深。
2. `chunked prefill` 与 concurrency 只保留一个。
3. 取消非核心报告美化和额外 feature combination。
4. GPU 环境临时失败时，先在 CPU 完成模型正确性；但真实 vLLM evidence 不得用 mock 冒充。
5. 不得删除：Transformer、KV Cache、Profiler、真实 streaming、真实 failure chain。

## 5. 每周固定检查

每周最后一天只回答五个问题：

1. 本周本人亲手实现了哪个核心机制？
2. 哪个结论有原始数据或 trace 支持？
3. 哪段代码主要由 Codex 生成，本人需要理解到什么层级？
4. 哪个功能应冻结而不是继续完善？
5. 当前产物能否形成一条不夸大的简历 bullet？

## 6. 官方参考入口

- vLLM installation：https://docs.vllm.ai/en/stable/getting_started/installation/index.html
- PyTorch SDPA：https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.scaled_dot_product_attention.html
- PyTorch `sdpa_kernel`：https://docs.pytorch.org/docs/stable/generated/torch.nn.attention.sdpa_kernel.html
- PyTorch compile profiling：https://docs.pytorch.org/docs/stable/user_guide/torch_compiler/torch.compiler_profiling_torch_compile.html
