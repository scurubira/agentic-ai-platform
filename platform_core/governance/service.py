from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from evals.evaluators.basic import PlaceholderEvaluator
from platform_core.errors import AppError

GuardrailStage = Literal["input", "output", "both"]
GuardrailAction = Literal["block", "warn"]
GuardrailType = Literal["blocked_terms", "required_terms", "max_length"]


class GovernanceService:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._evals: list[dict[str, Any]] = []
        self._guardrails: list[dict[str, Any]] = []
        self._evaluator = PlaceholderEvaluator()
        self._load()

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        return {"evals": list(self._evals), "guardrails": list(self._guardrails)}

    def create_eval(
        self,
        *,
        name: str,
        description: str,
        expected_keywords: list[str],
        min_score: float,
    ) -> dict[str, Any]:
        definition = {
            "id": str(uuid4()),
            "name": name.strip(),
            "description": description.strip(),
            "expected_keywords": self._clean_terms(expected_keywords),
            "min_score": min_score,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._evals.append(definition)
        self._save()
        return definition

    def run_eval(self, definition_id: str, *, answer: str, latency_ms: int) -> dict[str, Any]:
        definition = self._find(self._evals, definition_id, "Eval")
        result = self._evaluator.score(
            answer=answer,
            expected_keywords=definition["expected_keywords"],
            latency_ms=latency_ms,
        )
        return {
            "eval_id": definition_id,
            "passed": result.correctness >= definition["min_score"],
            "correctness": result.correctness,
            "groundedness": result.groundedness,
            "latency_ms": result.latency_ms,
            "errors": result.errors,
        }

    def delete_eval(self, definition_id: str) -> None:
        self._delete(self._evals, definition_id, "Eval")

    def create_guardrail(
        self,
        *,
        name: str,
        rule_type: GuardrailType,
        stage: GuardrailStage,
        action: GuardrailAction,
        terms: list[str],
        max_length: int | None,
        enabled: bool,
    ) -> dict[str, Any]:
        if rule_type == "max_length" and max_length is None:
            raise AppError("max_length is required for max_length guardrails")
        if rule_type != "max_length" and not self._clean_terms(terms):
            raise AppError("At least one term is required for term guardrails")
        definition = {
            "id": str(uuid4()),
            "name": name.strip(),
            "rule_type": rule_type,
            "stage": stage,
            "action": action,
            "terms": self._clean_terms(terms),
            "max_length": max_length,
            "enabled": enabled,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._guardrails.append(definition)
        self._save()
        return definition

    def set_guardrail_enabled(self, definition_id: str, enabled: bool) -> dict[str, Any]:
        definition = self._find(self._guardrails, definition_id, "Guardrail")
        definition["enabled"] = enabled
        self._save()
        return definition

    def delete_guardrail(self, definition_id: str) -> None:
        self._delete(self._guardrails, definition_id, "Guardrail")

    def test_guardrails(self, *, text: str, stage: Literal["input", "output"]) -> dict[str, Any]:
        violations: list[dict[str, str]] = []
        for definition in self._guardrails:
            if not definition["enabled"] or definition["stage"] not in (stage, "both"):
                continue
            detail = self._evaluate_guardrail(definition, text)
            if detail:
                violations.append(
                    {
                        "guardrail_id": definition["id"],
                        "name": definition["name"],
                        "action": definition["action"],
                        "detail": detail,
                    }
                )
        return {
            "allowed": not any(violation["action"] == "block" for violation in violations),
            "violations": violations,
        }

    def enforce(self, *, text: str, stage: Literal["input", "output"]) -> None:
        result = self.test_guardrails(text=text, stage=stage)
        if not result["allowed"]:
            names = ", ".join(violation["name"] for violation in result["violations"] if violation["action"] == "block")
            raise AppError(f"Content blocked by guardrail: {names}", status_code=422)

    def _evaluate_guardrail(self, definition: dict[str, Any], text: str) -> str | None:
        normalized = text.casefold()
        if definition["rule_type"] == "blocked_terms":
            matches = [term for term in definition["terms"] if term.casefold() in normalized]
            return f"Blocked terms found: {', '.join(matches)}" if matches else None
        if definition["rule_type"] == "required_terms":
            missing = [term for term in definition["terms"] if term.casefold() not in normalized]
            return f"Required terms missing: {', '.join(missing)}" if missing else None
        limit = int(definition["max_length"])
        return f"Text has {len(text)} characters; limit is {limit}" if len(text) > limit else None

    def _load(self) -> None:
        if not self._config_path.exists():
            return
        try:
            payload = json.loads(self._config_path.read_text(encoding="utf-8"))
            self._evals = list(payload.get("evals", []))
            self._guardrails = list(payload.get("guardrails", []))
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise AppError(f"Invalid governance configuration: {self._config_path}", status_code=500) from exc

    def _save(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._config_path.with_suffix(f"{self._config_path.suffix}.tmp")
        temporary_path.write_text(
            json.dumps(self.snapshot(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(self._config_path)

    def _delete(self, definitions: list[dict[str, Any]], definition_id: str, label: str) -> None:
        definition = self._find(definitions, definition_id, label)
        definitions.remove(definition)
        self._save()

    def _find(self, definitions: list[dict[str, Any]], definition_id: str, label: str) -> dict[str, Any]:
        for definition in definitions:
            if definition["id"] == definition_id:
                return definition
        raise AppError(f"{label} not found: {definition_id}", status_code=404)

    def _clean_terms(self, terms: list[str]) -> list[str]:
        return list(dict.fromkeys(term.strip() for term in terms if term.strip()))