from collections.abc import Sequence
from typing import Any
import logging

import chromadb

from app.core.config import Settings
from app.core.exceptions import RetrievalError
from app.services.embeddings import EmbeddingService


logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, settings: Settings, embedding_service: EmbeddingService):
        self.settings = settings
        self.embedding_service = embedding_service
        self.client = chromadb.PersistentClient(path=settings.chroma_path)
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
        self.collection.add(
            ids=list(ids),
            documents=list(texts),
            embeddings=embeddings,
            metadatas=list(metadatas),
        )

    def search(self, query: str, limit: int | None = None) -> list[dict[str, Any]]:
        limit = limit or self.settings.retrieval_k
        try:
            query_embedding = self.embedding_service.embed_query(query)
            response = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.exception("Vector search failed")
            raise RetrievalError() from exc

        documents = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]

        results: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for document, metadata, distance in zip(documents, metadatas, distances, strict=False):
            score = 1 - distance if distance is not None else None
            if score is not None and score < self.settings.min_similarity_score:
                continue
            dedupe_key = f"{(metadata or {}).get('title','')}::{(metadata or {}).get('citation','')}::{document[:120]}"
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            results.append(
                {
                    "text": document,
                    "metadata": metadata or {},
                    "score": score,
                }
            )
        return results
