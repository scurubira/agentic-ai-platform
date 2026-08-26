from __future__ import annotations

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from apps.api.main import create_app
from mcp_servers.news.server import NewsMCPServer


def test_health_and_ready_endpoints(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "stub")
    monkeypatch.setenv("STATE_BACKEND", "memory")

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
    assert {model["alias"] for model in payload["models"]} == {"fast", "reasoning"}
    assert payload["services"]["memory"] == {"backend": "memory"}
    assert "password" not in response.text.lower()


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
