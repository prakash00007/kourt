from fastapi import UploadFile

from app.schemas.summary import SummaryResponse
from app.services.summarization import SummarizationService


class SummarizationWorkerSubAgent:
    def __init__(self, summarization_service: SummarizationService):
        self.summarization_service = summarization_service

    async def run(self, upload: UploadFile) -> tuple[SummaryResponse, str]:
        return await self.summarization_service.summarize_pdf(upload)
