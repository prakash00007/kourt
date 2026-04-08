import hashlib

from app.core.exceptions import ServiceUnavailableError
from app.services.anonymizer import AnonymizerService
from app.core.config import Settings
from app.core.cache import RedisCacheService
from app.schemas.chat import ChatRequest, ChatResponse, Citation, SourceChunk
from app.services.llm import LLMService
from app.services.vector_store import VectorStore
from app.utils.prompts import RESEARCH_PROMPT
from app.utils.text import join_context_blocks, truncate_text


class ResearchService:
    def __init__(
        self,
        settings: Settings,
        vector_store: VectorStore,
        llm_service: LLMService,
        cache_service: RedisCacheService,
        anonymizer_service: AnonymizerService,
    ):
        self.settings = settings
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.cache = cache_service
        self.anonymizer = anonymizer_service

    async def answer(self, payload: ChatRequest) -> ChatResponse:
        cache_key = hashlib.sha256(payload.query.strip().lower().encode("utf-8")).hexdigest()
        cached = await self.cache.get_json("research", cache_key)
        if cached is not None:
            return ChatResponse.model_validate(cached)

        retrieved = self.vector_store.search(payload.query, limit=self.settings.max_context_documents)

        if not retrieved:
            response = ChatResponse(
                answer="I could not find relevant Indian legal materials in the current knowledge base for this query.",
                citations=[],
                sources=[],
                disclaimer=self.settings.disclaimer_text,
            )
            await self.cache.set_json("research", cache_key, response.model_dump(mode="json"))
            return response

        context_blocks: list[str] = []
        citations: list[Citation] = []
        sources: list[SourceChunk] = []

        for index, item in enumerate(retrieved, start=1):
            metadata = item["metadata"]
            title = metadata.get("title", f"Document {index}")
            citation = metadata.get("citation")
            court = metadata.get("court")
            source_url = metadata.get("source_url")
            excerpt = truncate_text(item["text"], 140)

            context_blocks.append(
                "\n".join(
                    [
                        f"[Source {index}]",
                        f"Title: {title}",
                        f"Citation: {citation or 'Not available'}",
                        f"Court: {court or 'Not available'}",
                        f"URL: {source_url or 'Not available'}",
                        f"Content: {item['text']}",
                    ]
                )
            )

            citations.append(
                Citation(
                    title=title,
                    citation=citation,
                    court=court,
                    source_url=source_url,
                    relevance_score=item["score"],
                )
            )
            sources.append(
                SourceChunk(
                    title=title,
                    excerpt=excerpt,
                    citation=citation,
                    source_url=source_url,
                )
            )

        redacted_query = self.anonymizer.anonymize_text(payload.query).redacted_text
        prompt = RESEARCH_PROMPT.format(
            query=redacted_query,
            documents=join_context_blocks(context_blocks)[: self.settings.max_prompt_context_chars],
        )
        try:
            answer = await self.llm_service.complete(prompt, task="research")
        except ServiceUnavailableError:
            answer = self._build_local_fallback_answer(payload.query, citations, sources)

        response = ChatResponse(
            answer=answer,
            citations=citations,
            sources=sources,
            disclaimer=self.settings.disclaimer_text,
        )
        await self.cache.set_json("research", cache_key, response.model_dump(mode="json"))
        return response

    def _build_local_fallback_answer(
        self,
        query: str,
        citations: list[Citation],
        sources: list[SourceChunk],
    ) -> str:
        citation_lines = [
            f"- {item.title} | {item.citation or 'Citation unavailable'} | {item.court or 'Court not provided'}"
            for item in citations[:5]
        ]
        excerpt_lines = [f"{index}. {item.excerpt}" for index, item in enumerate(sources[:3], start=1)]

        return "\n".join(
            [
                "Direct Answer:",
                f"I found potentially relevant materials for the query '{query}', but the AI synthesis service is unavailable right now.",
                "",
                "Relevant Case Laws:",
                *(citation_lines or ["- No structured citations are available."]),
                "",
                "Explanation:",
                "Review the listed authorities and excerpts below as a source-first fallback. A synthesized legal analysis could not be generated locally.",
                *(["", "Key Excerpts:", *excerpt_lines] if excerpt_lines else []),
            ]
        )
