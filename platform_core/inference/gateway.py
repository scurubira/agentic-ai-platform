from __future__ import annotations

from typing import Any

import httpx
from litellm import acompletion

from platform_core.config.model_registry import ModelRegistry
from platform_core.config.settings import Settings
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
        }
        if target.provider.startswith("ollama"):
            kwargs["api_base"] = self._settings.ollama_base_url
        response = await acompletion(**kwargs)
        answer = str(response.choices[0].message.content or "").strip()
        return InferenceResult(
            answer=answer,
            physical_model=target.physical_model,
            public_model_name=target.public_name,
        )

    async def readiness(self, *, model_alias: str) -> dict[str, object]:
        target = self._registry.get(model_alias)
        if target.provider.startswith("ollama"):
            async with httpx.AsyncClient(timeout=self._settings.healthcheck_timeout_seconds) as client:
                response = await client.get(f"{self._settings.ollama_base_url}/api/tags")
                response.raise_for_status()
        return {"ok": True, "model_alias": model_alias, "physical_model": target.physical_model}
