"""Markdown renderer for InferMatrix reports.

阶段 D-2 的目标：

    RunReport
        ↓
    render_markdown_report()
        ↓
    Markdown string

这个模块只负责“渲染”。

它不负责：

- 执行 Case
- 调用 Backend
- 解析 Response
- 执行 Analyzer
- 创建目录
- 写入文件

文件写入会由后续 Writer 模块负责。
"""

from __future__ import annotations

import json
from typing import Any

from infermatrix.reports.models import ReportCheck, RunReport


def render_markdown_report(report: RunReport) -> str:
    """把 RunReport 渲染成 Markdown 文本。

    Args:
        report:
            已经构造完成的统一运行报告。

    Returns:
        str:
            完整 Markdown 文本。

    设计目标：

    - 人类可读
    - 输出结构稳定
    - 保留 Raw Output
    - 保留 Parsed Output
    - 清楚展示每个检查项
    - 包含复现命令
    """

    sections = [
        _render_title(),
        _render_summary(report),
        _render_case(report),
        _render_features(report),
        _render_checks(report.checks),
        _render_failure_reasons(report.failure_reasons),
        _render_parsed_output(report.parsed_output),
        _render_raw_output(report.raw_output),
        _render_reproduction(report.reproduction_command),
    ]

    # 每个 section 自己不负责添加多余的首尾空白。
    # 在这里统一用两个换行连接 Markdown 区块。
    markdown = "\n\n".join(sections)

    # Markdown 文件通常应以换行符结束。
    return markdown.rstrip() + "\n"


def _render_title() -> str:
    """渲染报告标题。"""

    return "# InferMatrix Run Report"


def _render_summary(report: RunReport) -> str:
    """渲染本次运行的概要信息。"""

    verdict = report.verdict.upper()

    return "\n".join(
        [
            "## Summary",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Run ID | `{_escape_inline_code(report.run_id)}` |",
            f"| Created At | `{report.created_at.isoformat()}` |",
            f"| Verdict | **{verdict}** |",
            f"| Response Type | `{_escape_inline_code(report.response_type)}` |",
        ]
    )


def _render_case(report: RunReport) -> str:
    """渲染 Case 和 Backend 信息。"""

    return "\n".join(
        [
            "## Case",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Case ID | `{_escape_inline_code(report.case_id)}` |",
            f"| Case File | `{_escape_inline_code(report.case_file)}` |",
            f"| Backend | `{_escape_inline_code(report.backend)}` |",
            f"| Model | `{_escape_inline_code(report.model)}` |",
        ]
    )


def _render_features(report: RunReport) -> str:
    """渲染当前 Case 开启的 Feature。"""

    lines = [
        "## Features",
        "",
        "| Feature | Enabled |",
        "|---|---|",
    ]

    for feature_name, enabled in sorted(report.features.items()):
        enabled_text = "true" if enabled else "false"

        lines.append(
            f"| `{_escape_inline_code(feature_name)}` | `{enabled_text}` |"
        )

    return "\n".join(lines)


def _render_checks(checks: list[ReportCheck]) -> str:
    """渲染 Analyzer 检查结果。

    每个检查项单独成为一个三级标题。

    不使用一个很宽的 Markdown Table，
    因为 reason 和 details 可能很长。
    """

    lines = ["## Checks"]

    if not checks:
        lines.extend(
            [
                "",
                "No analyzer checks were recorded.",
            ]
        )
        return "\n".join(lines)

    for check in checks:
        status = check.status.upper()

        lines.extend(
            [
                "",
                f"### `{_escape_inline_code(check.name)}` — {status}",
                "",
                check.reason,
            ]
        )

        if check.details:
            lines.extend(
                [
                    "",
                    "Details:",
                    "",
                    _render_json_code_block(check.details),
                ]
            )

    return "\n".join(lines)


def _render_failure_reasons(failure_reasons: list[str]) -> str:
    """渲染最终失败原因。

    failure_reasons 只包含 status=fail 的检查原因。
    """

    lines = ["## Failure Reasons", ""]

    if not failure_reasons:
        lines.append("None.")
        return "\n".join(lines)

    for reason in failure_reasons:
        lines.append(f"- {reason}")

    return "\n".join(lines)


def _render_parsed_output(
    parsed_output: dict[str, Any] | None,
) -> str:
    """渲染 Parser 输出。"""

    lines = ["## Parsed Output", ""]

    if parsed_output is None:
        lines.append("No parsed output was recorded.")
        return "\n".join(lines)

    lines.append(_render_json_code_block(parsed_output))

    return "\n".join(lines)


def _render_raw_output(
    raw_output: (
        dict[str, Any]
        | list[dict[str, Any]]
        | None
    ),
) -> str:
    """渲染 Backend 原始输出。

    Runner 在产生响应前失败时，raw_output 可能为 None。
    """

    lines = [
        "## Raw Output",
        "",
    ]

    if raw_output is None:
        lines.append("No raw output was recorded.")
        return "\n".join(lines)

    lines.append(_render_json_code_block(raw_output))

    return "\n".join(lines)


def _render_reproduction(command: str) -> str:
    """渲染复现命令。"""

    return "\n".join(
        [
            "## Reproduction",
            "",
            "```bash",
            command,
            "```",
        ]
    )


def _render_json_code_block(value: Any) -> str:
    """把 Python 数据转换成格式化 JSON Code Block。

    ensure_ascii=False：
        中文不会变成 \\u4e2d 一类转义文本。

    indent=2：
        报告更容易阅读。

    default=str：
        遇到 datetime 等 JSON 原生不支持的对象时，
        使用它们的字符串表示，避免渲染器直接崩溃。
    """

    json_text = json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        default=str,
    )

    return "\n".join(
        [
            "```json",
            json_text,
            "```",
        ]
    )


def _escape_inline_code(value: str) -> str:
    """避免字符串中的反引号破坏 Markdown Inline Code。"""

    return value.replace("`", "\\`")