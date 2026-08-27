from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from platform_core.errors import AppError

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)(?::-(.*?))?\}")
_ALIAS_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_DYNAMIC_PROVIDERS = {"huggingface", "openrouter"}


@dataclass(frozen=True)
class ModelTarget:
    alias: str
    physical_model: str
    provider: str

    @property
    def public_name(self) -> str:
        _, _, model_name = self.physical_model.partition("/")
        return model_name or self.physical_model


class ModelRegistry:
    def __init__(self, config_path: Path, dynamic_config_path: Path | None = None) -> None:
        self._config_path = config_path
        self._dynamic_config_path = dynamic_config_path
        self._models = self._load_models(config_path)
        dynamic_models = self._load_dynamic_models()
        self._dynamic_aliases = set(dynamic_models)
        self._models.update(dynamic_models)

    def list(self) -> list[ModelTarget]:
        return sorted(self._models.values(), key=lambda model: model.alias)

    def get(self, alias: str) -> ModelTarget:
        try:
            return self._models[alias]
        except KeyError as exc:
            raise AppError(f"Unknown model alias: {alias}", status_code=400) from exc

    def add(self, *, alias: str, provider: str, model_id: str) -> ModelTarget:
        normalized_alias = alias.strip().lower()
        normalized_provider = provider.strip().lower()
        normalized_model_id = model_id.strip().strip("/")
        if not _ALIAS_PATTERN.fullmatch(normalized_alias):
            raise AppError("Model alias must use lowercase letters, numbers, hyphens, or underscores", status_code=422)
        if normalized_provider not in _DYNAMIC_PROVIDERS:
            raise AppError("Provider must be openrouter or huggingface", status_code=422)
        if not normalized_model_id or "/" not in normalized_model_id:
            raise AppError("Model ID must include its organization, for example org/model", status_code=422)
        if normalized_alias in self._models:
            raise AppError(f"Model alias already exists: {normalized_alias}", status_code=409)
        if self._dynamic_config_path is None:
            raise AppError("Dynamic model registry is not configured", status_code=503)

        target = ModelTarget(
            alias=normalized_alias,
            physical_model=f"{normalized_provider}/{normalized_model_id}",
            provider=normalized_provider,
        )
        self._models[target.alias] = target
        self._dynamic_aliases.add(target.alias)
        self._save_dynamic_models()
        return target

    def _load_dynamic_models(self) -> dict[str, ModelTarget]:
        if self._dynamic_config_path is None or not self._dynamic_config_path.exists():
            return {}
        try:
            entries = json.loads(self._dynamic_config_path.read_text(encoding="utf-8"))
            return {
                str(entry["alias"]): ModelTarget(
                    alias=str(entry["alias"]),
                    physical_model=str(entry["physical_model"]),
                    provider=str(entry["provider"]),
                )
                for entry in entries
            }
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AppError("Dynamic model registry is invalid", status_code=500) from exc

    def _save_dynamic_models(self) -> None:
        assert self._dynamic_config_path is not None
        dynamic_models = [
            {
                "alias": model.alias,
                "physical_model": model.physical_model,
                "provider": model.provider,
            }
            for model in self.list()
            if model.alias in self._dynamic_aliases
        ]
        self._dynamic_config_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._dynamic_config_path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(dynamic_models, indent=2) + "\n", encoding="utf-8")
        temporary_path.replace(self._dynamic_config_path)

    def _load_models(self, config_path: Path) -> dict[str, ModelTarget]:
        raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        models: dict[str, ModelTarget] = {}
        for entry in raw_config.get("model_list", []):
            alias = str(entry["model_name"])
            params = entry.get("litellm_params", {})
            physical_model = self._interpolate_env(str(params["model"]))
            provider, _, _ = physical_model.partition("/")
            models[alias] = ModelTarget(alias=alias, physical_model=physical_model, provider=provider)
        return models

    def _interpolate_env(self, value: str) -> str:
        def replace(match: re.Match[str]) -> str:
            name, default = match.group(1), match.group(2)
            resolved = os.getenv(name, default)
            if resolved is None:
                raise AppError(f"Missing required environment variable: {name}", status_code=500)
            return resolved

        return _ENV_VAR_PATTERN.sub(replace, value)
