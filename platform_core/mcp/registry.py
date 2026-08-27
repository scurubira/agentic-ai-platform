from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from platform_core.errors import AppError


@dataclass(frozen=True)
class MCPServerDefinition:
    name: str
    description: str
    version: str
    source: str
    transport: str
    repository_url: str | None = None


class MCPRegistryService:
    REGISTRY_URL = "https://registry.modelcontextprotocol.io/v0.1/servers"

    def __init__(self, config_path: Path, timeout_seconds: int = 10) -> None:
        self._config_path = config_path
        self._timeout_seconds = timeout_seconds
        self._installed = self._load()

    def list_installed(self) -> list[MCPServerDefinition]:
        return sorted(self._installed.values(), key=lambda item: item.name)

    async def search(self, query: str, limit: int) -> list[dict[str, object]]:
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.get(
                    self.REGISTRY_URL,
                    params={"search": query, "limit": limit, "version": "latest"},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AppError("Could not query the official MCP Registry", status_code=502) from exc

        results: list[dict[str, object]] = []
        for entry in response.json().get("servers", []):
            server = entry.get("server", entry)
            packages = server.get("packages") or []
            remotes = server.get("remotes") or []
            package = packages[0] if packages else {}
            remote = remotes[0] if remotes else {}
            repository = server.get("repository") or {}
            source = str(package.get("identifier") or remote.get("url") or repository.get("url") or "")
            transport = str((package.get("transport") or remote.get("transport") or {}).get("type", "unknown"))
            name = str(server.get("name", ""))
            if not name:
                continue
            results.append(
                {
                    "name": name,
                    "description": str(server.get("description", "")),
                    "version": str(server.get("version", package.get("version", "latest"))),
                    "source": source,
                    "transport": transport,
                    "repository_url": repository.get("url"),
                    "installed": name in self._installed,
                }
            )
        return results

    def install(self, definition: MCPServerDefinition) -> MCPServerDefinition:
        if definition.name in self._installed:
            raise AppError(f"MCP server is already installed: {definition.name}", status_code=409)
        if not definition.name.strip() or not definition.source.strip():
            raise AppError("MCP server name and source are required", status_code=422)
        self._installed[definition.name] = definition
        self._save()
        return definition

    def remove(self, name: str) -> None:
        if name not in self._installed:
            raise AppError(f"MCP server is not installed: {name}", status_code=404)
        del self._installed[name]
        self._save()

    def _load(self) -> dict[str, MCPServerDefinition]:
        if not self._config_path.exists():
            return {}
        try:
            entries = json.loads(self._config_path.read_text(encoding="utf-8"))
            return {str(entry["name"]): MCPServerDefinition(**entry) for entry in entries}
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AppError("MCP server registry is invalid", status_code=500) from exc

    def _save(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._config_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps([asdict(item) for item in self.list_installed()], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self._config_path)
