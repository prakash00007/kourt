from pydantic import BaseModel, Field


class DraftRequest(BaseModel):
    draft_type: str = Field(..., min_length=3, max_length=120)
    details: str = Field(..., min_length=20, max_length=5000)


class DraftResponse(BaseModel):
    title: str
    draft: str
    disclaimer: str
