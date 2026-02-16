"""Auth 도메인 의존성 주입"""

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.auth.repository import (
    NullTokenBlacklistRepository,
    RefreshTokenRepository,
    TokenBlacklistRepository,
    UserRepository,
)
from app.auth.service import AuthService
from app.database import get_db
from app.common.exception.base_exception import UnauthorizedException
from app.config import get_auth_settings

auth_settings = get_auth_settings()
security = HTTPBearer()

def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_refresh_token_repository(db: AsyncSession = Depends(get_db)) -> RefreshTokenRepository:
    return RefreshTokenRepository(db)


def get_token_blacklist_repository() -> TokenBlacklistRepository:
    return NullTokenBlacklistRepository()


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    refresh_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
    token_blacklist_repo: TokenBlacklistRepository = Depends(get_token_blacklist_repository),
) -> AuthService:
    return AuthService(user_repo, refresh_repo, token_blacklist_repo)

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    token = credentials.credentials
    credentials_exception = UnauthorizedException("인증 정보를 검증할 수 없습니다.")
    try:
        payload = jwt.decode(token, auth_settings.JWT_SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return int(user_id)