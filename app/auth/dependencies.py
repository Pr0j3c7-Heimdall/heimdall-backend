"""Auth 도메인 의존성 주입"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception import UnauthorizedException
from app.config import get_auth_settings

from app.auth.repository import (
    NullTokenBlacklistRepository,
    RefreshTokenRepository,
    TokenBlacklistRepository,
    UserRepository,
)
from app.auth.service import AuthService
from app.database import get_db


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_refresh_token_repository(db: AsyncSession = Depends(get_db)) -> RefreshTokenRepository:
    return RefreshTokenRepository(db)


def get_token_blacklist_repository() -> TokenBlacklistRepository:
    return NullTokenBlacklistRepository()


_ALGORITHM = "HS256"
_http_bearer = HTTPBearer(auto_error=True)


def get_current_user_credentials(
    credentials: HTTPAuthorizationCredentials = Depends(_http_bearer),
) -> tuple[int, str]:
    """JWT 검증 후 (user_id, access_token) 반환. 인증 실패 시 401"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            get_auth_settings().JWT_SECRET_KEY,
            algorithms=[_ALGORITHM],
        )
        sub = payload.get("sub")
        if not sub:
            raise UnauthorizedException("유효하지 않은 토큰입니다")
        return int(sub), credentials.credentials
    except (JWTError, ValueError) as e:
        raise UnauthorizedException("유효하지 않거나 만료된 토큰입니다") from e


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    refresh_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
    token_blacklist_repo: TokenBlacklistRepository = Depends(get_token_blacklist_repository),
) -> AuthService:
    return AuthService(user_repo, refresh_repo, token_blacklist_repo)
