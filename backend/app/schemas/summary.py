from pydantic import BaseModel


class SummarySections(BaseModel):
    facts: str
    issues: str
    judgment: str
    key_takeaways: str


class SummaryResponse(BaseModel):
    file_name: str
    summary: SummarySections
    disclaimer: str
