"""Markdown renderer for Agent Eval Lab reports."""

from __future__ import annotations

import json
from typing import Any

from agent_eval_lab.reports.models import (
    ReportCheck,
    RunReport,
)


def render_markdown_report(
    report: RunReport,
) -> str:
    """把 RunReport 渲染成 Markdown 文本。"""

    sections = [
        _render_title(),
        _render_summary(report),
        _render_case(report),
        _render_features(report),
        _render_protocol_observations(
            report.protocol_observations
        ),
        _render_http_exchange(
            report.http_exchange
        ),
        _render_checks(report.checks),
        _render_failure_reasons(
            report.failure_reasons
        ),
        _render_parsed_output(
            report.parsed_output
        ),
        _render_raw_output(
            report.raw_output
        ),
        _render_reproduction(
            report.reproduction_command
        ),
    ]

    markdown = "\n\n".join(
        sections
    )

    return markdown.rstrip() + "\n"


def _render_title() -> str:
    """渲染报告标题。"""

    return "# Agent Eval Lab Run Report"


def _render_summary(
    report: RunReport,
) -> str:
    """渲染本次运行的概要信息。"""

    verdict = report.verdict.upper()

    return "\n".join(
        [
            "## Summary",
            "",
            "| Field | Value |",
            "|---|---|",
            (
                "| Run ID | "
                f"`{_escape_inline_code(report.run_id)}` |"
            ),
            (
                "| Created At | "
                f"`{report.created_at.isoformat()}` |"
            ),
            f"| Verdict | **{verdict}** |",
            (
                "| Response Type | "
                f"`{_escape_inline_code(report.response_type)}` |"
            ),
        ]
    )


def _render_case(
    report: RunReport,
) -> str:
    """渲染 Case、Backend 和 Protocol 信息。"""

    return "\n".join(
        [
            "## Case",
            "",
            "| Field | Value |",
            "|---|---|",
            (
                "| Case ID | "
                f"`{_escape_inline_code(report.case_id)}` |"
            ),
            (
                "| Case File | "
                f"`{_escape_inline_code(report.case_file)}` |"
            ),
            (
                "| Backend | "
                f"`{_escape_inline_code(report.backend)}` |"
            ),
            (
                "| Protocol | "
                f"`{_escape_inline_code(report.protocol)}` |"
            ),
            (
                "| Model | "
                f"`{_escape_inline_code(report.model)}` |"
            ),
        ]
    )


def _render_features(
    report: RunReport,
) -> str:
    """渲染当前 Case 开启的 Feature。"""

    lines = [
        "## Features",
        "",
        "| Feature | Enabled |",
        "|---|---|",
    ]

    for feature_name, enabled in sorted(
        report.features.items()
    ):
        enabled_text = (
            "true"
            if enabled
            else "false"
        )

        lines.append(
            "| "
            f"`{_escape_inline_code(feature_name)}` "
            f"| `{enabled_text}` |"
        )

    return "\n".join(lines)


def _render_protocol_observations(
    observations: list[dict[str, Any]],
) -> str:
    """渲染非致命协议兼容性偏差。"""

    lines = [
        "## Protocol Observations",
        "",
    ]

    if not observations:
        lines.append(
            "No protocol compatibility "
            "observations were recorded."
        )
        return "\n".join(lines)

    lines.append(
        _render_json_code_block(
            observations
        )
    )

    return "\n".join(lines)


def _render_http_exchange(
    exchange: dict[str, Any] | None,
) -> str:
    """渲染脱敏后的原始 HTTP Exchange。"""

    lines = [
        "## HTTP Exchange",
        "",
    ]

    if exchange is None:
        lines.append(
            "No HTTP exchange was recorded."
        )
        return "\n".join(lines)

    lines.append(
        _render_json_code_block(
            exchange
        )
    )

    return "\n".join(lines)


def _render_checks(
    checks: list[ReportCheck],
) -> str:
    """渲染 Analyzer 检查结果。"""

    lines = [
        "## Checks",
    ]

    if not checks:
        lines.extend(
            [
                "",
                (
                    "No analyzer checks "
                    "were recorded."
                ),
            ]
        )
        return "\n".join(lines)

    for check in checks:
        status = check.status.upper()

        lines.extend(
            [
                "",
                (
                    "### "
                    f"`{_escape_inline_code(check.name)}` "
                    f"— {status}"
                ),
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
                    _render_json_code_block(
                        check.details
                    ),
                ]
            )

    return "\n".join(lines)


def _render_failure_reasons(
    failure_reasons: list[str],
) -> str:
    """渲染最终失败原因。"""

    lines = [
        "## Failure Reasons",
        "",
    ]

    if not failure_reasons:
        lines.append("None.")
        return "\n".join(lines)

    for reason in failure_reasons:
        lines.append(
            f"- {reason}"
        )

    return "\n".join(lines)


def _render_parsed_output(
    parsed_output: dict[str, Any] | None,
) -> str:
    """渲染 Parser 输出。"""

    lines = [
        "## Parsed Output",
        "",
    ]

    if parsed_output is None:
        lines.append(
            "No parsed output was recorded."
        )
        return "\n".join(lines)

    lines.append(
        _render_json_code_block(
            parsed_output
        )
    )

    return "\n".join(lines)


def _render_raw_output(
    raw_output: (
        dict[str, Any]
        | list[dict[str, Any]]
        | None
    ),
) -> str:
    """渲染 Backend 协议原始输出。"""

    lines = [
        "## Raw Output",
        "",
    ]

    if raw_output is None:
        lines.append(
            "No raw output was recorded."
        )
        return "\n".join(lines)

    lines.append(
        _render_json_code_block(
            raw_output
        )
    )

    return "\n".join(lines)


def _render_reproduction(
    command: str,
) -> str:
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


def _render_json_code_block(
    value: Any,
) -> str:
    """把 Python 数据转换成格式化 JSON Code Block。"""

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


def _escape_inline_code(
    value: str,
) -> str:
    """避免字符串中的反引号破坏 Markdown。"""

    return value.replace(
        "`",
        "\\`",
    )