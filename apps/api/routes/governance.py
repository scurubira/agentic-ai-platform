from fastapi import APIRouter, Depends, Response, status

from apps.api.dependencies.services import get_container
from apps.api.schemas.governance import EvalCreate, EvalRun, GuardrailCreate, GuardrailTest, GuardrailToggle
from platform_core.container import AppContainer

router = APIRouter(prefix="/api/v1/governance", tags=["governance"])


@router.get("")
async def snapshot(container: AppContainer = Depends(get_container)) -> dict[str, object]:
    return container.governance_service.snapshot()


@router.post("/evals", status_code=status.HTTP_201_CREATED)
async def create_eval(
    payload: EvalCreate,
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    return container.governance_service.create_eval(**payload.model_dump())


@router.post("/evals/{definition_id}/run")
async def run_eval(
    definition_id: str,
    payload: EvalRun,
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    return container.governance_service.run_eval(definition_id, **payload.model_dump())


@router.delete("/evals/{definition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_eval(definition_id: str, container: AppContainer = Depends(get_container)) -> Response:
    container.governance_service.delete_eval(definition_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/guardrails", status_code=status.HTTP_201_CREATED)
async def create_guardrail(
    payload: GuardrailCreate,
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    return container.governance_service.create_guardrail(**payload.model_dump())


@router.patch("/guardrails/{definition_id}")
async def toggle_guardrail(
    definition_id: str,
    payload: GuardrailToggle,
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    return container.governance_service.set_guardrail_enabled(definition_id, payload.enabled)


@router.delete("/guardrails/{definition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guardrail(definition_id: str, container: AppContainer = Depends(get_container)) -> Response:
    container.governance_service.delete_guardrail(definition_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/guardrails/test")
async def test_guardrails(
    payload: GuardrailTest,
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    return container.governance_service.test_guardrails(**payload.model_dump())