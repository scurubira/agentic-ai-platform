from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from apps.api.main import create_app
from mcp_servers.news.server import NewsMCPServer
from platform_core.config.model_catalog import ModelCatalogService


def test_health_and_ready_endpoints(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "stub")
    monkeypatch.setenv("STATE_BACKEND", "memory")
    monkeypatch.setenv("LANGFUSE_ENABLED", "false")

    with TestClient(create_app()) as client:
        health_response = client.get("/health")
        ready_response = client.get("/ready")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert ready_response.status_code == 200
    assert ready_response.json()["status"] == "ready"
    assert ready_response.json()["checks"]["observability"] == {
        "ok": False,
        "enabled": False,
        "backend": "langfuse",
    }


def test_platform_overview_exposes_sanitized_inventory(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "stub")
    monkeypatch.setenv("STATE_BACKEND", "memory")

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/platform/overview")

    payload = response.json()
    assert response.status_code == 200
    assert payload["agent"]["name"] == "supervisor"
    assert {model["alias"] for model in payload["models"]} == {"fast", "openrouter-free", "reasoning"}
    assert payload["services"]["memory"] == {"backend": "memory"}
    assert "password" not in response.text.lower()


def test_model_discovery_returns_normalized_catalog(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "stub")
    monkeypatch.setenv("STATE_BACKEND", "memory")

    async def fake_search(
        self: ModelCatalogService,
        *,
        provider: str,
        query: str,
        limit: int,
    ) -> list[dict[str, object]]:
        del self
        assert (provider, query, limit) == ("openrouter", "qwen", 5)
        return [
            {
                "provider": "openrouter",
                "model_id": "qwen/qwen3-8b",
                "name": "Qwen 3 8B",
                "description": "Reasoning model",
                "context_length": 131072,
                "input_price": "0.0000001",
                "output_price": "0.0000002",
                "downloads": None,
                "likes": None,
            }
        ]

    monkeypatch.setattr(ModelCatalogService, "search", fake_search)

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/platform/models/discover?provider=openrouter&query=qwen&limit=5")

    assert response.status_code == 200
    assert response.json()["models"][0]["model_id"] == "qwen/qwen3-8b"


def test_added_model_appears_in_platform_inventory(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "stub")
    monkeypatch.setenv("STATE_BACKEND", "memory")
    monkeypatch.setenv("DYNAMIC_MODEL_CONFIG_PATH", str(tmp_path / "models.json"))

    with TestClient(create_app()) as client:
        created = client.post(
            "/api/v1/platform/models",
            json={"alias": "qwen-hf", "provider": "huggingface", "model_id": "Qwen/Qwen3-8B"},
        )
        overview_response = client.get("/api/v1/platform/overview")

    assert created.status_code == 201
    assert created.json()["alias"] == "qwen-hf"
    assert any(model["alias"] == "qwen-hf" for model in overview_response.json()["models"])


def test_chat_endpoint_returns_structured_response(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "stub")
    monkeypatch.setenv("STATE_BACKEND", "memory")

    with TestClient(create_app()) as client:
        response = client.post("/api/v1/chat", json={"message": "Explique arquitetura agêntica."})

    payload = response.json()
    assert response.status_code == 200
    assert payload["answer"] == "Stub response for: Explique arquitetura agêntica."
    assert payload["session_id"]
    assert payload["model"] == "qwen2.5:7b-instruct-q4_K_M"
    assert isinstance(payload["latency_ms"], int)


def test_chat_endpoint_rejects_oversized_request(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "stub")
    monkeypatch.setenv("STATE_BACKEND", "memory")
    monkeypatch.setenv("APP_MAX_REQUEST_SIZE_BYTES", "64")

    with TestClient(create_app()) as client:
        response = client.post("/api/v1/chat", json={"message": "x" * 200})

    assert response.status_code == 413
    assert response.json() == {"detail": "Request body too large"}


def test_chat_endpoint_routes_news_requests(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "stub")
    monkeypatch.setenv("STATE_BACKEND", "memory")
    monkeypatch.setenv("NEWS_RSS_FEEDS", "https://example.com/rss.xml")
    monkeypatch.setattr(
        NewsMCPServer,
        "_download_feed",
        lambda self, _url: """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Notícia de tecnologia</title>
      <link>https://example.com/news-1</link>
      <description>Resumo rápido.</description>
      <pubDate>2026-08-24T11:00:00+00:00</pubDate>
    </item>
  </channel>
</rss>
""",
    )

    with TestClient(create_app()) as client:
        response = client.post("/api/v1/chat", json={"message": "Quais notícias de tecnologia hoje?"})

    payload = response.json()
    assert response.status_code == 200
    assert "Notícias encontradas:" in payload["answer"]
    assert "Notícia de tecnologia" in payload["answer"]
    assert payload["model"] == "news-mcp"


def test_chat_endpoint_explains_missing_openrouter_key(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "litellm")
    monkeypatch.setenv("STATE_BACKEND", "memory")
    monkeypatch.setenv("OPENROUTER_API_KEY", "")

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/chat",
            json={"message": "Olá", "model": "openrouter-free"},
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "OPENROUTER_API_KEY is required for OpenRouter models"}


def test_governance_api_creates_and_runs_eval(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "stub")
    monkeypatch.setenv("STATE_BACKEND", "memory")
    monkeypatch.setenv("GOVERNANCE_CONFIG_PATH", str(tmp_path / "governance.json"))

    with TestClient(create_app()) as client:
        created = client.post(
            "/api/v1/governance/evals",
            json={"name": "Qualidade", "expected_keywords": ["MCP"], "min_score": 1},
        )
        result = client.post(
            f"/api/v1/governance/evals/{created.json()['id']}/run",
            json={"answer": "Resposta com MCP", "latency_ms": 50},
        )

    assert created.status_code == 201
    assert result.json()["passed"] is True


def test_active_guardrail_blocks_chat(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "stub")
    monkeypatch.setenv("STATE_BACKEND", "memory")
    monkeypatch.setenv("GOVERNANCE_CONFIG_PATH", str(tmp_path / "governance.json"))

    with TestClient(create_app()) as client:
        created = client.post(
            "/api/v1/governance/guardrails",
            json={
                "name": "Sem segredos",
                "rule_type": "blocked_terms",
                "stage": "input",
                "action": "block",
                "terms": ["senha"],
            },
        )
        blocked = client.post("/api/v1/chat", json={"message": "minha senha", "model": "fast"})

    assert created.status_code == 201
    assert blocked.status_code == 422
    assert blocked.json() == {"detail": "Content blocked by guardrail: Sem segredos"}
