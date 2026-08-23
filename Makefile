UV ?= $(HOME)/.local/bin/uv

setup:
	$(UV) sync

up:
	docker compose up -d --build

down:
	docker compose down --remove-orphans

dev:
	$(UV) run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check .
	$(UV) run mypy .

format:
	$(UV) run ruff format .

health:
	curl -sSf http://localhost:8000/health
