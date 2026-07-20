# InferMatrix 恢复审计（2026-07-19）

## 当前状态

- 分支：`phase-e1d`。
- 已修改 7 个业务文件，集中在 real chat smoke、pipeline、Chat Completions protocol 和 report。
- 正常 diff 与 `-w` diff 规模接近，说明约 1000 行差异不是单纯换行或空白变化，必须逐模块审查。
- `git diff --check` 未报告 whitespace error。
- Ruff baseline：pass。

## 无效测试运行

- 命令从 `C:\Users\ASUS` 启动，仅调用 venv Python，没有锁定 cwd/config/test path。
- pytest 因此收集到 `C:\Users\ASUS\AppData\Local\GrampsAIO64-5.1.3` 的测试，Gramps import 触发 `SystemExit`。
- 该结果不能用于判断 InferMatrix 是否通过或失败。
- 根因是 invocation scope，不是 InferMatrix 代码。
- 修正：工作目录固定为 `D:\infermatrix`，显式使用项目 `pyproject.toml` 与 `tests/`。

## 下一步审计顺序

1. 用正确 scope 运行 pytest 与 Ruff。
2. 先读 tests 与 protocol/pipeline diff，确定已实现行为和缺口。
3. 再审 report 大 diff，检查是否为数据模型迁移导致的机械变化。
4. 不覆盖或重写现有未提交代码；新增行为必须先有失败测试。
