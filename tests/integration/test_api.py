from __future__ import annotations

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from apps.api.main import create_app


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
