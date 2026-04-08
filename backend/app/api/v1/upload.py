from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_container, get_current_user, get_db_session
from app.models.user import User
from app.schemas.summary import SummaryResponse
from app.services.container import ServiceContainer

router = APIRouter()


@router.post("", response_model=SummaryResponse)
async def upload_judgment(
    file: UploadFile = File(...),
    container: ServiceContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> SummaryResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are supported.")
    result, _object_key = await container.summarization_service.summarize_pdf(file)
    await container.document_service.create_metadata(
        session,
        user_id=current_user.id,
        filename=result.file_name,
        s3_object_key=_object_key,
    )
    return result
