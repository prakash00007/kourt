from app.schemas.draft import DraftRequest, DraftResponse
from app.services.drafting import DraftingService


class DraftingWorkerSubAgent:
    def __init__(self, drafting_service: DraftingService):
        self.drafting_service = drafting_service

    async def run(self, payload: DraftRequest) -> DraftResponse:
        return await self.drafting_service.generate(payload)
