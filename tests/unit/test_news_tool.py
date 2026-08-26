from __future__ import annotations

from agents.tools.news import build_news_answer
from platform_core.mcp.gateway import MCPGateway


class StubNewsServer:
    def __init__(self) -> None:
        self.queries: list[tuple[str, int | None]] = []

    def fetch_latest_news(self, query: str, max_items: int | None = None) -> list[dict[str, str]]:
        self.queries.append((query, max_items))
        return [
            {
                "title": f"Destaque de {query}",
                "source": "Portal Esportivo",
                "url": "https://example.com/noticia",
                "summary": "",
                "published_at": "2026-08-26T10:00:00+00:00",
            }
        ]


def test_general_football_request_returns_three_sections() -> None:
    server = StubNewsServer()
    gateway = MCPGateway()
    gateway.register("news", server)

    answer = build_news_answer(gateway, "Quero notícias variadas sobre futebol")

    assert "Futebol brasileiro:" in answer
    assert "Futebol internacional:" in answer
    assert "Mercado da bola:" in answer
    assert len(server.queries) == 3
    assert all(max_items == 3 for _, max_items in server.queries)


def test_short_football_news_request_is_also_varied() -> None:
    server = StubNewsServer()
    gateway = MCPGateway()
    gateway.register("news", server)

    answer = build_news_answer(gateway, "Notícias de futebol")

    assert "Futebol brasileiro:" in answer
    assert "Futebol internacional:" in answer
    assert "Mercado da bola:" in answer


def test_specific_football_request_remains_focused() -> None:
    server = StubNewsServer()
    gateway = MCPGateway()
    gateway.register("news", server)

    build_news_answer(gateway, "Últimas notícias do Palmeiras")

    assert server.queries == [("Últimas notícias do Palmeiras", None)]