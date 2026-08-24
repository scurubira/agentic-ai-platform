from __future__ import annotations

from mcp_servers.news.server import NewsMCPServer

_SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sample News</title>
    <item>
      <title>Tecnologia cresce no Brasil</title>
      <link>https://example.com/tech-1</link>
      <description>Mercado de tecnologia em alta.</description>
      <pubDate>2026-08-24T10:00:00+00:00</pubDate>
    </item>
    <item>
      <title>Esportes hoje</title>
      <link>https://example.com/sport-1</link>
      <description>Resumo do dia.</description>
      <pubDate>2026-08-24T09:00:00+00:00</pubDate>
    </item>
  </channel>
</rss>
"""


def test_fetch_latest_news_filters_by_query() -> None:
    class StubNewsMCPServer(NewsMCPServer):
        def _download_feed(self, feed_url: str) -> str:
            return _SAMPLE_RSS

    server = StubNewsMCPServer(feeds=["https://example.com/rss.xml"])

    items = server.fetch_latest_news(query="tecnologia")

    assert len(items) == 1
    assert items[0]["title"] == "Tecnologia cresce no Brasil"


def test_fetch_latest_news_returns_empty_when_no_feeds_configured() -> None:
    server = NewsMCPServer(feeds=[])

    assert server.fetch_latest_news() == []
