from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, Query

from apps.api.dependencies.services import get_container
from apps.api.schemas.agents import AgentInstall
from apps.api.schemas.models import ModelCreate
from platform_core.container import AppContainer

router = APIRouter(prefix="/api/v1/platform", tags=["platform"])


@router.get("/agents")
async def list_agents(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    return {
        "installed": [asdict(agent) for agent in container.agent_registry.list_installed()],
        "catalog": container.agent_registry.list_catalog(),
    }


@router.post("/agents/{agent_id}/install", status_code=201)
async def install_agent(
    agent_id: str,
    payload: AgentInstall,
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    container.model_registry.get(payload.model_alias)
    return asdict(container.agent_registry.install(agent_id=agent_id, model_alias=payload.model_alias))


@router.delete("/agents/{agent_id}", status_code=204)
async def remove_agent(
    agent_id: str,
    container: AppContainer = Depends(get_container),
) -> None:
    container.agent_registry.remove(agent_id)


@router.get("/models/discover")
async def discover_models(
    provider: Literal["openrouter", "huggingface"],
    query: str = Query(default="", max_length=120),
    limit: int = Query(default=20, ge=1, le=50),
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    models = await container.model_catalog_service.search(provider=provider, query=query.strip(), limit=limit)
    return {"models": models}


@router.post("/models", status_code=201)
async def add_model(
    payload: ModelCreate,
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    model = container.model_registry.add(
        alias=payload.alias,
        provider=payload.provider,
        model_id=payload.model_id,
    )
    return {
        "alias": model.alias,
        "name": model.public_name,
        "provider": model.provider,
        "default": model.alias == container.settings.default_model_alias,
    }


@router.get("/overview")
async def overview(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    settings = container.settings
    return {
        "environment": settings.app_env,
        "agent": {
            "name": "supervisor",
            "routes": ["direct", "rag", "sql", "tools"],
        },
        "models": [
            {
                "alias": model.alias,
                "name": model.public_name,
                "provider": model.provider,
                "default": model.alias == settings.default_model_alias,
            }
            for model in container.model_registry.list()
        ],
        "services": {
            "inference": {"backend": settings.model_backend},
            "memory": {"backend": settings.state_backend},
            "observability": {
                "backend": "langfuse",
                "enabled": settings.langfuse_enabled,
                "url": settings.langfuse_base_url,
            },
            "mcp": {"servers": container.mcp_gateway.list_capabilities()},
        },
    }