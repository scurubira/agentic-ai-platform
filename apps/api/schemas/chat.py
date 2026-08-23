from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    model: str = Field(default="fast", min_length=1, max_length=64)


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    model: str
    latency_ms: int
