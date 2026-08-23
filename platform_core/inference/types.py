from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class InferenceResult:
    answer: str
    physical_model: str
    public_model_name: str


class InferenceGateway(Protocol):
    async def complete(self, *, model_alias: str, conversation: list[dict[str, str]]) -> InferenceResult: ...

    async def readiness(self, *, model_alias: str) -> dict[str, object]: ...
