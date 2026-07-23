# D1 Verification Report

> Historical note: this document predates the rename from InferMatrix to Agent Eval Lab.

## Result

技术 Gate：**PASS**
Ownership Gate：**PENDING USER EXPLANATION**

## Fresh evidence

- Python executable：`/root/.venvs/infermatrix-model-lab/bin/python`
- PyTorch：`2.12.1+cu130`
- PyTorch module：新 venv 内，不来自 `/usr/local`
- CUDA available：`true`
- GPU：RTX 3060 Laptop，6144 MiB，capability `8.6`
- supported arch：包含 `sm_86`
- CUDA forward/backward：pass
- SDPA forward/backward：pass，output `[2, 4, 64, 64]`
- `torch.compile` correctness：pass，max absolute error `4.76837158203125e-07`

原始机器可读证据：`D:\infermatrix_model_lab\artifacts\d1_environment.json`

## Non-blocking warnings

- NumPy 尚未安装：D2 开发依赖阶段处理，不影响当前纯 Torch 验收。
- TF32 未开启：保留为 Week 3 的显式实验变量。
- 3060 SM 数量不足以采用某些 max-autotune GEMM 策略：属于硬件提示，不是 correctness failure。
