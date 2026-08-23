from __future__ import annotations

from time import perf_counter
from typing import TypedDict
from uuid import uuid4

from agents.supervisor.graph import build_supervisor_graph
from platform_core.inference.types import InferenceGateway
from platform_core.memory.store import ConversationStore
from platform_core.observability.logging import get_logger

logger = get_logger(__name__)


class ChatResult(TypedDict):
    answer: str
    session_id: str
    model: str
    latency_ms: int


class ChatService:
    def __init__(
        self,
        conversation_store: ConversationStore,
        inference_gateway: InferenceGateway,
    ) -> None:
        self._conversation_store = conversation_store
        self._graph = build_supervisor_graph(inference_gateway)

    async def chat(
        self,
        *,
        message: str,
        session_id: str | None,
        model_alias: str,
    ) -> ChatResult:
        active_session_id = session_id or str(uuid4())
        history = self._conversation_store.load_messages(active_session_id)
        conversation = [*history, {"role": "user", "content": message}]
        started_at = perf_counter()
        result = await self._graph.ainvoke(
            {
                "session_id": active_session_id,
                "message": message,
                "model_alias": model_alias,
                "conversation": conversation,
            }
        )
        latency_ms = int((perf_counter() - started_at) * 1000)
        answer = result["answer"]
        self._conversation_store.save_turn(active_session_id, user_message=message, assistant_message=answer)
        logger.info(
            "chat_completed",
            extra={
                "session_id": active_session_id,
                "agent": "supervisor",
                "model_alias": model_alias,
                "physical_model": result["physical_model"],
                "latency_ms": latency_ms,
                "tool_calls": 0,
                "retrieval": False,
            },
        )
        return {
            "answer": answer,
            "session_id": active_session_id,
            "model": result["public_model_name"],
            "latency_ms": latency_ms,
        }
