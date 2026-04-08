from fastapi import APIRouter, Depends

from app.api.deps import enforce_draft_quota, get_container
from app.models.user import User
from app.schemas.draft import DraftRequest, DraftResponse
from app.services.container import ServiceContainer

router = APIRouter()


@router.post("", response_model=DraftResponse)
async def draft(
    payload: DraftRequest,
    container: ServiceContainer = Depends(get_container),
    current_user: User = Depends(enforce_draft_quota),
) -> DraftResponse:
    return await container.drafting_service.generate(payload)
