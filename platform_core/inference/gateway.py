from __future__ import annotations

from typing import Any

import httpx
from litellm import acompletion

from platform_core.config.model_registry import ModelRegistry
from platform_core.config.settings import Settings
from platform_core.errors import AppError
from platform_core.inference.types import InferenceResult


class StubInferenceGateway:
    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    async def complete(self, *, model_alias: str, conversation: list[dict[str, str]]) -> InferenceResult:
        target = self._registry.get(model_alias)
        latest_message = conversation[-1]["content"] if conversation else ""
        return InferenceResult(
            answer=f"Stub response for: {latest_message}",
            physical_model=target.physical_model,
            public_model_name=target.public_name,
        )

    async def readiness(self, *, model_alias: str) -> dict[str, object]:
        target = self._registry.get(model_alias)
        return {"ok": True, "model_alias": model_alias, "physical_model": target.physical_model}


class LiteLLMInferenceGateway:
    def __init__(self, settings: Settings, registry: ModelRegistry) -> None:
        self._settings = settings
        self._registry = registry

    async def complete(self, *, model_alias: str, conversation: list[dict[str, str]]) -> InferenceResult:
        target = self._registry.get(model_alias)
        kwargs: dict[str, Any] = {
            "model": target.physical_model,
            "messages": conversation,
            "timeout": self._settings.model_timeout_seconds,
            "max_tokens": self._settings.model_max_tokens,
        }
        if target.provider.startswith("ollama"):
            kwargs["api_base"] = self._settings.ollama_base_url
        if target.provider == "openrouter":
            if not self._settings.openrouter_api_key:
                raise AppError("OPENROUTER_API_KEY is required for OpenRouter models", status_code=503)
            kwargs["api_key"] = self._settings.openrouter_api_key
        if target.provider == "huggingface":
            if not self._settings.huggingface_api_key:
                raise AppError("HF_TOKEN is required for Hugging Face models", status_code=503)
            kwargs["api_key"] = self._settings.huggingface_api_key
        response = await acompletion(**kwargs)
        answer = str(response.choices[0].message.content or "").strip()
        return InferenceResult(
            answer=answer,
            physical_model=target.physical_model,
            public_model_name=target.public_name,
        )

    async def readiness(self, *, model_alias: str) -> dict[str, object]:
        target = self._registry.get(model_alias)
        if target.provider == "openrouter" and not self._settings.openrouter_api_key:
            return {
                "ok": False,
                "model_alias": model_alias,
                "physical_model": target.physical_model,
                "reason": "OPENROUTER_API_KEY is not configured",
            }
        if target.provider == "huggingface" and not self._settings.huggingface_api_key:
            return {
                "ok": False,
                "model_alias": model_alias,
                "physical_model": target.physical_model,
                "reason": "HF_TOKEN is not configured",
            }
        if target.provider.startswith("ollama"):
            async with httpx.AsyncClient(timeout=self._settings.healthcheck_timeout_seconds) as client:
                response = await client.get(f"{self._settings.ollama_base_url}/api/tags")
                response.raise_for_status()
        return {"ok": True, "model_alias": model_alias, "physical_model": target.physical_model}
