import hashlib
from dataclasses import asdict
from time import perf_counter
from typing import Any
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.agents.shared.trace import AgentStepTrace
from app.agents.tasks.research.subagents.planner import ResearchPlannerSubAgent
from app.agents.tasks.research.subagents.retriever import ResearchRetrieverSubAgent
from app.agents.tasks.research.subagents.synthesizer import ResearchSynthesizerSubAgent
from app.agents.tasks.research.subagents.verifier import ResearchVerifierSubAgent
from app.agents.tasks.research.state import ResearchGraphState
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
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        workflow = StateGraph(ResearchGraphState)
        workflow.add_node("planner_subagent", self._planner_node)
        workflow.add_node("retriever_subagent", self._retriever_node)
        workflow.add_node("synthesizer_subagent", self._synthesizer_node)
        workflow.add_node("verifier_subagent", self._verifier_node)
        workflow.add_edge(START, "planner_subagent")
        workflow.add_edge("planner_subagent", "retriever_subagent")
        workflow.add_edge("retriever_subagent", "synthesizer_subagent")
        workflow.add_edge("synthesizer_subagent", "verifier_subagent")
        workflow.add_edge("verifier_subagent", END)
        return workflow.compile()

    async def _planner_node(self, state: ResearchGraphState) -> ResearchGraphState:
        started = perf_counter()
        plan = await self.planner.run(state["query"])
        trace = self._append_trace(
            state,
            "research/planner-subagent",
            f"strategy={plan.get('strategy', 'default')}, terms={len(plan.get('must_have_terms', []))}",
            started,
        )
        return {"plan": plan, "trace": trace}

    def _retriever_node(self, state: ResearchGraphState) -> ResearchGraphState:
        started = perf_counter()
        retrieval = self.retriever.run(state["query"], state.get("plan") or {})
        trace = self._append_trace(
            state,
            "research/retriever-subagent",
            f"documents={len(retrieval['documents'])}",
            started,
        )
        return {"retrieval": retrieval, "trace": trace}

    async def _synthesizer_node(self, state: ResearchGraphState) -> ResearchGraphState:
        started = perf_counter()
        retrieval = state.get("retrieval") or self._empty_retrieval()
        answer = await self.synthesizer.run(state["query"], state.get("plan") or {}, retrieval)
        trace = self._append_trace(
            state,
            "research/synthesizer-subagent",
            "drafted grounded legal answer",
            started,
        )
        return {"answer": answer, "trace": trace}

    async def _verifier_node(self, state: ResearchGraphState) -> ResearchGraphState:
        started = perf_counter()
        retrieval = state.get("retrieval") or self._empty_retrieval()
        verified_answer, verification_note = await self.verifier.run(state["query"], state.get("answer", ""), retrieval)
        trace = self._append_trace(
            state,
            "research/verifier-subagent",
            verification_note,
            started,
        )
        return {
            "answer": verified_answer,
            "verification_note": verification_note,
            "trace": trace,
        }

    def _append_trace(
        self,
        state: ResearchGraphState,
        agent: str,
        summary: str,
        started: float,
    ) -> list[dict[str, Any]]:
        trace = list(state.get("trace") or [])
        trace.append(
            {
                "agent": agent,
                "summary": summary,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            }
        )
        return trace

    def _empty_retrieval(self) -> dict[str, Any]:
        return {
            "documents": [],
            "context_blocks": [],
            "citations": [],
            "sources": [],
        }

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

        final_state = await self.workflow.ainvoke({"query": payload.query, "trace": []})
        retrieval = final_state.get("retrieval") or self._empty_retrieval()
        verified_answer = str(final_state.get("answer") or "")
        trace = [AgentStepTrace(**item) for item in final_state.get("trace") or []]

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
