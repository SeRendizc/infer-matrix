"""JSONL report writer for InferMatrix.

阶段 D-4 的目标：

    RunReport
        ↓
    Pydantic JSON-compatible data
        ↓
    单行 JSON
        ↓
    追加到 runs/runs.jsonl

JSONL 的含义是 JSON Lines。

规则：

- 一条 RunReport 占一行
- 每一行本身都是合法 JSON object
- 多次运行追加到同一个文件
- 不使用外层 JSON array

这个模块只负责序列化和文件追加。

它不负责：

- 执行 Case
- 调用 Backend
- 解析 Response
- 执行 Analyzer
- 构造 RunReport
"""

from __future__ import annotations

import json
from pathlib import Path

from infermatrix.reports.errors import ReportWriteError
from infermatrix.reports.models import RunReport


def write_jsonl_report(
    report: RunReport,
    output_file: str | Path = "runs/runs.jsonl",
) -> Path:
    """把一份 RunReport 追加到 JSONL 文件。

    Args:
        report:
            已经构造完成的统一运行报告。

        output_file:
            JSONL 输出文件路径。

            默认值：

                runs/runs.jsonl

    Returns:
        Path:
            最终写入的 JSONL 文件路径。

    Raises:
        ReportWriteError:
            父目录无法创建或文件无法写入。
    """

    output_path = Path(output_file)

    # 在文件系统操作前完成序列化。
    # 如果报告无法序列化，不会创建空文件或半成品目录。
    json_line = _serialize_jsonl_record(report)

    try:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
    except OSError as error:
        raise ReportWriteError(
            "Failed to create JSONL report directory "
            f"'{output_path.parent}': {error}"
        ) from error

    try:
        with output_path.open(
            mode="a",
            encoding="utf-8",
            newline="\n",
        ) as file:
            file.write(json_line)
            file.write("\n")
    except OSError as error:
        raise ReportWriteError(
            f"Failed to append JSONL report '{output_path}': {error}"
        ) from error

    return output_path


def _serialize_jsonl_record(report: RunReport) -> str:
    """把 RunReport 转换成单行 JSON。

    model_dump(mode="json")：

        把 datetime 等 Pydantic 类型转换成
        JSON 可以接受的字符串、数字、列表或对象。

    ensure_ascii=False：

        保留中文原文，不转换成 \\uXXXX。

    separators=(",", ":")：

        去掉 JSON 中不必要的空格，
        让一条运行记录保持紧凑。

    JSON 字符串中的真实换行符会被转义为 \\n，
    因此不会破坏“一条记录一行”的 JSONL 规则。
    """

    json_compatible_data = report.model_dump(
        mode="json",
    )

    return json.dumps(
        json_compatible_data,
        ensure_ascii=False,
        separators=(",", ":"),
    )