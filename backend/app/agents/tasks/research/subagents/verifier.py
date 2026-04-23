from app.core.exceptions import ServiceUnavailableError
from app.services.llm import LLMService
from app.utils.prompts import AGENT_VERIFIER_PROMPT
from app.utils.text import join_context_blocks


class ResearchVerifierSubAgent:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def run(self, query: str, answer: str, retrieval: dict) -> tuple[str, str]:
        context_blocks: list[str] = retrieval["context_blocks"]
        if not context_blocks:
            return answer, "skipped: no context"

        prompt = AGENT_VERIFIER_PROMPT.format(
            query=query,
            answer=answer,
            documents=join_context_blocks(context_blocks)[:8000],
        )
        try:
            payload = await self.llm_service.complete_json(prompt, task="research")
        except ServiceUnavailableError:
            return answer, "skipped: verifier unavailable"

        is_grounded = bool(payload.get("is_grounded", True))
        risk = str(payload.get("risk") or "unknown").strip()
        revised_answer = str(payload.get("revised_answer") or "").strip()
        if not is_grounded and revised_answer:
            return revised_answer, f"revised: {risk}"
        return answer, f"grounded: {risk}"
