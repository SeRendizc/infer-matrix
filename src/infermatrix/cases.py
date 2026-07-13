"""Case definitions and loader for InferMatrix.

这个模块负责把 YAML case 文件读取成结构化的 Python 对象。

阶段 A：
- 支持普通 messages
- 支持 features
- 支持 expected
- 支持 metadata

阶段 B-2：
- 增加 tools 字段，用来描述 tool calling case 中可用的工具定义。
"""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class Message(BaseModel):
    """单条 chat message。

    role 表示消息角色。
    content 表示消息文本。
    """

    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant", "tool"]
    content: str


class TimeoutConfig(BaseModel):
    """真实 Backend 的 HTTP Timeout 配置。

    HTTPX 将 Timeout 分成四类：

    - connect：建立连接允许等待的时间
    - read：等待响应数据允许的时间
    - write：发送请求数据允许的时间
    - pool：等待连接池可用连接的时间

    模型推理可能耗时较长，因此 read 默认明显高于 connect。
    """

    model_config = ConfigDict(extra="forbid")

    connect: float = Field(default=5.0, gt=0)
    read: float = Field(default=120.0, gt=0)
    write: float = Field(default=30.0, gt=0)
    pool: float = Field(default=5.0, gt=0)


class BackendConfig(BaseModel):
    """InferMatrix 使用的 Backend 配置。

    provider 表示服务提供方式，而不是 API 协议。

    当前支持：

    - mock：进程内 Mock Backend
    - openai_compatible：真实 OpenAI-compatible HTTP 服务

    API Key 不直接写入 YAML，只保存环境变量名称。
    """

    model_config = ConfigDict(extra="forbid")

    provider: Literal[
        "mock",
        "openai_compatible",
    ] = "mock"

    base_url: AnyHttpUrl | None = None
    api_key_env: str | None = None

    timeout: TimeoutConfig = Field(
        default_factory=TimeoutConfig
    )

    @model_validator(mode="after")
    def validate_provider_configuration(
        self,
    ) -> "BackendConfig":
        """校验不同 Provider 所需的配置。"""

        if (
            self.provider == "openai_compatible"
            and self.base_url is None
        ):
            raise ValueError(
                "backend.base_url is required when "
                "backend.provider is 'openai_compatible'."
            )

        if self.provider == "mock":
            if self.base_url is not None:
                raise ValueError(
                    "backend.base_url must not be configured "
                    "for the in-process mock backend."
                )

            if self.api_key_env is not None:
                raise ValueError(
                    "backend.api_key_env must not be configured "
                    "for the in-process mock backend."
                )

        return self


class ProtocolConfig(BaseModel):
    """InferMatrix 与 Backend 交互时使用的 API 协议。

    同一个 Backend 可能同时支持多种协议，因此 Protocol
    必须与 Backend 分开建模。
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "chat_completions",
        "responses",
    ] = "chat_completions"


class CaseFeatures(BaseModel):
    """一个 case 启用了哪些能力。

    这些字段不会直接调用模型，而是告诉 runner/client：
    当前 case 期望模拟或测试哪些行为。
    """

    model_config = ConfigDict(extra="forbid")

    streaming: bool = False
    tool_calling: bool = False
    structured_output: bool = False


class CaseExpected(BaseModel):
    """一个 case 的预期结果。

    expected 用来描述我们希望模型输出满足什么条件。

    注意：
    parser 不直接使用 expected。
    expected 主要给 analyzer/checker 使用。
    """

    model_config = ConfigDict(extra="forbid")

    contains_text: str | None = None
    json_schema_valid: bool | None = None
    json_schema: dict[str, Any] | None = None
    tool_name: str | None = None
    arguments_schema_valid: bool | None = None


class InferCase(BaseModel):
    """InferMatrix 的核心 case 对象。

    YAML case 会被读取并校验成这个对象。

    字段说明：
    - case_id: case 的唯一标识
    - backend: 使用哪个 backend，目前主要是 mock
    - model: 模型名
    - features: 当前 case 涉及哪些能力
    - messages: 输入消息
    - tools: tool calling case 中的工具定义
    - expected: 预期结果
    - metadata: 补充信息，mock 阶段常用来控制假响应
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)

    backend: BackendConfig = Field(default_factory=BackendConfig)

    protocol: ProtocolConfig = Field(default_factory=ProtocolConfig)

    model: str = Field(
        default="mock-model",
        min_length=1,
    )

    features: CaseFeatures = Field(default_factory=CaseFeatures)
    messages: list[Message] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    expected: CaseExpected = Field(default_factory=CaseExpected)
    metadata: dict[str, Any] = Field(default_factory=dict)


def load_case(path: str | Path) -> InferCase:
    """从 YAML 文件读取一个 InferMatrix case。

    Args:
        path: YAML case 文件路径。

    Returns:
        InferCase: 通过 Pydantic 校验后的 case 对象。

    Raises:
        FileNotFoundError: case 文件不存在。
        ValueError: case 文件为空。
        pydantic.ValidationError: YAML 内容不符合 InferCase schema。
    """

    case_path = Path(path)

    if not case_path.exists():
        raise FileNotFoundError(f"Case file not found: {case_path}")

    with case_path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file)

    if raw is None:
        raise ValueError(f"Case file is empty: {case_path}")

    return InferCase.model_validate(raw)