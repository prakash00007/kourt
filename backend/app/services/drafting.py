import hashlib

from app.services.anonymizer import AnonymizerService
from app.core.cache import RedisCacheService
from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError
from app.schemas.draft import DraftRequest, DraftResponse
from app.services.llm import LLMService
from app.utils.prompts import DRAFT_PROMPT


class DraftingService:
    def __init__(
        self,
        settings: Settings,
        llm_service: LLMService,
        cache_service: RedisCacheService,
        anonymizer_service: AnonymizerService,
    ):
        self.settings = settings
        self.llm_service = llm_service
        self.cache = cache_service
        self.anonymizer = anonymizer_service

    async def generate(self, payload: DraftRequest) -> DraftResponse:
        cache_key = hashlib.sha256(f"{payload.draft_type}:{payload.details}".encode("utf-8")).hexdigest()
        cached = await self.cache.get_json("draft", cache_key)
        if cached is not None:
            return DraftResponse.model_validate(cached)

        anonymized = self.anonymizer.anonymize_text(payload.details)
        prompt = DRAFT_PROMPT.format(draft_type=payload.draft_type, details=anonymized.redacted_text)
        try:
            draft = await self.llm_service.complete(prompt, task="drafting")
            final_draft = self.anonymizer.deanonymize_text(draft, anonymized.mapping)
        except ServiceUnavailableError:
            final_draft = self._build_local_fallback_draft(payload)

        response = DraftResponse(
            title=f"{payload.draft_type.title()} Draft",
            draft=final_draft,
            disclaimer=self.settings.disclaimer_text,
        )
        await self.cache.set_json("draft", cache_key, response.model_dump(mode="json"))
        return response

    def _build_local_fallback_draft(self, payload: DraftRequest) -> str:
        return "\n".join(
            [
                f"IN THE COURT OF THE COMPETENT AUTHORITY AT [PLACE]",
                "",
                f"Subject: {payload.draft_type.title()}",
                "",
                "Most Respectfully Submitted:",
                "",
                "1. Facts",
                f"The applicant seeks relief in relation to the following matter: {payload.details}",
                "The exact FIR number, police station, case number, and stage of proceedings should be inserted after verification from the record.",
                "",
                "2. Grounds",
                "The applicant has arguable grounds based on the facts presently available and reserves the right to raise additional grounds at the time of hearing.",
                "The applicant's custody period, procedural status, and personal circumstances should be highlighted with supporting records.",
                "The prosecution allegations must be tested at trial, and no adverse inference should be drawn beyond the present record.",
                "",
                "3. Prayer",
                "In view of the facts and grounds set out above, it is most respectfully prayed that this Hon'ble Court may be pleased to grant the relief sought in the interest of justice.",
                "Any other order deemed fit and proper in the facts and circumstances of the case may also be passed.",
                "",
                "[Local fallback draft generated because the external AI drafting service is unavailable. Please verify and refine before use.]",
            ]
        )
