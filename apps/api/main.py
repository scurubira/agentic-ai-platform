from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.routes.chat import router as chat_router
from apps.api.routes.governance import router as governance_router
from apps.api.routes.health import router as health_router
from apps.api.routes.platform import router as platform_router
from apps.api.routes.wiki import router as wiki_router
from platform_core.config.settings import Settings
from platform_core.container import build_container
from platform_core.errors import AppError
from platform_core.observability.logging import configure_logging, get_logger
from platform_core.observability.middleware import RequestContextMiddleware, RequestSizeLimitMiddleware


def create_app() -> FastAPI:
    settings = Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = build_container()
        await container.startup()
        app.state.container = container
        yield
        await container.shutdown()

    application = FastAPI(title="agentic-ai-platform", version="0.1.0", lifespan=lifespan)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(RequestSizeLimitMiddleware, max_body_size=settings.max_request_size_bytes)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    application.include_router(chat_router)
    application.include_router(governance_router)
    application.include_router(platform_router)
    application.include_router(wiki_router)

    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "application_error",
            extra={
                "path": str(request.url.path),
                "request_id": getattr(request.state, "request_id", None),
                "error": str(exc),
            },
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            extra={
                "path": str(request.url.path),
                "request_id": getattr(request.state, "request_id", None),
            },
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return application


configure_logging()
logger = get_logger(__name__)
app = create_app()
