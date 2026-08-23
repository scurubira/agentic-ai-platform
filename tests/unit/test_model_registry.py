from __future__ import annotations

from pathlib import Path

import pytest
from pytest import MonkeyPatch

from platform_core.config.model_registry import ModelRegistry
from platform_core.errors import AppError


def test_model_registry_interpolates_environment_variables(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "qwen-local")
    config_path = tmp_path / "litellm.yaml"
    config_path.write_text(
        "model_list:\n  - model_name: fast\n    litellm_params:\n      model: ollama_chat/${OLLAMA_MODEL:-fallback}\n",
        encoding="utf-8",
    )

    registry = ModelRegistry(config_path)

    target = registry.get("fast")
    assert target.physical_model == "ollama_chat/qwen-local"
    assert target.public_name == "qwen-local"


def test_model_registry_raises_for_missing_required_environment_variable(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    config_path = tmp_path / "litellm.yaml"
    config_path.write_text(
        "model_list:\n  - model_name: fast\n    litellm_params:\n      model: ollama_chat/${OLLAMA_MODEL}\n",
        encoding="utf-8",
    )

    with pytest.raises(AppError, match="Missing required environment variable: OLLAMA_MODEL"):
        ModelRegistry(config_path)
