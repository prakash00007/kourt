from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, AsyncSession

from app.agents.main.supervisor import MainSupervisorAgent
from app.agents.tasks.drafting.subagents.drafting_worker import DraftingWorkerSubAgent
from app.agents.tasks.drafting.supervisor import DraftingTaskSupervisorAgent
from app.agents.tasks.research.supervisor import ResearchTaskSupervisorAgent
from app.agents.tasks.summarization.subagents.summarization_worker import SummarizationWorkerSubAgent
from app.agents.tasks.summarization.supervisor import SummarizationTaskSupervisorAgent
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
        self.research_task_supervisor = ResearchTaskSupervisorAgent(
            settings,
            self.vector_store,
            self.llm_service,
            self.cache_service,
            self.anonymizer_service,
        )
        self.drafting_worker_subagent = DraftingWorkerSubAgent(self.drafting_service)
        self.drafting_task_supervisor = DraftingTaskSupervisorAgent(self.drafting_worker_subagent)
        self.summarization_worker_subagent = SummarizationWorkerSubAgent(self.summarization_service)
        self.summarization_task_supervisor = SummarizationTaskSupervisorAgent(self.summarization_worker_subagent)
        self.main_supervisor_agent = MainSupervisorAgent(
            self.research_task_supervisor,
            self.drafting_task_supervisor,
            self.summarization_task_supervisor,
        )
        # Backward-compatible alias for existing callers.
        self.hierarchical_research_service = self.research_task_supervisor

    async def close(self) -> None:
        await self.redis.aclose()
        await self.engine.dispose()
