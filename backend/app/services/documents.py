from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.document_metadata import DocumentMetadata


class DocumentService:
    async def create_metadata(self, session: AsyncSession, *, user_id, filename: str, s3_object_key: str) -> DocumentMetadata:
        record = DocumentMetadata(user_id=user_id, filename=filename, s3_object_key=s3_object_key)
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    async def get_document_for_user(
        self,
        session: AsyncSession,
        *,
        document_id: UUID,
        user_id: UUID,
    ) -> DocumentMetadata:
        record = await session.scalar(
            select(DocumentMetadata).where(
                DocumentMetadata.id == document_id,
                DocumentMetadata.user_id == user_id,
            )
        )
        if record is None:
            raise NotFoundError("Document not found.")
        return record
