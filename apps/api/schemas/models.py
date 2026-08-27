from typing import Literal

from pydantic import BaseModel, Field


class ModelCreate(BaseModel):
    alias: str = Field(min_length=1, max_length=64)
    provider: Literal["openrouter", "huggingface"]
    model_id: str = Field(min_length=3, max_length=200)