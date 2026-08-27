from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from platform_core.errors import AppError
from platform_core.rag.interfaces import RetrievedDocument

WORD_PATTERN = re.compile(r"[a-zA-ZÀ-ÿ0-9_-]{2,}")


@dataclass(frozen=True)
class WikiPage:
    id: str
    title: str
    content: str
    source: str
    tags: list[str]
    created_at: str
    updated_at: str


class WikiService:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._pages = self._load()

    def list_pages(self, query: str = "") -> list[WikiPage]:
        pages: Iterable[WikiPage] = self._pages.values()
        if query.strip():
            terms = self._terms(query)
            pages = (
                page for page in pages if terms <= self._terms(f"{page.title} {page.content} {' '.join(page.tags)}")
            )
        return sorted(pages, key=lambda page: page.updated_at, reverse=True)

    def get_page(self, page_id: str) -> WikiPage:
        try:
            return self._pages[page_id]
        except KeyError as exc:
            raise AppError(f"Wiki page not found: {page_id}", status_code=404) from exc

    def create_page(
        self, *, title: str, content: str, source: str = "manual", tags: list[str] | None = None
    ) -> WikiPage:
        now = datetime.now(UTC).isoformat()
        page = WikiPage(
            id=str(uuid4()),
            title=title.strip(),
            content=content.strip(),
            source=source.strip() or "manual",
            tags=self._normalize_tags(tags or []),
            created_at=now,
            updated_at=now,
        )
        self._pages[page.id] = page
        self._save()
        return page

    def import_page(self, *, title: str, content: str, source: str, tags: list[str] | None = None) -> WikiPage:
        existing = next((page for page in self._pages.values() if page.source == source), None)
        if existing is not None:
            return self.update_page(existing.id, title=title, content=content, tags=tags or existing.tags)
        return self.create_page(title=title, content=content, source=source, tags=tags)

    def update_page(self, page_id: str, *, title: str, content: str, tags: list[str]) -> WikiPage:
        current = self.get_page(page_id)
        page = WikiPage(
            id=current.id,
            title=title.strip(),
            content=content.strip(),
            source=current.source,
            tags=self._normalize_tags(tags),
            created_at=current.created_at,
            updated_at=datetime.now(UTC).isoformat(),
        )
        self._pages[page.id] = page
        self._save()
        return page

    def delete_page(self, page_id: str) -> None:
        self.get_page(page_id)
        del self._pages[page_id]
        self._save()

    def retrieve(self, query: str, *, limit: int = 4) -> list[RetrievedDocument]:
        query_terms = self._terms(query)
        if not query_terms:
            return []
        documents: list[RetrievedDocument] = []
        for page in self._pages.values():
            for index, chunk in enumerate(self._chunks(page.content)):
                title_terms = self._terms(page.title)
                chunk_terms = self._terms(chunk)
                overlap = query_terms & chunk_terms
                title_overlap = query_terms & title_terms
                if not overlap and not title_overlap:
                    continue
                score = (2 * len(title_overlap) + len(overlap)) / math.sqrt(max(len(chunk_terms), 1))
                documents.append(
                    RetrievedDocument(content=chunk, source=f"{page.title}#{index + 1}", score=round(score, 4))
                )
        return sorted(documents, key=lambda document: document.score, reverse=True)[:limit]

    def stats(self) -> dict[str, int]:
        chunks = sum(len(self._chunks(page.content)) for page in self._pages.values())
        return {"pages": len(self._pages), "chunks": chunks}

    def _load(self) -> dict[str, WikiPage]:
        if not self._config_path.exists():
            return {}
        try:
            entries = json.loads(self._config_path.read_text(encoding="utf-8"))
            return {str(entry["id"]): WikiPage(**entry) for entry in entries}
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AppError("Wiki registry is invalid", status_code=500) from exc

    def _save(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._config_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps([asdict(page) for page in self._pages.values()], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self._config_path)

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {word.lower() for word in WORD_PATTERN.findall(text)}

    @staticmethod
    def _normalize_tags(tags: list[str]) -> list[str]:
        return sorted({tag.strip().lower() for tag in tags if tag.strip()})

    @staticmethod
    def _chunks(content: str, size: int = 1200) -> list[str]:
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", content) if paragraph.strip()]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            if current and len(current) + len(paragraph) + 2 > size:
                chunks.append(current)
                current = paragraph
            else:
                current = f"{current}\n\n{paragraph}".strip()
        if current:
            chunks.append(current)
        return chunks