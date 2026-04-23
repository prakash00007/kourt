from typing import Any

from app.core.config import Settings
from app.schemas.chat import Citation, SourceChunk
from app.services.vector_store import VectorStore
from app.utils.text import truncate_text


class ResearchRetrieverSubAgent:
    def __init__(self, settings: Settings, vector_store: VectorStore):
        self.settings = settings
        self.vector_store = vector_store

    def run(self, query: str, plan: dict[str, Any]) -> dict[str, Any]:
        retrieved = self.vector_store.search(query, limit=self.settings.max_context_documents)

        required_terms = {term.lower() for term in plan.get("must_have_terms", []) if str(term).strip()}
        if required_terms:
            filtered = [item for item in retrieved if self._matches_terms(required_terms, item)]
            if filtered:
                retrieved = filtered

        context_blocks: list[str] = []
        citations: list[Citation] = []
        sources: list[SourceChunk] = []

        for index, item in enumerate(retrieved, start=1):
            metadata = item.get("metadata") or {}
            title = metadata.get("title", f"Document {index}")
            citation = metadata.get("citation")
            court = metadata.get("court")
            source_url = metadata.get("source_url")
            excerpt = truncate_text(item.get("text", ""), 140)
            context_blocks.append(
                "\n".join(
                    [
                        f"[Source {index}]",
                        f"Title: {title}",
                        f"Citation: {citation or 'Not available'}",
                        f"Court: {court or 'Not available'}",
                        f"URL: {source_url or 'Not available'}",
                        f"Content: {item.get('text', '')}",
                    ]
                )
            )
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

        return {
            "documents": retrieved,
            "context_blocks": context_blocks,
            "citations": citations,
            "sources": sources,
        }

    def _matches_terms(self, required_terms: set[str], item: dict[str, Any]) -> bool:
        metadata = item.get("metadata") or {}
        haystack = " ".join(
            [
                str(metadata.get("title", "")),
                str(metadata.get("citation", "")),
                str(metadata.get("court", "")),
                item.get("text", ""),
            ]
        ).lower()
        return all(term in haystack for term in required_terms)
