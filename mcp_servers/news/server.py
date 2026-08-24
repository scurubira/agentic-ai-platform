from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from xml.etree import ElementTree

import httpx

from platform_core.errors import AppError

logger = logging.getLogger(__name__)


class NewsMCPServer:
    def __init__(self, feeds: list[str], timeout_seconds: int = 8, max_items: int = 5) -> None:
        self._feeds = [feed.strip() for feed in feeds if feed.strip()]
        self._timeout_seconds = timeout_seconds
        self._max_items = max_items

    def fetch_latest_news(self, query: str | None = None, max_items: int | None = None) -> list[dict[str, Any]]:
        if not self._feeds:
            return []

        items: list[dict[str, Any]] = []
        for feed_url in self._feeds:
            try:
                payload = self._download_feed(feed_url)
                items.extend(self._parse_feed(payload, source=feed_url))
            except Exception as exc:
                logger.warning("news_feed_fetch_failed", extra={"feed_url": feed_url, "error": str(exc)})
                continue

        if query:
            filtered_items = self._filter_items_by_query(items, query)
            if filtered_items:
                items = filtered_items

        items = sorted(items, key=lambda item: item["published_at"], reverse=True)
        return items[: max_items or self._max_items]

    def _filter_items_by_query(self, items: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        normalized_query = query.casefold().strip()
        if not normalized_query:
            return items

        direct_matches = [
            item
            for item in items
            if normalized_query in item["title"].casefold() or normalized_query in item["summary"].casefold()
        ]
        if direct_matches:
            return direct_matches

        tokens = [token for token in re.findall(r"\w+", normalized_query) if len(token) >= 4]
        if not tokens:
            return items

        return [
            item
            for item in items
            if any(token in item["title"].casefold() or token in item["summary"].casefold() for token in tokens)
        ]

    def _download_feed(self, feed_url: str) -> str:
        response = httpx.get(
            feed_url,
            timeout=self._timeout_seconds,
            headers={"User-Agent": "agentic-ai-platform-news-agent/1.0"},
        )
        response.raise_for_status()
        return response.text

    def _parse_feed(self, payload: str, *, source: str) -> list[dict[str, Any]]:
        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError as exc:
            raise AppError("Invalid RSS/Atom payload", status_code=502) from exc

        if root.tag.endswith("rss"):
            return self._parse_rss(root, source=source)
        if root.tag.endswith("feed"):
            return self._parse_atom(root, source=source)
        return []

    def _parse_rss(self, root: ElementTree.Element, *, source: str) -> list[dict[str, Any]]:
        channel = root.find("channel")
        if channel is None:
            return []
        items: list[dict[str, Any]] = []
        for entry in channel.findall("item"):
            title = self._safe_text(entry, "title")
            link = self._safe_text(entry, "link")
            summary = self._safe_text(entry, "description")
            published_raw = self._safe_text(entry, "pubDate")
            if not title or not link:
                continue
            items.append(
                {
                    "title": title,
                    "url": link,
                    "summary": summary,
                    "published_at": self._normalize_date(published_raw),
                    "source": source,
                }
            )
        return items

    def _parse_atom(self, root: ElementTree.Element, *, source: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for entry in root.findall("{*}entry"):
            title = self._safe_text(entry, "{*}title")
            summary = self._safe_text(entry, "{*}summary")
            published_raw = self._safe_text(entry, "{*}published") or self._safe_text(entry, "{*}updated")
            link_el = entry.find("{*}link")
            link = link_el.attrib.get("href", "") if link_el is not None else ""
            if not title or not link:
                continue
            items.append(
                {
                    "title": title,
                    "url": link,
                    "summary": summary,
                    "published_at": self._normalize_date(published_raw),
                    "source": source,
                }
            )
        return items

    def _safe_text(self, element: ElementTree.Element, path: str) -> str:
        target = element.find(path)
        return target.text.strip() if target is not None and target.text else ""

    def _normalize_date(self, value: str) -> str:
        if not value:
            return ""
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized).isoformat()
        except ValueError:
            return value
