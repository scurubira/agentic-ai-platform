from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from litellm.exceptions import RateLimitError
from pytest import MonkeyPatch

from platform_core.config.model_registry import ModelRegistry
from platform_core.config.settings import Settings
from platform_core.errors import AppError
from platform_core.inference.gateway import LiteLLMInferenceGateway


def _openrouter_registry(tmp_path: Path) -> ModelRegistry:
    config_path = tmp_path / "litellm.yaml"
    config_path.write_text(
        "model_list:\n"
        "  - model_name: openrouter-free\n"
        "    litellm_params:\n"
        "      model: openrouter/openrouter/free\n",
        encoding="utf-8",
    )
    return ModelRegistry(config_path)


def test_openrouter_completion_passes_api_key(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    async def fake_completion(**kwargs: object) -> object:
        captured.update(kwargs)
        message = SimpleNamespace(content="Resposta gratuita")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    monkeypatch.setattr("platform_core.inference.gateway.acompletion", fake_completion)
    settings = Settings(OPENROUTER_API_KEY="test-key")
    gateway = LiteLLMInferenceGateway(settings, _openrouter_registry(tmp_path))

    result = asyncio.run(
        gateway.complete(
            model_alias="openrouter-free",
            conversation=[{"role": "user", "content": "Olá"}],
        )
    )

    assert captured["model"] == "openrouter/openrouter/free"
    assert captured["api_key"] == "test-key"
    assert captured["max_tokens"] == 4096
    assert result.answer == "Resposta gratuita"


def test_openrouter_completion_requires_api_key(tmp_path: Path) -> None:
    gateway = LiteLLMInferenceGateway(Settings(OPENROUTER_API_KEY=None), _openrouter_registry(tmp_path))

    with pytest.raises(AppError, match="OPENROUTER_API_KEY"):
        asyncio.run(
            gateway.complete(
                model_alias="openrouter-free",
                conversation=[{"role": "user", "content": "Olá"}],
            )
        )


def test_reasoning_alias_uses_openrouter_provider(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("REASONING_MODEL_ID", "qwen/qwen3-next-80b-a3b-thinking")
    registry = ModelRegistry(Path("litellm.yaml"))

    target = registry.get("reasoning")

    assert target.provider == "openrouter"
    assert target.physical_model == "openrouter/qwen/qwen3-next-80b-a3b-thinking"


def test_openrouter_rate_limit_returns_actionable_app_error(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    async def rate_limited_completion(**kwargs: object) -> object:
        del kwargs
        raise RateLimitError("upstream rate limit", llm_provider="openrouter", model="qwen/test")

    monkeypatch.setattr("platform_core.inference.gateway.acompletion", rate_limited_completion)
    gateway = LiteLLMInferenceGateway(Settings(OPENROUTER_API_KEY="test-key"), _openrouter_registry(tmp_path))

    with pytest.raises(AppError, match="temporarily rate-limited") as error:
        asyncio.run(
            gateway.complete(
                model_alias="openrouter-free",
                conversation=[{"role": "user", "content": "Olá"}],
            )
        )

    assert error.value.status_code == 429