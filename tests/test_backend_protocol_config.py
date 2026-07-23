"""Tests for Backend and Protocol configuration."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_eval_lab.cases import (
    BackendConfig,
    EvalCase,
    ProtocolConfig,
    TimeoutConfig,
    load_case,
)


def test_existing_mock_case_uses_explicit_backend_and_protocol() -> None:
    """迁移后的 Mock Case 应使用独立 Backend 与 Protocol。"""

    case = load_case(
        Path("examples/basic_chat.yaml")
    )

    assert case.backend.provider == "mock"
    assert case.backend.base_url is None
    assert case.backend.api_key_env is None

    assert case.protocol.type == (
        "chat_completions"
    )


def test_openai_compatible_backend_requires_base_url() -> None:
    """真实 OpenAI-compatible Backend 必须配置 base_url。"""

    with pytest.raises(
        ValidationError,
        match="base_url",
    ):
        BackendConfig(
            provider="openai_compatible"
        )


def test_openai_compatible_backend_accepts_endpoint() -> None:
    """真实 Backend 配置应保留 Endpoint 和 API Key 环境变量名。"""

    config = BackendConfig(
        provider="openai_compatible",
        base_url="http://127.0.0.1:8000/v1",
        api_key_env="AGENT_EVAL_API_KEY",
    )

    assert config.provider == (
        "openai_compatible"
    )
    assert str(config.base_url).startswith(
        "http://127.0.0.1:8000"
    )
    assert config.api_key_env == (
        "AGENT_EVAL_API_KEY"
    )


def test_timeout_values_must_be_positive() -> None:
    """Timeout 不能为零或负数。"""

    with pytest.raises(ValidationError):
        TimeoutConfig(read=0)


def test_mock_backend_rejects_http_configuration() -> None:
    """进程内 Mock Backend 不应包含真实连接参数。"""

    with pytest.raises(
        ValidationError,
        match="base_url",
    ):
        BackendConfig(
            provider="mock",
            base_url="http://localhost:8000/v1",
        )


def test_responses_protocol_is_valid_configuration() -> None:
    """Responses 可以被配置，但本阶段还不执行。"""

    protocol = ProtocolConfig(
        type="responses"
    )

    assert protocol.type == "responses"


def test_unknown_protocol_is_rejected() -> None:
    """未知协议应在 Case 加载阶段被拒绝。"""

    with pytest.raises(ValidationError):
        ProtocolConfig(
            type="unknown_protocol"
        )


def test_complete_real_backend_case_can_be_validated() -> None:
    """真实 Backend Case 应通过 EvalCase Schema。"""

    case = EvalCase.model_validate(
        {
            "case_id": "real_chat_001",
            "backend": {
                "provider": "openai_compatible",
                "base_url": (
                    "http://127.0.0.1:8000/v1"
                ),
                "api_key_env": (
                    "AGENT_EVAL_API_KEY"
                ),
            },
            "protocol": {
                "type": "chat_completions",
            },
            "model": (
                "Qwen/Qwen2.5-1.5B-Instruct"
            ),
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                }
            ],
        }
    )

    assert case.backend.provider == (
        "openai_compatible"
    )
    assert case.protocol.type == (
        "chat_completions"
    )