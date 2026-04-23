from fastapi import APIRouter, Depends

from app.api.deps import get_container, get_current_user
from app.models.user import User
from app.schemas.agent import AgentResearchRequest, AgentResearchResponse, AgentTraceStep
from app.schemas.chat import ChatRequest
from app.services.container import ServiceContainer

router = APIRouter()


@router.post("/research", response_model=AgentResearchResponse)
async def multi_agent_research(
    payload: AgentResearchRequest,
    container: ServiceContainer = Depends(get_container),
    current_user: User = Depends(get_current_user),
) -> AgentResearchResponse:
    chat_payload = ChatRequest(query=payload.query)
    response, trace, workflow_id = await container.main_supervisor_agent.execute_research(
        chat_payload,
        include_trace=payload.include_trace,
    )
    return AgentResearchResponse(
        answer=response.answer,
        citations=response.citations,
        sources=response.sources,
        disclaimer=response.disclaimer,
        workflow_id=workflow_id,
        trace=[AgentTraceStep(**step.__dict__) for step in trace] if payload.include_trace else [],
    )
