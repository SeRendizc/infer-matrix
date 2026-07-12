"""Shared report exceptions for InferMatrix."""


class ReportWriteError(RuntimeError):
    """报告无法安全写入文件时抛出。

    常见原因：

    - 输出目录无法创建
    - 目标文件无法写入
    - 同名 Markdown 报告已经存在
    - run_id 不能安全地作为文件名
    - 操作系统拒绝文件操作
    """