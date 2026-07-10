"""JSON Schema checker for structured outputs.

阶段 C-4 的目标：
检查 ParsedStructuredOutput.data 是否符合 case.expected.json_schema。

注意：
这个模块属于 analyzer/checker 层，不属于 parser 层。

parser 负责：
    JSON text → Python dict

schema checker 负责：
    Python dict + JSON Schema → pass / fail / skip

为什么要分开？
因为“是不是合法 JSON”和“是否符合 schema”是两个不同问题。

例如：

    {"status": "ok"}

这是合法 JSON object。

但如果 schema 要求必须有：

    status
    answer

那么它仍然会 schema validation 失败。
"""


from __future__ import annotations

from typing import Any, Literal

from jsonschema import ValidationError, validate
from pydantic import BaseModel, ConfigDict, Field

from infermatrix.cases import InferCase
from infermatrix.parsers.structured_output_parser import ParsedStructuredOutput


class SchemaCheckResult(BaseModel):
    """JSON Schema 检查结果。

    字段说明：
    - name: 检查项名称
    - status: pass / fail / skip
    - expected_schema: 使用的 JSON Schema
    - actual_data: 实际解析出的 structured output data
    - reason: 人能读懂的原因说明
    """

    model_config = ConfigDict(extra="forbid")

    name: str = "json_schema"
    status: Literal["pass", "fail", "skip"]
    expected_schema: dict[str, Any] | None = None
    actual_data: dict[str, Any] | None = None
    reason: str = Field(min_length=1)

    @property
    def passed(self) -> bool:
        """检查是否通过。"""
        return self.status == "pass"

    @property
    def failed(self) -> bool:
        """检查是否失败。"""
        return self.status == "fail"

    @property
    def skipped(self) -> bool:
        """检查是否跳过。"""
        return self.status == "skip"

def check_json_schema(case: InferCase, structured_output: ParsedStructuredOutput) -> SchemaCheckResult:
    """检查 structured output 是否符合 case.expected.json_schema。

    Args:
        case: 当前 InferCase。
        structured_output: 已经通过 structured output parser 解析出的对象。

    Returns:
        SchemaCheckResult: JSON Schema 检查结果。

    阶段 C-4 规则：
        - 如果 case.expected.json_schema_valid 不是 true，则跳过。
        - 如果没有配置 expected.json_schema，则跳过。
        - 如果 actual data 符合 schema，则 pass。
        - 如果 actual data 不符合 schema，则 fail，并给出 failure reason。

    注意：
        jsonschema.validate() 会在失败时抛 ValidationError。
        我们捕获它，并转换成 SchemaCheckResult(status="fail")。
    """

    should_validate = case.expected.json_schema_valid

    if not should_validate:
        return SchemaCheckResult(
            status="skip",
            expected_schema=case.expected.json_schema,
            actual_data=structured_output.data,
            reason="expected.json_schema_valid is not true; skipped JSON Schema check.",
        )

    schema = case.expected.json_schema

    if schema is None:
        return SchemaCheckResult(
            status="skip",
            expected_schema=None,
            actual_data=structured_output.data,
            reason="No expected.json_schema configured; skipped JSON Schema check.",
        )

    try:
        validate(instance=structured_output.data, schema=schema)
    except ValidationError as error:
        return SchemaCheckResult(
            status="fail",
            expected_schema=schema,
            actual_data=structured_output.data,
            reason=f"Structured output does not match JSON Schema: {error.message}",
        )

    return SchemaCheckResult(
        status="pass",
        expected_schema=schema,
        actual_data=structured_output.data,
        reason="Structured output matches expected JSON Schema.",
    )