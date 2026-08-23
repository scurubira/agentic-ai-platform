from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RetrievedDocument:
    content: str
    source: str
    score: float


class DocumentIngestionService(Protocol):
    def ingest(self, source_path: str) -> int: ...


class EmbeddingService(Protocol):
    def embed(self, text: str) -> list[float]: ...


class RetrievalService(Protocol):
    def retrieve(self, query: str, *, limit: int = 4) -> list[RetrievedDocument]: ...
