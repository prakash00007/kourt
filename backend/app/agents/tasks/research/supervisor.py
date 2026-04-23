import hashlib
from dataclasses import asdict
from time import perf_counter
from uuid import uuid4

from app.agents.shared.trace import AgentStepTrace
from app.agents.tasks.research.subagents.planner import ResearchPlannerSubAgent
from app.agents.tasks.research.subagents.retriever import ResearchRetrieverSubAgent
from app.agents.tasks.research.subagents.synthesizer import ResearchSynthesizerSubAgent
from app.agents.tasks.research.subagents.verifier import ResearchVerifierSubAgent
from app.core.cache import RedisCacheService
from app.core.config import Settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.anonymizer import AnonymizerService
from app.services.llm import LLMService
from app.services.vector_store import VectorStore


class ResearchTaskSupervisorAgent:
    def __init__(
        self,
        settings: Settings,
        vector_store: VectorStore,
        llm_service: LLMService,
        cache_service: RedisCacheService,
        anonymizer_service: AnonymizerService,
    ):
        self.settings = settings
        self.cache = cache_service
        self.planner = ResearchPlannerSubAgent(llm_service)
        self.retriever = ResearchRetrieverSubAgent(settings, vector_store)
        self.synthesizer = ResearchSynthesizerSubAgent(settings, llm_service, anonymizer_service)
        self.verifier = ResearchVerifierSubAgent(llm_service)

    async def execute(
        self,
        payload: ChatRequest,
        *,
        include_trace: bool = False,
    ) -> tuple[ChatResponse, list[AgentStepTrace], str]:
        workflow_id = str(uuid4())
        cache_key = hashlib.sha256(payload.query.strip().lower().encode("utf-8")).hexdigest()
        cached = await self.cache.get_json("agent_research", cache_key)
        if cached is not None:
            response = ChatResponse.model_validate(cached["response"])
            cached_trace = [AgentStepTrace(**item) for item in cached.get("trace", [])]
            return response, cached_trace if include_trace else [], cached.get("workflow_id", workflow_id)

        trace: list[AgentStepTrace] = []

        started = perf_counter()
        plan = await self.planner.run(payload.query)
        trace.append(
            AgentStepTrace(
                agent="research/planner-subagent",
                summary=f"strategy={plan.get('strategy', 'default')}, terms={len(plan.get('must_have_terms', []))}",
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
        )

        started = perf_counter()
        retrieval = self.retriever.run(payload.query, plan)
        trace.append(
            AgentStepTrace(
                agent="research/retriever-subagent",
                summary=f"documents={len(retrieval['documents'])}",
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
        )

        started = perf_counter()
        answer = await self.synthesizer.run(payload.query, plan, retrieval)
        trace.append(
            AgentStepTrace(
                agent="research/synthesizer-subagent",
                summary="drafted grounded legal answer",
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
        )

        started = perf_counter()
        verified_answer, verification_note = await self.verifier.run(payload.query, answer, retrieval)
        trace.append(
            AgentStepTrace(
                agent="research/verifier-subagent",
                summary=verification_note,
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
        )

        response = ChatResponse(
            answer=verified_answer,
            citations=retrieval["citations"],
            sources=retrieval["sources"],
            disclaimer=self.settings.disclaimer_text,
        )

        await self.cache.set_json(
            "agent_research",
            cache_key,
            {
                "workflow_id": workflow_id,
                "response": response.model_dump(mode="json"),
                "trace": [asdict(step) for step in trace],
            },
        )
        return response, trace if include_trace else [], workflow_id

    async def execute_for_chat(self, payload: ChatRequest) -> ChatResponse:
        response, _, _ = await self.execute(payload, include_trace=False)
        return response
