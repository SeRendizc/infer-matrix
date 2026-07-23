# D1 Install Decision

> Historical note: this document predates the rename from InferMatrix to Agent Eval Lab.

## 2026-07-18

- 使用隔离环境：`/root/.venvs/infermatrix-model-lab`。
- 使用 WSL 系统 Python 3.10 创建 venv，但禁止继承 system site-packages。
- Model Lab 安装 PyTorch `2.12.1` 的官方 CUDA 13.0 wheel；只安装当前需要的 `torch`，不额外安装 torchvision/torchaudio。
- 选择依据：PyTorch 官方 current/previous-version 页面提供 Linux CUDA 13.0 wheel；Python 3.10 满足当前 stable 的最低版本。
- RTX 3060 属于 Ampere，目标 capability `sm_86`；安装后必须以实际 `torch.cuda.get_arch_list()` 和 forward/backward 验证，不能只看版本号。
- 暂不修改系统 CUDA toolkit 11.5；普通 wheel 运行依赖 wheel runtime 与 Windows NVIDIA driver，而不是系统 `nvcc`。
- vLLM 后续使用独立 serving venv，避免其 PyTorch pin 与 Model Lab 冲突。

官方来源：

- https://pytorch.org/get-started/locally/
- https://pytorch.org/get-started/previous-versions/
