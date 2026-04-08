from pydantic import BaseModel


class DocumentURLResponse(BaseModel):
    url: str
    expires_in_seconds: int
