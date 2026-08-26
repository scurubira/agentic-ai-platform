from __future__ import annotations

from dataclasses import dataclass

from agents.supervisor.service import ChatService
from mcp_servers.news.server import NewsMCPServer
from platform_core.config.model_registry import ModelRegistry
from platform_core.config.settings import Settings
from platform_core.inference.gateway import LiteLLMInferenceGateway, StubInferenceGateway
from platform_core.inference.types import InferenceGateway
from platform_core.mcp.gateway import MCPGateway
from platform_core.memory.store import InMemoryConversationStore, PostgresConversationStore
from platform_core.observability.logging import get_logger
from platform_core.observability.tracing import TracingService, build_tracing_service

logger = get_logger(__name__)
ConversationStore = InMemoryConversationStore | PostgresConversationStore


@dataclass
class ReadinessService:
    settings: Settings
    inference_gateway: InferenceGateway
    conversation_store: ConversationStore
    tracing_service: TracingService

    async def check(self) -> dict[str, object]:
        inference_check = await self.inference_gateway.readiness(model_alias=self.settings.default_model_alias)
        database_ok = True
        if isinstance(self.conversation_store, PostgresConversationStore):
            try:
                self.conversation_store.create_tables()
            except Exception:
                database_ok = False
        return {
            "status": "ready" if inference_check["ok"] and database_ok else "degraded",
            "checks": {
                "inference": inference_check,
                "database": {"ok": database_ok, "backend": self.settings.state_backend},
                "observability": self.tracing_service.readiness(),
            },
        }


@dataclass
class AppContainer:
    settings: Settings
    model_registry: ModelRegistry
    inference_gateway: InferenceGateway
    conversation_store: ConversationStore
    mcp_gateway: MCPGateway
    chat_service: ChatService
    readiness_service: ReadinessService
    tracing_service: TracingService

    async def startup(self) -> None:
        if isinstance(self.conversation_store, PostgresConversationStore):
            self.conversation_store.create_tables()
        logger.info(
            "container_started",
            extra={
                "agent": "supervisor",
                "model_alias": self.settings.default_model_alias,
            },
        )

    async def shutdown(self) -> None:
        self.tracing_service.shutdown()
        logger.info("container_stopped")


def build_container() -> AppContainer:
    settings = Settings()
    model_registry = ModelRegistry(settings.model_config_path)
    inference_gateway: InferenceGateway = (
        StubInferenceGateway(model_registry)
        if settings.model_backend == "stub"
        else LiteLLMInferenceGateway(settings, model_registry)
    )
    conversation_store: ConversationStore = (
        PostgresConversationStore.from_url(settings.database_url)
        if settings.state_backend == "postgres"
        else InMemoryConversationStore()
    )
    mcp_gateway = MCPGateway()
    tracing_service = build_tracing_service(settings)
    chat_service = ChatService(
        conversation_store=conversation_store,
        inference_gateway=inference_gateway,
        settings=settings,
        tracing_service=tracing_service,
    )
    readiness_service = ReadinessService(
        settings=settings,
        inference_gateway=inference_gateway,
        conversation_store=conversation_store,
        tracing_service=tracing_service,
    )
    return AppContainer(
        settings=settings,
        model_registry=model_registry,
        inference_gateway=inference_gateway,
        conversation_store=conversation_store,
        mcp_gateway=mcp_gateway,
        chat_service=chat_service,
        readiness_service=readiness_service,
        tracing_service=tracing_service,
    )
