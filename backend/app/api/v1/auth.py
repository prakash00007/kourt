from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_container, get_db_session
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse
from app.services.container import ServiceContainer

router = APIRouter()


@router.post("/signup", response_model=TokenResponse)
async def signup(
    payload: SignupRequest,
    container: ServiceContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    return await container.auth_service.signup(session, payload)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    container: ServiceContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    return await container.auth_service.login(session, payload)
