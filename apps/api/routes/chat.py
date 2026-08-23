from fastapi import APIRouter, Depends

from apps.api.dependencies.services import get_container
from apps.api.schemas.chat import ChatRequest, ChatResponse
from platform_core.container import AppContainer

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    container: AppContainer = Depends(get_container),
) -> ChatResponse:
    result = await container.chat_service.chat(
        message=payload.message,
        session_id=payload.session_id,
        model_alias=payload.model,
    )
    return ChatResponse.model_validate(result)
