from __future__ import annotations

import pytest
from pytest import MonkeyPatch


@pytest.fixture(autouse=True)
def isolate_external_services(monkeypatch: MonkeyPatch) -> None:
	monkeypatch.setenv("LANGFUSE_ENABLED", "false")
