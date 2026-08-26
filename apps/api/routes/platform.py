from fastapi import APIRouter, Depends

from apps.api.dependencies.services import get_container
from platform_core.container import AppContainer

router = APIRouter(prefix="/api/v1/platform", tags=["platform"])


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