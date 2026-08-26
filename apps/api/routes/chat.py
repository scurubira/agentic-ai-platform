from fastapi import APIRouter, Depends, HTTPException

from apps.api.dependencies.services import get_container
from apps.api.schemas.chat import ChatRequest, ChatResponse
from platform_core.container import AppContainer

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    container: AppContainer = Depends(get_container),
) -> ChatResponse:
    guardrail_result = container.governance_service.test_guardrails(text=payload.message, stage="input")
    if not guardrail_result["allowed"]:
        names = ", ".join(
            violation["name"]
            for violation in guardrail_result["violations"]
            if violation["action"] == "block"
        )
        raise HTTPException(status_code=422, detail=f"Content blocked by guardrail: {names}")
    result = await container.chat_service.chat(
        message=payload.message,
        session_id=payload.session_id,
        model_alias=payload.model,
    )
    return ChatResponse.model_validate(result)
