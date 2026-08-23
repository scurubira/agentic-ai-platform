from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from platform_core.errors import AppError

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)(?::-(.*?))?\}")


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
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._models = self._load_models(config_path)

    def get(self, alias: str) -> ModelTarget:
        try:
            return self._models[alias]
        except KeyError as exc:
            raise AppError(f"Unknown model alias: {alias}", status_code=400) from exc

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
            return os.getenv(name, default or "")

        return _ENV_VAR_PATTERN.sub(replace, value)
