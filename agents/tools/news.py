from __future__ import annotations

from platform_core.mcp.gateway import MCPGateway

_NEWS_KEYWORDS = ("notícia", "noticia", "noticias", "notícias", "news", "manchete", "headlines", "jornal")


def should_route_to_news(message: str) -> bool:
    normalized = message.casefold()
    return any(keyword in normalized for keyword in _NEWS_KEYWORDS)


def build_news_answer(mcp_gateway: MCPGateway, message: str) -> str:
    items = mcp_gateway.call("news", "fetch_latest_news", query=message)
    if not items:
        return "Não encontrei notícias no momento. Verifique as fontes RSS configuradas."

    lines = ["Notícias encontradas:"]
    for item in items:
        source = item.get("source", "fonte desconhecida")
        title = item["title"].removesuffix(f" - {source}")
        lines.append(f"- {title} — {source}")
    return "\n".join(lines)
