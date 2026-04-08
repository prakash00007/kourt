from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession

from app.core.config import Settings
from app.core.cache import RedisCacheService
from app.db.session import create_engine, create_session_factory
from app.services.auth import AuthService
from app.services.drafting import DraftingService
from app.services.documents import DocumentService
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMService
from app.services.research import ResearchService
from app.services.storage import StorageService
from app.services.summarization import SummarizationService
from app.services.anonymizer import AnonymizerService
from app.services.usage_metering import UsageMeteringService
from app.services.vector_store import VectorStore


class ServiceContainer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self.cache_service = RedisCacheService(settings, self.redis)
        self.engine: AsyncEngine = create_engine(settings)
        self.session_factory: async_sessionmaker[AsyncSession] = create_session_factory(self.engine)
        self.embedding_service = EmbeddingService(settings)
        self.vector_store = VectorStore(settings, self.embedding_service)
        self.llm_service = LLMService(settings)
        self.storage_service = StorageService(settings)
        self.anonymizer_service = AnonymizerService()
        self.usage_metering_service = UsageMeteringService(settings, self.redis)
        self.auth_service = AuthService(settings)
        self.document_service = DocumentService()
        self.research_service = ResearchService(
            settings,
            self.vector_store,
            self.llm_service,
            self.cache_service,
            self.anonymizer_service,
        )
        self.summarization_service = SummarizationService(
            settings,
            self.llm_service,
            self.cache_service,
            self.storage_service,
            self.anonymizer_service,
        )
        self.drafting_service = DraftingService(
            settings,
            self.llm_service,
            self.cache_service,
            self.anonymizer_service,
        )

    async def close(self) -> None:
        await self.redis.aclose()
        await self.engine.dispose()
