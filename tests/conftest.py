from __future__ import annotations

from pathlib import Path

import pytest
from pytest import MonkeyPatch


@pytest.fixture(autouse=True)
def isolate_external_services(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
	monkeypatch.setenv("LANGFUSE_ENABLED", "false")
	monkeypatch.setenv("DYNAMIC_MODEL_CONFIG_PATH", str(tmp_path / "models.json"))
	monkeypatch.setenv("AGENT_CONFIG_PATH", str(tmp_path / "agents.json"))
