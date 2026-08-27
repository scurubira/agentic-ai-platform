from pydantic import BaseModel, Field


class AgentInstall(BaseModel):
    model_alias: str = Field(default="fast", min_length=1, max_length=64)