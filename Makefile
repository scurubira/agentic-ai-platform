UV ?= $(HOME)/.local/bin/uv

setup:
	$(UV) sync

up:
	docker compose -f docker-compose.yml -f docker-compose.langfuse.yml up -d --build

down:
	docker compose -f docker-compose.yml -f docker-compose.langfuse.yml down --remove-orphans

dev:
	$(UV) run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

dev-observed:
	MODEL_BACKEND=litellm STATE_BACKEND=memory \
	LANGFUSE_ENABLED=true \
	LANGFUSE_PUBLIC_KEY=pk-lf-local-development-project \
	LANGFUSE_SECRET_KEY=sk-lf-local-development-project \
	LANGFUSE_BASE_URL=http://127.0.0.1:3000 \
	$(UV) run uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000

dev-stub:
	MODEL_BACKEND=stub STATE_BACKEND=memory \
	$(UV) run uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000

web:
	npm run --prefix apps/web dev

studio:
	MODEL_BACKEND=stub STATE_BACKEND=memory $(UV) run langgraph dev --port 2024

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check .
	$(UV) run mypy .

format:
	$(UV) run ruff format .

health:
	curl -sSf http://localhost:8000/health
