from dataclasses import dataclass


@dataclass
class AgentStepTrace:
    agent: str
    summary: str
    duration_ms: float


@dataclass
class AgentWorkflowReport:
    workflow_id: str
    task: str
    supervisor: str
    steps: list[AgentStepTrace]
