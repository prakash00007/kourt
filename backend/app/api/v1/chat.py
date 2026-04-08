from fastapi import APIRouter, Depends

from app.api.deps import get_container, get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.container import ServiceContainer

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    container: ServiceContainer = Depends(get_container),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    return await container.research_service.answer(payload)
