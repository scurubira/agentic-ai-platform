from __future__ import annotations

from pathlib import Path

import pytest

from platform_core.errors import AppError
from platform_core.governance.service import GovernanceService


def test_eval_definition_is_persisted_and_executable(tmp_path: Path) -> None:
    config_path = tmp_path / "governance.json"
    service = GovernanceService(config_path)
    definition = service.create_eval(
        name="Resposta factual",
        description="Exige termos-chave",
        expected_keywords=["LangGraph", "MCP"],
        min_score=1.0,
    )

    result = service.run_eval(definition["id"], answer="LangGraph usa MCP", latency_ms=120)
    reloaded = GovernanceService(config_path)

    assert result["passed"] is True
    assert reloaded.snapshot()["evals"][0]["name"] == "Resposta factual"


def test_blocking_guardrail_detects_and_enforces_terms(tmp_path: Path) -> None:
    service = GovernanceService(tmp_path / "governance.json")
    service.create_guardrail(
        name="Bloquear segredos",
        rule_type="blocked_terms",
        stage="input",
        action="block",
        terms=["senha", "token secreto"],
        max_length=None,
        enabled=True,
    )

    result = service.test_guardrails(text="Minha senha está aqui", stage="input")

    assert result["allowed"] is False
    assert result["violations"][0]["name"] == "Bloquear segredos"
    with pytest.raises(AppError, match="Content blocked by guardrail"):
        service.enforce(text="Minha senha está aqui", stage="input")


def test_warning_guardrail_reports_without_blocking(tmp_path: Path) -> None:
    service = GovernanceService(tmp_path / "governance.json")
    service.create_guardrail(
        name="Resposta curta",
        rule_type="max_length",
        stage="output",
        action="warn",
        terms=[],
        max_length=10,
        enabled=True,
    )

    result = service.test_guardrails(text="Uma resposta longa", stage="output")

    assert result["allowed"] is True
    assert len(result["violations"]) == 1