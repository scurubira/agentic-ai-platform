from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalCaseResult:
    correctness: float
    groundedness: float
    latency_ms: int
    errors: int


class PlaceholderEvaluator:
    """Starter evaluator contract for future model-vs-model comparisons."""

    def score(self, *, answer: str, expected_keywords: list[str], latency_ms: int) -> EvalCaseResult:
        correctness = 1.0 if all(keyword.lower() in answer.lower() for keyword in expected_keywords) else 0.0
        return EvalCaseResult(correctness=correctness, groundedness=0.0, latency_ms=latency_ms, errors=0)
