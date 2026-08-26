from typing import Literal

from pydantic import BaseModel, Field


class EvalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    expected_keywords: list[str] = Field(min_length=1, max_length=20)
    min_score: float = Field(default=1.0, ge=0, le=1)


class EvalRun(BaseModel):
    answer: str = Field(min_length=1, max_length=20_000)
    latency_ms: int = Field(default=0, ge=0)


class GuardrailCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    rule_type: Literal["blocked_terms", "required_terms", "max_length"]
    stage: Literal["input", "output", "both"] = "input"
    action: Literal["block", "warn"] = "block"
    terms: list[str] = Field(default_factory=list, max_length=50)
    max_length: int | None = Field(default=None, ge=1, le=100_000)
    enabled: bool = True


class GuardrailToggle(BaseModel):
    enabled: bool


class GuardrailTest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    stage: Literal["input", "output"] = "input"