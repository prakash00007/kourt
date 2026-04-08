from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserResponse


class AuthService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def signup(self, session: AsyncSession, payload: SignupRequest) -> TokenResponse:
        existing = await session.scalar(select(User).where(User.email == payload.email.lower()))
        if existing:
            raise ValidationError("An account with this email already exists.")

        user = User(
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            tier=payload.tier,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token = create_access_token(self.settings, user.id, user.email)
        return TokenResponse(access_token=token, user=UserResponse.model_validate(user))

    async def login(self, session: AsyncSession, payload: LoginRequest) -> TokenResponse:
        user = await session.scalar(select(User).where(User.email == payload.email.lower()))
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise ValidationError("Invalid email or password.")

        token = create_access_token(self.settings, user.id, user.email)
        return TokenResponse(access_token=token, user=UserResponse.model_validate(user))
