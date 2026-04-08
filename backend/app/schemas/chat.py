from pydantic import BaseModel, Field


class Citation(BaseModel):
    title: str
    citation: str | None = None
    court: str | None = None
    source_url: str | None = None
    relevance_score: float | None = None


class SourceChunk(BaseModel):
    title: str
    excerpt: str
    citation: str | None = None
    source_url: str | None = None


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    sources: list[SourceChunk]
    disclaimer: str
