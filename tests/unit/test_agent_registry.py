from pathlib import Path

import pytest

from platform_core.config.agent_registry import AgentRegistry
from platform_core.errors import AppError


def test_agent_registry_persists_installed_agent(tmp_path: Path) -> None:
    config_path = tmp_path / "agents.json"
    registry = AgentRegistry(config_path)

    installed = registry.install(agent_id="rag", model_alias="reasoning")
    reloaded = AgentRegistry(config_path)

    assert installed.model_alias == "reasoning"
    assert {agent.id for agent in reloaded.list_installed()} == {"rag", "supervisor"}


def test_agent_registry_removes_installed_agent(tmp_path: Path) -> None:
    registry = AgentRegistry(tmp_path / "agents.json")
    registry.install(agent_id="news", model_alias="fast")

    registry.remove("news")

    assert {agent.id for agent in registry.list_installed()} == {"supervisor"}


def test_agent_registry_protects_supervisor(tmp_path: Path) -> None:
    registry = AgentRegistry(tmp_path / "agents.json")

    with pytest.raises(AppError, match="cannot be removed"):
        registry.remove("supervisor")