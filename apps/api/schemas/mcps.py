from pydantic import BaseModel, Field, HttpUrl


class MCPServerInstall(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    version: str = Field(default="latest", min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=1000)
    transport: str = Field(default="unknown", max_length=50)
    repository_url: HttpUrl | None = None
