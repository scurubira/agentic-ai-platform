from pathlib import Path

import pytest

from platform_core.errors import AppError
from platform_core.mcp.registry import MCPRegistryService, MCPServerDefinition


def test_mcp_registry_installs_persists_and_removes(tmp_path: Path) -> None:
    config_path = tmp_path / "mcps.json"
    registry = MCPRegistryService(config_path)
    server = MCPServerDefinition(
        name="io.github.example/filesystem",
        description="Filesystem tools",
        version="1.0.0",
        source="@example/mcp-filesystem",
        transport="stdio",
    )

    registry.install(server)
    assert MCPRegistryService(config_path).list_installed() == [server]

    registry.remove(server.name)
    assert registry.list_installed() == []


def test_mcp_registry_rejects_duplicate(tmp_path: Path) -> None:
    registry = MCPRegistryService(tmp_path / "mcps.json")
    server = MCPServerDefinition("example", "", "1", "package", "stdio")
    registry.install(server)

    with pytest.raises(AppError) as error:
        registry.install(server)

    assert error.value.status_code == 409
