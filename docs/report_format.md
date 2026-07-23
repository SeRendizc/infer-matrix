# Agent Eval Lab 报告格式

Agent Eval Lab 每次执行 Case 时生成两种报告：

* Markdown：供开发者阅读、调试和提交 GitHub Issue
* JSONL：供程序批量读取、过滤和比较

## Markdown

每次 Run 生成一个文件：

```text
runs/<run_id>.md
```

主要区块：

* Summary
* Case
* Features
* Checks
* Failure Reasons
* Parsed Output
* Raw Output
* Reproduction

## JSONL

所有 Run 追加到：

```text
runs/runs.jsonl
```

每一行是一份完整的 `RunReport` JSON Object。

JSONL 不使用外层数组，因此可以逐条追加和逐行读取。

## Verdict

报告 Verdict 只有两种：

* `pass`
* `fail`

计算规则：

* 任意 Check 为 `fail`，最终 Verdict 为 `fail`
* 没有失败 Check，最终 Verdict 为 `pass`
* `skip` 不视为失败

## Check Status

每个 Check 使用：

* `pass`
* `fail`
* `skip`

并包含：

* `name`
* `status`
* `reason`
* `details`

## Failure Stage

当前支持将以下失败阶段记录成 Check：

* `execution`
* `parsing`
* `analysis`

YAML 无法加载或无法通过 Case Schema 校验时，由于尚未产生合法 `EvalCase`，CLI 会直接输出错误，不生成正式 RunReport。
    