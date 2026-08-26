from __future__ import annotations

from platform_core.mcp.gateway import MCPGateway

_NEWS_KEYWORDS = ("notícia", "noticia", "noticias", "notícias", "news", "manchete", "headlines", "jornal")
_GENERAL_FOOTBALL_MARKERS = ("variad", "gerais", "sobre futebol", "de futebol", "do futebol", "futebol hoje")
_FOOTBALL_SECTIONS = (
    ("Futebol brasileiro", "(Brasileirão OR Copa do Brasil OR Seleção Brasileira) futebol when:2d"),
    ("Futebol internacional", "(Champions League OR Premier League OR La Liga) futebol when:2d"),
    ("Mercado da bola", "mercado da bola when:2d"),
)


def should_route_to_news(message: str) -> bool:
    normalized = message.casefold()
    return any(keyword in normalized for keyword in _NEWS_KEYWORDS)


def build_news_answer(mcp_gateway: MCPGateway, message: str) -> str:
    if _is_general_football_request(message):
        return _build_varied_football_answer(mcp_gateway)

    items = mcp_gateway.call("news", "fetch_latest_news", query=message)
    if not items:
        return "Não encontrei notícias no momento. Verifique as fontes RSS configuradas."

    lines = ["Notícias encontradas:"]
    for item in items:
        lines.append(_format_item(item))
    return "\n".join(lines)


def _is_general_football_request(message: str) -> bool:
    normalized = message.casefold()
    return "futebol" in normalized and any(marker in normalized for marker in _GENERAL_FOOTBALL_MARKERS)


def _build_varied_football_answer(mcp_gateway: MCPGateway) -> str:
    lines = ["Giro de notícias do futebol:"]
    seen_titles: set[str] = set()

    for section, query in _FOOTBALL_SECTIONS:
        items = mcp_gateway.call("news", "fetch_latest_news", query=query, max_items=3)
        unique_items = []
        for item in items:
            normalized_title = item["title"].casefold()
            if normalized_title in seen_titles:
                continue
            seen_titles.add(normalized_title)
            unique_items.append(item)

        if unique_items:
            lines.extend(("", f"{section}:"))
            lines.extend(_format_item(item) for item in unique_items)

    if len(lines) == 1:
        return "Não encontrei notícias de futebol no momento. Tente novamente em instantes."
    return "\n".join(lines)


def _format_item(item: dict[str, object]) -> str:
    source = str(item.get("source", "fonte desconhecida"))
    title = str(item["title"]).removesuffix(f" - {source}")
    return f"- {title} — {source}"
