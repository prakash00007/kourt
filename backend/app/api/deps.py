from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, hash_password
from app.models.user import User
from app.services.container import ServiceContainer


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_container(request: Request) -> ServiceContainer:
    return request.app.state.container


async def get_db_session(container: ServiceContainer = Depends(get_container)):
    async with container.session_factory() as session:
        yield session


def _can_use_demo_mode(container: ServiceContainer) -> bool:
    return container.settings.allow_anonymous_demo and container.settings.app_env != "production"


async def _get_or_create_demo_user(container: ServiceContainer, session: AsyncSession) -> User:
    demo_email = container.settings.demo_user_email
    user = await session.scalar(select(User).where(User.email == demo_email))
    if user is not None:
        return user

    user = User(
        email=demo_email,
        hashed_password=hash_password("local-demo-access"),
        tier="demo",
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing_user = await session.scalar(select(User).where(User.email == demo_email))
        if existing_user is not None:
            return existing_user
        raise

    await session.refresh(user)
    return user


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    container: ServiceContainer = Depends(get_container),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if token:
        try:
            payload = decode_access_token(container.settings, token)
            user_id = UUID(payload["sub"])
            user = await session.scalar(select(User).where(User.id == user_id))
            if user is not None:
                return user
        except Exception:
            pass

    if _can_use_demo_mode(container):
        return await _get_or_create_demo_user(container, session)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def enforce_draft_quota(
    current_user: User = Depends(get_current_user),
    container: ServiceContainer = Depends(get_container),
) -> User:
    if _can_use_demo_mode(container) and current_user.email == container.settings.demo_user_email:
        return current_user

    allowed, current = await container.usage_metering_service.check_and_increment_draft_usage(current_user.id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily draft limit exceeded. Allowed drafts per day: {container.settings.draft_daily_limit}. Current count: {current}.",
        )
    return current_user
