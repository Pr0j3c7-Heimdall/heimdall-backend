"""Auth 도메인 의존성 주입"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception import UnauthorizedException
from app.config import get_auth_settings

from app.user.model import User, UserStatus
from app.auth.repository import (
    NullTokenBlacklistRepository,
    RefreshTokenRepository,
    TokenBlacklistRepository,
)
from app.auth.service import AuthService
from app.database import get_db
from app.user.dependencies import get_user_repository
from app.user.repository import UserRepository


def get_refresh_token_repository(db: AsyncSession = Depends(get_db)) -> RefreshTokenRepository:
    return RefreshTokenRepository(db)


def get_token_blacklist_repository() -> TokenBlacklistRepository:
    return NullTokenBlacklistRepository()


_ALGORITHM = "HS256"
_http_bearer = HTTPBearer(auto_error=True)


async def get_current_user_credentials(
    credentials: HTTPAuthorizationCredentials = Depends(_http_bearer),
    user_repo: UserRepository = Depends(get_user_repository),
    token_blacklist_repo: TokenBlacklistRepository = Depends(get_token_blacklist_repository),
) -> tuple[User, str]:
    """JWT 검증 + 블랙리스트 + user status 확인 후 (User, access_token) 반환"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            get_auth_settings().JWT_SECRET_KEY,
            algorithms=[_ALGORITHM],
        )
        sub = payload.get("sub")
        if not sub:
            raise UnauthorizedException("유효하지 않은 토큰입니다")
        user_id = int(sub)
    except (JWTError, ValueError) as e:
        raise UnauthorizedException("유효하지 않거나 만료된 토큰입니다") from e

    if await token_blacklist_repo.contains(credentials.credentials):
        raise UnauthorizedException("로그아웃된 토큰입니다")

    user = await user_repo.find_by_id(user_id)
    if not user or user.status == UserStatus.DELETED:
        raise UnauthorizedException("탈퇴한 계정입니다")

    return user, credentials.credentials


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    refresh_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
    token_blacklist_repo: TokenBlacklistRepository = Depends(get_token_blacklist_repository),
) -> AuthService:
    return AuthService(user_repo, refresh_repo, token_blacklist_repo)
