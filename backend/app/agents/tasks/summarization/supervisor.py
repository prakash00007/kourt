from time import perf_counter
from uuid import uuid4

from fastapi import UploadFile

from app.agents.shared.trace import AgentStepTrace
from app.agents.tasks.summarization.subagents.summarization_worker import SummarizationWorkerSubAgent
from app.schemas.summary import SummaryResponse


class SummarizationTaskSupervisorAgent:
    def __init__(self, worker: SummarizationWorkerSubAgent):
        self.worker = worker

    async def execute(
        self,
        upload: UploadFile,
        *,
        include_trace: bool = False,
    ) -> tuple[SummaryResponse, str, list[AgentStepTrace], str]:
        workflow_id = str(uuid4())
        started = perf_counter()
        response, object_key = await self.worker.run(upload)
        trace = [
            AgentStepTrace(
                agent="summarization/worker-subagent",
                summary="summarized uploaded judgment",
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
        ]
        return response, object_key, trace if include_trace else [], workflow_id
