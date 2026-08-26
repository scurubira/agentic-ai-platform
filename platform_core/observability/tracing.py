from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator, Protocol

from platform_core.config.settings import Settings


class ChatObservation(Protocol):
    def update(self, **kwargs: Any) -> object: ...


class TracingService(Protocol):
    @contextmanager
    def observe_chat(
        self,
        *,
        session_id: str,
        model_alias: str,
        message: str,
    ) -> Generator[ChatObservation | None]: ...

    def readiness(self) -> dict[str, object]: ...

    def shutdown(self) -> None: ...


class DisabledTracingService:
    @contextmanager
    def observe_chat(
        self,
        *,
        session_id: str,
        model_alias: str,
        message: str,
    ) -> Generator[None]:
        del session_id, model_alias, message
        yield None

    def readiness(self) -> dict[str, object]:
        return {"ok": False, "enabled": False, "backend": "langfuse"}

    def shutdown(self) -> None:
        return None


class LangfuseTracingService:
    def __init__(self, settings: Settings) -> None:
        if not settings.langfuse_public_key or not settings.langfuse_secret_key:
            raise ValueError("Langfuse credentials are required when LANGFUSE_ENABLED=true")

        from langfuse import Langfuse

        self._client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            base_url=settings.langfuse_base_url,
            environment=settings.app_env,
        )

    @contextmanager
    def observe_chat(
        self,
        *,
        session_id: str,
        model_alias: str,
        message: str,
    ) -> Generator[ChatObservation]:
        try:
            with self._client.start_as_current_observation(
                name="supervisor-chat",
                as_type="agent",
                input={"message": message},
                metadata={
                    "session_id": session_id,
                    "model_alias": model_alias,
                    "source": "agentic-platform",
                },
            ) as observation:
                yield observation
        finally:
            self._client.flush()

    def readiness(self) -> dict[str, object]:
        try:
            authenticated = self._client.auth_check()
        except Exception:
            authenticated = False
        return {
            "ok": authenticated,
            "enabled": True,
            "backend": "langfuse",
        }

    def shutdown(self) -> None:
        self._client.flush()
        self._client.shutdown()


def build_tracing_service(settings: Settings) -> TracingService:
    if settings.langfuse_enabled:
        return LangfuseTracingService(settings)
    return DisabledTracingService()