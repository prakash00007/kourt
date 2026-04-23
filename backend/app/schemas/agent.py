from pydantic import BaseModel, Field

from app.schemas.chat import Citation, SourceChunk


class AgentTraceStep(BaseModel):
    agent: str
    summary: str
    duration_ms: float


class AgentResearchRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=2000)
    include_trace: bool = True


class AgentResearchResponse(BaseModel):
    answer: str
    citations: list[Citation]
    sources: list[SourceChunk]
    disclaimer: str
    workflow_id: str
    trace: list[AgentTraceStep] = Field(default_factory=list)
