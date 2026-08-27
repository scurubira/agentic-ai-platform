from __future__ import annotations

from typing import Literal, TypedDict

import httpx

from platform_core.config.settings import Settings
from platform_core.errors import AppError

CatalogProvider = Literal["openrouter", "huggingface"]


class CatalogModel(TypedDict):
    provider: CatalogProvider
    model_id: str
    name: str
    description: str
    context_length: int | None
    input_price: str | None
    output_price: str | None
    downloads: int | None
    likes: int | None


class ModelCatalogService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def search(self, *, provider: CatalogProvider, query: str, limit: int) -> list[CatalogModel]:
        try:
            if provider == "openrouter":
                return await self._search_openrouter(query=query, limit=limit)
            return await self._search_huggingface(query=query, limit=limit)
        except httpx.HTTPError as exc:
            raise AppError(f"Could not query {provider} model catalog", status_code=502) from exc

    async def _search_openrouter(self, *, query: str, limit: int) -> list[CatalogModel]:
        headers = (
            {"Authorization": f"Bearer {self._settings.openrouter_api_key}"}
            if self._settings.openrouter_api_key
            else {}
        )
        async with httpx.AsyncClient(timeout=self._settings.model_catalog_timeout_seconds) as client:
            response = await client.get("https://openrouter.ai/api/v1/models", headers=headers)
            response.raise_for_status()
        normalized_query = query.casefold()
        results: list[CatalogModel] = []
        for item in response.json().get("data", []):
            model_id = str(item.get("id", ""))
            name = str(item.get("name", model_id))
            description = str(item.get("description", ""))
            if normalized_query and normalized_query not in f"{model_id} {name} {description}".casefold():
                continue
            pricing = item.get("pricing") or {}
            results.append(
                {
                    "provider": "openrouter",
                    "model_id": model_id,
                    "name": name,
                    "description": description,
                    "context_length": item.get("context_length"),
                    "input_price": pricing.get("prompt"),
                    "output_price": pricing.get("completion"),
                    "downloads": None,
                    "likes": None,
                }
            )
            if len(results) == limit:
                break
        return results

    async def _search_huggingface(self, *, query: str, limit: int) -> list[CatalogModel]:
        params: dict[str, str | int] = {
            "pipeline_tag": "text-generation",
            "sort": "trendingScore",
            "direction": -1,
            "limit": limit,
            "expand[]": "downloads,likes,pipeline_tag",
        }
        if query:
            params["search"] = query
        headers = (
            {"Authorization": f"Bearer {self._settings.huggingface_api_key}"}
            if self._settings.huggingface_api_key
            else {}
        )
        async with httpx.AsyncClient(timeout=self._settings.model_catalog_timeout_seconds) as client:
            response = await client.get("https://huggingface.co/api/models", params=params, headers=headers)
            response.raise_for_status()
        return [
            {
                "provider": "huggingface",
                "model_id": str(item["id"]),
                "name": str(item["id"]),
                "description": "Hugging Face text-generation model",
                "context_length": None,
                "input_price": None,
                "output_price": None,
                "downloads": item.get("downloads"),
                "likes": item.get("likes"),
            }
            for item in response.json()
        ]