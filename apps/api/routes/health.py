from fastapi import APIRouter, Depends

from apps.api.dependencies.services import get_container
from platform_core.container import AppContainer

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    result = await container.readiness_service.check()
    return result
