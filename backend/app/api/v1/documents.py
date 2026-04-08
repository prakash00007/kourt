from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_container, get_current_user, get_db_session
from app.models.user import User
from app.schemas.document import DocumentURLResponse
from app.services.container import ServiceContainer

router = APIRouter()


@router.get("/{document_id}/url", response_model=DocumentURLResponse)
async def get_document_url(
    document_id: UUID,
    container: ServiceContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DocumentURLResponse:
    document = await container.document_service.get_document_for_user(
        session,
        document_id=document_id,
        user_id=current_user.id,
    )
    url = await container.storage_service.generate_presigned_download_url(
        document.s3_object_key,
        file_name=document.filename,
    )
    return DocumentURLResponse(url=url, expires_in_seconds=container.settings.s3_presign_expiry_seconds)
