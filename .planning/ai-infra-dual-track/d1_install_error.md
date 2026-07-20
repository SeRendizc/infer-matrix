# D1 Install Error Log

## Attempt 1

- 现象：通过 PowerShell 变量把多行脚本传给 `bash -lc` 时，bash 中的 `ENV_DIR` 为空；安全检查输出 `Refusing to overwrite existing path:` 并退出。
- 影响：命令在 `mkdir`、venv 创建和下载前终止，没有建立或覆盖环境。
- 根因：跨 PowerShell/WSL 的多行命令参数边界不可靠。
- 修正：使用独立 `wsl_install_model_lab.sh`，由 `bash <script path>` 直接执行；不重复原调用方式。
