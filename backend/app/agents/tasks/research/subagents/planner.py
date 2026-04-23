import re
from typing import Any

from app.core.exceptions import ServiceUnavailableError
from app.services.llm import LLMService
from app.utils.prompts import AGENT_PLANNER_PROMPT


class ResearchPlannerSubAgent:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def run(self, query: str) -> dict[str, Any]:
        prompt = AGENT_PLANNER_PROMPT.format(query=query)
        try:
            payload = await self.llm_service.complete_json(prompt, task="research")
        except ServiceUnavailableError:
            payload = {}

        focus = str(payload.get("focus") or query).strip()
        strategy = str(payload.get("strategy") or "semantic_retrieval_then_grounded_synthesis").strip()
        terms = self._normalize_terms(payload.get("must_have_terms"), query)
        return {
            "focus": focus,
            "strategy": strategy,
            "must_have_terms": terms[:8],
        }

    def _normalize_terms(self, raw_terms: Any, query: str) -> list[str]:
        if isinstance(raw_terms, list):
            terms = [str(item).strip() for item in raw_terms if str(item).strip()]
        elif isinstance(raw_terms, str):
            terms = [token.strip() for token in raw_terms.split(",") if token.strip()]
        else:
            terms = []

        if terms:
            return terms

        fallback = []
        for token in re.findall(r"[A-Za-z0-9]+", query):
            if token.isdigit() or (token.isupper() and len(token) >= 3):
                fallback.append(token)
        return fallback
