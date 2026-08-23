FROM ghcr.io/astral-sh/uv:0.8.3 AS uvbin

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_CERTS=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uvbin /uv /uvx /bin/

COPY pyproject.toml uv.lock README.md ./
COPY apps ./apps
COPY agents ./agents
COPY platform_core ./platform_core
COPY mcp_servers ./mcp_servers
COPY evals ./evals
COPY litellm.yaml ./litellm.yaml

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
