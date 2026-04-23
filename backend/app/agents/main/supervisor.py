from app.agents.shared.trace import AgentStepTrace
from app.agents.tasks.drafting.supervisor import DraftingTaskSupervisorAgent
from app.agents.tasks.research.supervisor import ResearchTaskSupervisorAgent
from app.agents.tasks.summarization.supervisor import SummarizationTaskSupervisorAgent
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.draft import DraftRequest, DraftResponse


class MainSupervisorAgent:
    def __init__(
        self,
        research_supervisor: ResearchTaskSupervisorAgent,
        drafting_supervisor: DraftingTaskSupervisorAgent,
        summarization_supervisor: SummarizationTaskSupervisorAgent,
    ):
        self.research_supervisor = research_supervisor
        self.drafting_supervisor = drafting_supervisor
        self.summarization_supervisor = summarization_supervisor

    async def execute_research(
        self,
        payload: ChatRequest,
        *,
        include_trace: bool = False,
    ) -> tuple[ChatResponse, list[AgentStepTrace], str]:
        response, trace, workflow_id = await self.research_supervisor.execute(payload, include_trace=include_trace)
        return response, self._report_trace("research", trace) if include_trace else [], workflow_id

    async def execute_research_for_chat(self, payload: ChatRequest) -> ChatResponse:
        response, _, _ = await self.execute_research(payload, include_trace=False)
        return response

    async def execute_drafting(
        self,
        payload: DraftRequest,
        *,
        include_trace: bool = False,
    ) -> tuple[DraftResponse, list[AgentStepTrace], str]:
        response, trace, workflow_id = await self.drafting_supervisor.execute(payload, include_trace=include_trace)
        return response, self._report_trace("drafting", trace) if include_trace else [], workflow_id

    def _report_trace(self, task: str, trace: list[AgentStepTrace]) -> list[AgentStepTrace]:
        summary = f"main supervisor compiled task report for {task}"
        total_ms = round(sum(item.duration_ms for item in trace), 2)
        return trace + [AgentStepTrace(agent="main/supervisor-subagent", summary=summary, duration_ms=total_ms)]
