from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from platform_core.errors import AppError


@dataclass(frozen=True)
class AgentDefinition:
    id: str
    name: str
    description: str
    model_alias: str
    capabilities: list[str]
    protected: bool = False


AGENT_TEMPLATES = {
    "rag": AgentDefinition(
        id="rag",
        name="RAG Specialist",
        description="Recupera contexto em bases vetoriais antes de responder.",
        model_alias="fast",
        capabilities=["retrieval", "citations"],
    ),
    "sql": AgentDefinition(
        id="sql",
        name="SQL Analyst",
        description="Analisa esquemas e executa consultas governadas.",
        model_alias="reasoning",
        capabilities=["database", "analysis"],
    ),
    "news": AgentDefinition(
        id="news",
        name="News Researcher",
        description="Pesquisa fontes RSS e sintetiza notícias recentes.",
        model_alias="fast",
        capabilities=["news", "web-research"],
    ),
}


class AgentRegistry:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._agents = {"supervisor": self._supervisor()}
        self._agents.update(self._load())

    def list_installed(self) -> list[AgentDefinition]:
        return sorted(self._agents.values(), key=lambda agent: agent.id)

    def list_catalog(self) -> list[dict[str, object]]:
        installed_ids = set(self._agents)
        return [
            {**asdict(agent), "installed": agent.id in installed_ids}
            for agent in sorted(AGENT_TEMPLATES.values(), key=lambda item: item.id)
        ]

    def install(self, *, agent_id: str, model_alias: str) -> AgentDefinition:
        if agent_id in self._agents:
            raise AppError(f"Agent is already installed: {agent_id}", status_code=409)
        try:
            template = AGENT_TEMPLATES[agent_id]
        except KeyError as exc:
            raise AppError(f"Unknown agent template: {agent_id}", status_code=404) from exc
        agent = AgentDefinition(
            id=template.id,
            name=template.name,
            description=template.description,
            model_alias=model_alias,
            capabilities=template.capabilities,
        )
        self._agents[agent.id] = agent
        self._save()
        return agent

    def remove(self, agent_id: str) -> None:
        try:
            agent = self._agents[agent_id]
        except KeyError as exc:
            raise AppError(f"Agent is not installed: {agent_id}", status_code=404) from exc
        if agent.protected:
            raise AppError("The supervisor agent cannot be removed", status_code=409)
        del self._agents[agent_id]
        self._save()

    def _load(self) -> dict[str, AgentDefinition]:
        if not self._config_path.exists():
            return {}
        try:
            entries = json.loads(self._config_path.read_text(encoding="utf-8"))
            return {str(entry["id"]): AgentDefinition(**entry) for entry in entries}
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AppError("Agent registry is invalid", status_code=500) from exc

    def _save(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        entries = [asdict(agent) for agent in self.list_installed() if not agent.protected]
        temporary_path = self._config_path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary_path.replace(self._config_path)

    @staticmethod
    def _supervisor() -> AgentDefinition:
        return AgentDefinition(
            id="supervisor",
            name="Supervisor",
            description="Orquestra modelos, ferramentas e agentes especializados.",
            model_alias="fast",
            capabilities=["orchestration", "routing"],
            protected=True,
        )