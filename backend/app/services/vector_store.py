from collections.abc import Sequence
from typing import Any
import logging

import chromadb
from chromadb.config import Settings as ChromaClientSettings

from app.core.config import Settings
from app.core.exceptions import RetrievalError
from app.services.embeddings import EmbeddingService


logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, settings: Settings, embedding_service: EmbeddingService):
        self.settings = settings
        self.embedding_service = embedding_service
        self.client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=ChromaClientSettings(anonymized_telemetry=not settings.disable_chroma_telemetry),
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"description": "Indian legal corpus for Kourt MVP"},
        )

    def add_documents(
        self,
        ids: Sequence[str],
        texts: Sequence[str],
        metadatas: Sequence[dict[str, Any]],
    ) -> None:
        embeddings = self.embedding_service.embed_documents(texts)
        self.collection.upsert(
            ids=list(ids),
            documents=list(texts),
            embeddings=embeddings,
            metadatas=list(metadatas),
        )

    def search(self, query: str, limit: int | None = None) -> list[dict[str, Any]]:
        limit = limit or self.settings.retrieval_k
        try:
            responses = [self._query_with_embedding(query, limit)]
            for variant in self._build_query_variants(query):
                if variant.strip().lower() == query.strip().lower():
                    continue
                responses.append(self._query_with_embedding(variant, limit))
        except Exception as exc:
            logger.exception("Vector search failed")
            raise RetrievalError() from exc

        results: list[dict[str, Any]] = []
        fallback_results: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        merged_items: list[dict[str, Any]] = []

        for response in responses:
            documents = response.get("documents", [[]])[0]
            metadatas = response.get("metadatas", [[]])[0]
            distances = response.get("distances", [[]])[0]
            for document, metadata, distance in zip(documents, metadatas, distances, strict=False):
                score = None
                if distance is not None:
                    # Chroma returns a distance, not a similarity score. Normalize it into
                    # a bounded 0..1 range so our downstream threshold is meaningful.
                    score = max(0.0, 1.0 - min(float(distance), 2.0) / 2.0)

                dedupe_key = f"{(metadata or {}).get('title','')}::{(metadata or {}).get('citation','')}::{document[:120]}"
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)
                merged_items.append(
                    {
                        "text": document,
                        "metadata": metadata or {},
                        "score": score,
                    }
                )

        for item in merged_items:
            item["score"] = self._apply_keyword_boost(query, item)
            fallback_results.append(item)
            if item["score"] is None or item["score"] >= self.settings.min_similarity_score:
                results.append(item)

        results.sort(key=lambda item: item.get("score") or 0.0, reverse=True)
        fallback_results.sort(key=lambda item: item.get("score") or 0.0, reverse=True)

        if results:
            return results[:limit]
        return fallback_results[:limit]

    def _query_with_embedding(self, query: str, limit: int) -> dict[str, Any]:
        query_embedding = self.embedding_service.embed_query(query)
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )

    def _build_query_variants(self, query: str) -> list[str]:
        normalized = query.lower()
        variants: list[str] = []
        if any(token in normalized for token in ["ndps", "narcotic", "psychotropic", "section 37", "commercial quantity"]):
            variants.extend(
                [
                    "NDPS Act bail section 37 Narcotics Control Bureau",
                    "commercial quantity NDPS bail",
                    "psychotropic substances NDPS bail",
                    "Narcotics Control Bureau versus Kashif",
                    "Frank Vitus versus Narcotics Control Bureau",
                ]
            )
        elif "bail" in normalized:
            variants.extend(
                [
                    "bail section 37 Narcotics Control Bureau",
                    "commercial quantity bail",
                    "Narcotics Control Bureau versus Kashif",
                ]
            )
        return variants

    def _apply_keyword_boost(self, query: str, item: dict[str, Any]) -> float | None:
        score = item.get("score")
        if score is None:
            return None

        haystack = " ".join(
            [
                str((item.get("metadata") or {}).get("title", "")),
                str((item.get("metadata") or {}).get("citation", "")),
                str((item.get("metadata") or {}).get("court", "")),
                item.get("text", ""),
            ]
        ).lower()
        boost_terms = {
            "ndps": 0.12,
            "narcotic": 0.12,
            "psychotropic": 0.12,
            "section 37": 0.10,
            "commercial quantity": 0.10,
            "narcotics control bureau": 0.10,
            "bail": 0.05,
        }
        boost = 0.0
        for term, term_boost in boost_terms.items():
            if term in haystack and term in query.lower():
                boost += term_boost
        return min(1.0, score + boost)
