"""Analyzers for InferMatrix.

analyzer/checker 负责判断解析后的模型输出是否满足 expected。

parser 负责“把原始响应变成结构化对象”。
analyzer 负责“判断结构化对象是否符合预期”。
"""

from infermatrix.analyzers.schema_checker import (
    SchemaCheckResult,
    check_json_schema,
)

__all__ = [
    "SchemaCheckResult",
    "check_json_schema",
]