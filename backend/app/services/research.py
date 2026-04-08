import hashlib
import re

from app.core.exceptions import ServiceUnavailableError
from app.services.anonymizer import AnonymizerService
from app.core.config import Settings
from app.core.cache import RedisCacheService
from app.schemas.chat import ChatRequest, ChatResponse, Citation, SourceChunk
from app.services.llm import LLMService
from app.services.vector_store import VectorStore
from app.utils.prompts import RESEARCH_PROMPT
from app.utils.text import join_context_blocks, truncate_text


SIGNAL_STOPWORDS = {
    "about",
    "also",
    "and",
    "case",
    "cases",
    "give",
    "help",
    "here",
    "into",
    "legal",
    "law",
    "laws",
    "me",
    "need",
    "please",
    "query",
    "research",
    "show",
    "tell",
    "this",
    "those",
    "that",
    "the",
    "these",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}


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
            response = self._build_gap_response(payload.query, [], set(), set())
            await self.cache.set_json("research", cache_key, response.model_dump(mode="json"))
            return response

        query_terms, has_strong_anchor = self._extract_signal_terms(payload.query)
        anchor_terms = {
            token.lower()
            for token in re.findall(r"[A-Za-z0-9]+", payload.query)
            if (token.isupper() and len(token) >= 3) or token.isdigit()
        }
        top_score = max((item.get("score") or 0.0) for item in retrieved)
        query_is_covered = self._query_is_covered(query_terms, anchor_terms, retrieved)
        if query_terms and ((has_strong_anchor and not query_is_covered) or (top_score < 0.4 and not query_is_covered)):
            response = self._build_gap_response(payload.query, retrieved, query_terms, anchor_terms)
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

    def _extract_signal_terms(self, query: str) -> tuple[set[str], bool]:
        tokens = re.findall(r"[A-Za-z0-9]+", query.lower())
        terms: set[str] = set()
        has_strong_anchor = False
        for token in tokens:
            if token.isdigit():
                terms.add(token)
                has_strong_anchor = True
                continue
            if len(token) < 4 or token in SIGNAL_STOPWORDS:
                continue
            terms.add(token)
        raw_tokens = re.findall(r"[A-Za-z0-9]+", query)
        for token in raw_tokens:
            if token.isdigit():
                has_strong_anchor = True
                continue
            if token.isupper() and len(token) >= 3:
                has_strong_anchor = True
        return terms, has_strong_anchor

    def _matches_query_terms(self, query_terms: set[str], anchor_terms: set[str], item: dict) -> bool:
        metadata = item.get("metadata") or {}
        text_parts = [
            str(metadata.get("title", "")),
            str(metadata.get("citation", "")),
            str(metadata.get("court", "")),
            item.get("text", ""),
        ]
        haystack = " ".join(text_parts).lower()

        if anchor_terms and not all(anchor in haystack for anchor in anchor_terms):
            return False

        if query_terms:
            return any(term in haystack for term in query_terms)
        return True

    def _query_is_covered(self, query_terms: set[str], anchor_terms: set[str], retrieved: list[dict]) -> bool:
        if not query_terms:
            return True

        for item in retrieved:
            if self._matches_query_terms(query_terms, anchor_terms, item):
                return True
        return False

    def _build_gap_response(
        self,
        query: str,
        retrieved: list[dict],
        query_terms: set[str],
        anchor_terms: set[str],
    ) -> ChatResponse:
        citations: list[Citation] = []
        sources: list[SourceChunk] = []

        filtered_items = [item for item in retrieved if self._matches_query_terms(query_terms, anchor_terms, item)]

        for index, item in enumerate(filtered_items, start=1):
            metadata = item.get("metadata") or {}
            title = metadata.get("title", f"Document {index}")
            citation = metadata.get("citation")
            court = metadata.get("court")
            source_url = metadata.get("source_url")
            excerpt = truncate_text(item.get("text", ""), 140)

            citations.append(
                Citation(
                    title=title,
                    citation=citation,
                    court=court,
                    source_url=source_url,
                    relevance_score=item.get("score"),
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

        answer_lines = [
            "Direct Answer:",
            f"I could not find authorities matching '{query}' in the current knowledge base.",
            "",
            "Relevant Case Laws:",
        ]

        if citations:
            answer_lines.extend(
                f"- {item.title} | {item.citation or 'Citation unavailable'} | {item.court or 'Court not provided'}"
                for item in citations[:5]
            )
        else:
            answer_lines.append("- No close matches are currently indexed.")

        answer_lines.extend(
            [
                "",
                "Explanation:",
                "The indexed corpus does not appear to cover this topic yet, so I am not going to invent case law from unrelated materials. Upload the relevant judgments or connect a newer corpus, then re-run ingestion.",
            ]
        )
        if sources:
            answer_lines.extend(["", "Key Excerpts:"])
            answer_lines.extend(
                f"{index}. {item.excerpt}" for index, item in enumerate(sources[:3], start=1)
            )

        return ChatResponse(
            answer="\n".join(answer_lines),
            citations=citations,
            sources=sources,
            disclaimer=self.settings.disclaimer_text,
        )

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
