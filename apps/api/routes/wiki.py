from __future__ import annotations

import ipaddress
import re
from dataclasses import asdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from fastapi import APIRouter, Depends, Query

from apps.api.dependencies.services import get_container
from apps.api.schemas.wiki import (
    WikiFileImport,
    WikiPageWrite,
    WikiQuestion,
    WikiRepositoryImport,
    WikiUrlImport,
)
from platform_core.container import AppContainer
from platform_core.errors import AppError
from platform_core.rag.wiki import WikiPage

router = APIRouter(prefix="/api/v1/wiki", tags=["wiki"])
_IGNORED_PARTS = {".git", ".venv", "data", "dist", "node_modules", "__pycache__"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"script", "style", "noscript"}:
            self.ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth and data.strip():
            self.parts.append(data.strip())


class _SearchResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "a" and "result__a" in classes:
            self._current = {"title": "", "url": _normalize_search_url(attributes.get("href") or ""), "snippet": ""}
            self._capture = "title"
        elif self._current is not None and "result__snippet" in classes:
            self._capture = "snippet"

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture == "title":
            self._capture = None
        elif tag in {"a", "div"} and self._capture == "snippet" and self._current is not None:
            if self._current["title"] and self._current["url"]:
                self.results.append(self._current)
            self._current = None
            self._capture = None

    def handle_data(self, data: str) -> None:
        if self._current is not None and self._capture and data.strip():
            current = self._current[self._capture]
            self._current[self._capture] = f"{current} {data.strip()}".strip()


@router.get("")
async def list_wiki(
    query: str = Query(default="", max_length=160),
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    return {
        "pages": [asdict(page) for page in container.wiki_service.list_pages(query)],
        "stats": container.wiki_service.stats(),
    }


@router.get("/search")
async def search_web(
    query: str = Query(min_length=2, max_length=160),
    limit: int = Query(default=8, ge=1, le=15),
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    try:
        async with httpx.AsyncClient(timeout=container.settings.request_timeout_seconds, follow_redirects=True) as client:
            response = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 BensTech-Wiki/1.0"},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AppError("Internet search is temporarily unavailable", status_code=502) from exc
    parser = _SearchResultParser()
    parser.feed(response.text)
    results = []
    for result in parser.results:
        try:
            _validate_public_url(result["url"])
        except AppError:
            continue
        results.append(result)
        if len(results) == limit:
            break
    return {"query": query, "results": results}


@router.post("/pages", status_code=201)
async def create_page(payload: WikiPageWrite, container: AppContainer = Depends(get_container)) -> dict[str, object]:
    return asdict(container.wiki_service.create_page(title=payload.title, content=payload.content, tags=payload.tags))


@router.put("/pages/{page_id}")
async def update_page(
    page_id: str,
    payload: WikiPageWrite,
    container: AppContainer = Depends(get_container),
) -> dict[str, object]:
    return asdict(
        container.wiki_service.update_page(page_id, title=payload.title, content=payload.content, tags=payload.tags)
    )


@router.delete("/pages/{page_id}", status_code=204)
async def delete_page(page_id: str, container: AppContainer = Depends(get_container)) -> None:
    container.wiki_service.delete_page(page_id)


@router.post("/import/file", status_code=201)
async def import_file(
    payload: WikiFileImport, container: AppContainer = Depends(get_container)
) -> dict[str, object]:
    suffix = Path(payload.filename).suffix.lower()
    if suffix not in {".md", ".markdown", ".txt"}:
        raise AppError("Wiki uploads support Markdown and text files", status_code=422)
    page = container.wiki_service.import_page(
        title=payload.title, content=payload.content, source=f"file:{Path(payload.filename).name}", tags=payload.tags
    )
    return asdict(page)


@router.post("/import/url", status_code=201)
async def import_url(payload: WikiUrlImport, container: AppContainer = Depends(get_container)) -> dict[str, object]:
    url = str(payload.url)
    _validate_public_url(url)
    try:
        async with httpx.AsyncClient(
            timeout=container.settings.request_timeout_seconds, follow_redirects=True
        ) as client:
            response = await client.get(url, headers={"User-Agent": "BensTech-Wiki/1.0"})
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AppError("Could not import the requested URL", status_code=502) from exc
    if len(response.content) > 1_000_000:
        raise AppError("URL content exceeds the 1 MB Wiki limit", status_code=413)
    extractor = _TextExtractor()
    extractor.feed(response.text)
    content = re.sub(r"\s+", " ", " ".join(extractor.parts)).strip()
    if not content:
        raise AppError("The URL did not contain readable text", status_code=422)
    title = payload.title or urlparse(url).hostname or "Imported page"
    return asdict(container.wiki_service.import_page(title=title, content=content, source=url, tags=payload.tags))


@router.post("/import/repository", status_code=201)
async def import_repository(
    payload: WikiRepositoryImport, container: AppContainer = Depends(get_container)
) -> dict[str, object]:
    root = container.settings.wiki_repository_root.resolve()
    target = (root / payload.relative_path).resolve()
    if not target.is_relative_to(root) or not target.exists():
        raise AppError("Repository path is outside the allowed root or does not exist", status_code=422)
    candidates = [target] if target.is_file() else list(target.rglob("*"))
    imported: list[WikiPage] = []
    for file_path in candidates:
        relative = file_path.relative_to(root)
        if len(imported) >= 100:
            break
        if not file_path.is_file() or file_path.suffix.lower() not in {".md", ".txt"}:
            continue
        if any(part.startswith(".") or part in _IGNORED_PARTS for part in relative.parts):
            continue
        content = file_path.read_text(encoding="utf-8", errors="replace")
        if not content.strip() or len(content) > 500_000:
            continue
        imported.append(
            container.wiki_service.import_page(
                title=file_path.stem.replace("-", " ").replace("_", " ").title(),
                content=content,
                source=f"repo:{relative.as_posix()}",
                tags=["repository"],
            )
        )
    return {"imported": len(imported), "pages": [asdict(page) for page in imported]}


@router.post("/ask")
async def ask_wiki(payload: WikiQuestion, container: AppContainer = Depends(get_container)) -> dict[str, object]:
    container.model_registry.get(payload.model_alias)
    documents = container.wiki_service.retrieve(payload.question)
    if not documents:
        raise AppError("No relevant Wiki content was found", status_code=404)
    context = "\n\n".join(f"SOURCE: {document.source}\n{document.content}" for document in documents)
    result = await container.inference_gateway.complete(
        model_alias=payload.model_alias,
        conversation=[
            {
                "role": "system",
                "content": (
                    "Answer only from the supplied Wiki context. "
                    "Cite source names and say when context is insufficient."
                ),
            },
            {"role": "user", "content": f"WIKI CONTEXT:\n{context}\n\nQUESTION:\n{payload.question}"},
        ],
    )
    return {"answer": result.answer, "model": result.public_model_name, "sources": [asdict(item) for item in documents]}


def _validate_public_url(url: str) -> None:
    hostname = urlparse(url).hostname or ""
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        raise AppError("Local URLs cannot be imported", status_code=422)
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if not address.is_global:
        raise AppError("Private network URLs cannot be imported", status_code=422)


def _normalize_search_url(url: str) -> str:
    parsed = urlparse(url if not url.startswith("//") else f"https:{url}")
    redirect_target = parse_qs(parsed.query).get("uddg")
    return unquote(redirect_target[0]) if redirect_target else url