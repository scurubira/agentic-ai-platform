from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPGateway:
    servers: dict[str, object] = field(default_factory=dict)

    def register(self, name: str, server: object) -> None:
        self.servers[name] = server

    def list_capabilities(self) -> list[str]:
        return sorted(self.servers.keys())

    def call(self, server_name: str, method_name: str, *args: Any, **kwargs: Any) -> Any:
        server = self.servers[server_name]
        return getattr(server, method_name)(*args, **kwargs)
