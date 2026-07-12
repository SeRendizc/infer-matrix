"""Markdown report file writer for InferMatrix.

阶段 D-3 的目标：

    RunReport
        ↓
    render_markdown_report()
        ↓
    Markdown string
        ↓
    write_markdown_report()
        ↓
    runs/<run_id>.md

这个模块负责文件系统操作：

- 创建输出目录
- 根据 run_id 生成文件名
- 使用 UTF-8 写入 Markdown
- 默认阻止覆盖同名报告
- 返回最终文件路径

它不负责：

- 执行 Case
- 调用 Backend
- 解析 Response
- 执行 Analyzer
- 构造 RunReport
"""


from __future__ import annotations

import re
from pathlib import Path

from infermatrix.reports.markdown_renderer import render_markdown_report
from infermatrix.reports.models import RunReport
from infermatrix.reports.errors import ReportWriteError


_SAFE_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def write_markdown_report(
    report: RunReport,
    output_dir: str | Path = "runs",
    *,
    overwrite: bool = False,
) -> Path:
    """把一份 RunReport 写成 Markdown 文件。

    Args:
        report:
            已构造完成的统一运行报告。

        output_dir:
            报告输出目录。

            默认是项目根目录下的 runs：

                runs/<run_id>.md

        overwrite:
            是否允许覆盖同名报告。

            默认为 False。因为每次 run 应该有唯一 run_id，
            同名文件通常表示调用方重复写入或 run_id 使用错误。

    Returns:
        Path:
            最终生成的 Markdown 文件路径。

    Raises:
        ReportWriteError:
            run_id 不安全、目录创建失败、文件已经存在，
            或其他文件系统操作失败。
    """

    output_path = Path(output_dir)
    file_name = _build_report_file_name(report.run_id)
    report_path = output_path / file_name

    # 先渲染，再执行文件系统操作。
    # 如果 renderer 本身发生异常，不会留下空目录或半成品文件。
    markdown = render_markdown_report(report)

    try:
        output_path.mkdir(
            parents=True,
            exist_ok=True,
        )
    except OSError as error:
        raise ReportWriteError(
            f"Failed to create report directory '{output_path}': {error}"
        ) from error

    # x 模式表示“只创建新文件”。
    # 文件已经存在时，Python 会抛 FileExistsError。
    #
    # w 模式表示覆盖写入，只在 overwrite=True 时使用。
    mode = "w" if overwrite else "x"

    try:
        with report_path.open(
            mode=mode,
            encoding="utf-8",
            newline="\n",
        ) as file:
            file.write(markdown)
    except FileExistsError as error:
        raise ReportWriteError(
            f"Report file already exists: {report_path}. "
            "Pass overwrite=True to replace it."
        ) from error
    except OSError as error:
        raise ReportWriteError(
            f"Failed to write Markdown report '{report_path}': {error}"
        ) from error

    return report_path


def _build_report_file_name(run_id: str) -> str:
    """根据 run_id 生成安全的 Markdown 文件名。

    允许：

    - 英文字母
    - 数字
    - 下划线
    - 连字符
    - 点

    拒绝：

    - /
    - \\
    - ..
      作为路径跳转的一部分
    - 其他可能改变文件路径的字符

    正常自动生成的 run_id：

        run_89fb7c...

    可以直接通过检查。
    """

    if not _SAFE_RUN_ID_PATTERN.fullmatch(run_id):
        raise ReportWriteError(
            "run_id contains characters that cannot be used safely "
            f"in a report filename: {run_id!r}"
        )

    return f"{run_id}.md"