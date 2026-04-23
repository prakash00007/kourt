from time import perf_counter
from uuid import uuid4

from app.agents.shared.trace import AgentStepTrace
from app.agents.tasks.drafting.subagents.drafting_worker import DraftingWorkerSubAgent
from app.schemas.draft import DraftRequest, DraftResponse


class DraftingTaskSupervisorAgent:
    def __init__(self, worker: DraftingWorkerSubAgent):
        self.worker = worker

    async def execute(
        self,
        payload: DraftRequest,
        *,
        include_trace: bool = False,
    ) -> tuple[DraftResponse, list[AgentStepTrace], str]:
        workflow_id = str(uuid4())
        started = perf_counter()
        response = await self.worker.run(payload)
        trace = [
            AgentStepTrace(
                agent="drafting/worker-subagent",
                summary="generated draft from matter details",
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
        ]
        return response, trace if include_trace else [], workflow_id
