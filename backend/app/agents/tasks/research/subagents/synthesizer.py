from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError
from app.schemas.chat import Citation, SourceChunk
from app.services.anonymizer import AnonymizerService
from app.services.llm import LLMService
from app.utils.prompts import AGENT_SYNTHESIS_PROMPT
from app.utils.text import join_context_blocks


class ResearchSynthesizerSubAgent:
    def __init__(self, settings: Settings, llm_service: LLMService, anonymizer: AnonymizerService):
        self.settings = settings
        self.llm_service = llm_service
        self.anonymizer = anonymizer

    async def run(self, query: str, plan: dict, retrieval: dict) -> str:
        citations: list[Citation] = retrieval["citations"]
        sources: list[SourceChunk] = retrieval["sources"]
        context_blocks: list[str] = retrieval["context_blocks"]

        if not context_blocks:
            return self._gap_answer(query, citations, sources)

        redacted_query = self.anonymizer.anonymize_text(query).redacted_text
        prompt = AGENT_SYNTHESIS_PROMPT.format(
            query=redacted_query,
            plan_focus=plan.get("focus", query),
            documents=join_context_blocks(context_blocks)[: self.settings.max_prompt_context_chars],
        )
        try:
            return await self.llm_service.complete(prompt, task="research")
        except ServiceUnavailableError:
            return self._fallback_answer(query, citations, sources)

    def _gap_answer(self, query: str, citations: list[Citation], sources: list[SourceChunk]) -> str:
        lines = [
            "Direct Answer:",
            f"I could not find reliable authorities for '{query}' in the indexed corpus.",
            "",
            "Relevant Case Laws:",
        ]
        if citations:
            lines.extend(
                f"- {item.title} | {item.citation or 'Citation unavailable'} | {item.court or 'Court not provided'}"
                for item in citations[:5]
            )
        else:
            lines.append("- No close matches are currently indexed.")
        lines.extend(
            [
                "",
                "Explanation:",
                "The available sources do not sufficiently cover this query. Upload more relevant judgments or legal materials and retry.",
            ]
        )
        if sources:
            lines.extend(["", "Key Excerpts:"])
            lines.extend(f"{index}. {item.excerpt}" for index, item in enumerate(sources[:3], start=1))
        return "\n".join(lines)

    def _fallback_answer(self, query: str, citations: list[Citation], sources: list[SourceChunk]) -> str:
        citation_lines = [
            f"- {item.title} | {item.citation or 'Citation unavailable'} | {item.court or 'Court not provided'}"
            for item in citations[:5]
        ]
        excerpt_lines = [f"{index}. {item.excerpt}" for index, item in enumerate(sources[:3], start=1)]
        return "\n".join(
            [
                "Direct Answer:",
                f"I found potentially relevant materials for '{query}', but synthesis is currently unavailable.",
                "",
                "Relevant Case Laws:",
                *(citation_lines or ["- No structured citations are available."]),
                "",
                "Explanation:",
                "Use the listed authorities and excerpts as source-first fallback until synthesis service recovers.",
                *(["", "Key Excerpts:", *excerpt_lines] if excerpt_lines else []),
            ]
        )
