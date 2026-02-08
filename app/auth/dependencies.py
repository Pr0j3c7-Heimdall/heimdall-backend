"""Auth 도메인 의존성 주입"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.repository import RefreshTokenRepository, UserRepository
from app.auth.service import AuthService
from app.database import get_db


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_refresh_token_repository(db: AsyncSession = Depends(get_db)) -> RefreshTokenRepository:
    return RefreshTokenRepository(db)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    refresh_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
) -> AuthService:
    return AuthService(user_repo, refresh_repo)
