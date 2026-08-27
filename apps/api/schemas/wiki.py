from pydantic import BaseModel, Field, HttpUrl


class WikiPageWrite(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=500_000)
    tags: list[str] = Field(default_factory=list, max_length=20)


class WikiFileImport(WikiPageWrite):
    filename: str = Field(min_length=1, max_length=255)


class WikiUrlImport(BaseModel):
    url: HttpUrl
    title: str | None = Field(default=None, max_length=160)
    tags: list[str] = Field(default_factory=list, max_length=20)


class WikiRepositoryImport(BaseModel):
    relative_path: str = Field(default=".", max_length=240)


class WikiQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    model_alias: str = Field(default="fast", min_length=1, max_length=64)