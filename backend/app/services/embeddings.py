from typing import Sequence

from openai import OpenAI
from sentence_transformers import SentenceTransformer

from app.core.config import Settings


class EmbeddingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._st_model: SentenceTransformer | None = None
        self._openai_client: OpenAI | None = None

        if settings.embedding_provider == "sentence-transformers":
            model_name = settings.embedding_model.replace("sentence-transformers/", "")
            self._st_model = SentenceTransformer(model_name)
        elif settings.embedding_provider == "openai":
            self._openai_client = OpenAI(api_key=settings.openai_api_key)
        else:
            raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if self._st_model is not None:
            embeddings = self._st_model.encode(list(texts), normalize_embeddings=True)
            return embeddings.tolist()

        if self._openai_client is None:
            raise RuntimeError("OpenAI client is not configured for embeddings.")

        response = self._openai_client.embeddings.create(
            model=self.settings.openai_embedding_model,
            input=list(texts),
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
