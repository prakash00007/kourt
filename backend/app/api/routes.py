from fastapi import APIRouter

from app.api.v1 import auth, chat, documents, draft, health, upload
from app.api.v1 import chat_runtime


router = APIRouter()
router.include_router(health.router, tags=["health"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
router.include_router(documents.router, prefix="/v1/documents", tags=["documents"])
router.include_router(chat_runtime.router, prefix="/chat", tags=["chat"])
router.include_router(upload.router, prefix="/upload", tags=["upload"])
router.include_router(upload.router, prefix="/v1/upload", tags=["upload"])
router.include_router(draft.router, prefix="/draft", tags=["draft"])
router.include_router(draft.router, prefix="/v1/draft", tags=["draft"])
