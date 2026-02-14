"""Auth 도메인 의존성 주입"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.repository import NullTokenBlacklistRepository, RefreshTokenRepository, UserRepository
from app.auth.service import AuthService
from app.database import get_db


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_refresh_token_repository(db: AsyncSession = Depends(get_db)) -> RefreshTokenRepository:
    return RefreshTokenRepository(db)


def get_token_blacklist_repository() -> NullTokenBlacklistRepository:
    return NullTokenBlacklistRepository()


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    refresh_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
    token_blacklist_repo: NullTokenBlacklistRepository = Depends(get_token_blacklist_repository),
) -> AuthService:
    return AuthService(user_repo, refresh_repo, token_blacklist_repo)
