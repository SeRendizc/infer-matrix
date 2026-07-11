"""Analyzers for InferMatrix.

Analyzer / checker 负责判断 parser 输出的结构化对象是否满足 case.expected。

职责关系：

    raw response
        ↓
    parser
        ↓
    parsed object
        ↓
    analyzer
        ↓
    pass / fail / skip
"""

from infermatrix.analyzers.schema_checker import (
    SchemaCheckResult,
    check_json_schema,
)
from infermatrix.analyzers.tool_call_checker import (
    ToolCallCheckError,
    ToolCallCheckResult,
    check_tool_call,
)

__all__ = [
    "SchemaCheckResult",
    "check_json_schema",
    "ToolCallCheckError",
    "ToolCallCheckResult",
    "check_tool_call",
]