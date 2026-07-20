# Findings

## 已知事实与边界

- 当前只执行 D1：建立隔离的 WSL2 GPU/PyTorch 环境，不启动后续开发。
- 目标硬件为 RTX 3060 Laptop 6GB；Lab 配置必须根据实测调整。
- 不覆盖系统 Python、旧虚拟环境或 `/root/ai-infra-learning`；不在旧环境中原地升级 PyTorch。
- Model Lab 是模型机制学习主线；InferMatrix 是 serving/evidence harness。

## 2026-07-18 现场结果

- WSL：Ubuntu 22.04.5 LTS、WSL2 kernel `5.15.167.4`、默认用户 `root`。
- GPU passthrough：RTX 3060 Laptop、6144 MiB、driver `610.74`、compute capability `8.6`。
- WSL 系统 Python 3.10.12、pip 22.0.2；未发现 `uv` 或 `conda`。
- 系统 `nvcc` 为 CUDA 11.5；全局 PyTorch 为 `1.12.0+cu102`。
- 旧 PyTorch 只包含 `sm_37 sm_50 sm_60 sm_70` kernel，不支持 RTX 3060 的 `sm_86`。
- 实际 CUDA tensor 创建失败：`no kernel image is available for execution on the device`。因此不能复用旧环境。
- `/root/ai-infra-learning` 已存在，包含论文、DeepSeek-V2 和 `minimal_inference.py`；必须原样保留。
- `D:\infermatrix_model_lab` 已通过 `/mnt/d/infermatrix_model_lab` 正常挂载，当前只有规划文件。
- WSL 根文件系统可用约 905GB；D 盘可用约 127GB。

## 当前决策

- 新虚拟环境放在 WSL ext4，而不是覆盖 `/usr/local`，也不复用旧全局 site-packages。
- 项目仍保留在 `D:\infermatrix_model_lab`；环境与大型 cache 优先放在 WSL ext4，减少 `/mnt/d` 小文件 I/O 开销。
- 使用 PyTorch 官方当前 Linux CUDA wheel；版本和 index URL 在读取官方安装页后确定。
- 完整 CUDA toolkit 不是普通 PyTorch wheel 运行的前置条件；D1 暂不改系统 `nvcc 11.5`。

## D1 通过条件

- 新环境的 `torch` 不来自 `/usr/local/lib/python3.10/dist-packages`。
- `torch.cuda.is_available()` 为真，设备和 capability 正确。
- CUDA tensor forward/backward 成功，并能读取显存。
- 生成 `environment.json` 和可重复验证脚本。
- 用户能解释 Windows driver、PyTorch wheel runtime、系统 `nvcc` 的职责边界。

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| Python `-c` 经 PowerShell/bash 两层传递后引号丢失，出现 `NameError` | 1 | 改用独立 `.py` 诊断脚本，已得到明确结果 |
| 未匹配 shell glob 产生空路径并误扫当前目录 | 1 | 改用 literal directory 检查，已确认真实目录 |
| 旧 PyTorch CUDA tensor 报 `no kernel image is available for execution on the device` | 1 | 已确认 wheel 不含 `sm_86`；新建隔离的现代 PyTorch 环境，不原地修补 |
