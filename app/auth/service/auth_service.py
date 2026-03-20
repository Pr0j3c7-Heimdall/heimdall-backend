from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from google.oauth2 import id_token  # type: ignore[attr-defined]
from google.auth.transport import requests as google_requests  # type: ignore[attr-defined]
from jose import jwt  # type: ignore[attr-defined]
from jose.exceptions import JWTError  # type: ignore[attr-defined]

from app.auth.exception import ProviderNotSupportedError
from app.auth.repository import (
    RefreshTokenRepositoryProtocol,
    TokenBlacklistRepository,
)
from app.user.model import User, UserStatus
from app.user.repository import UserRepository
from app.auth.schema import LoginRequest, LogoutRequest, RefreshRequest
from app.config import get_auth_settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간
REFRESH_TOKEN_EXPIRE_DAYS = 14


def create_access_token(user_id: int) -> str:
    settings = get_auth_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def _verify_google_token(id_token_str: str) -> dict | None:
    """구글 ID Token 검증, 성공 시 payload 반환"""
    settings = get_auth_settings()
    try:
        payload = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
        return payload
    except ValueError:
        return None


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepositoryProtocol,
        token_blacklist_repository: TokenBlacklistRepository,
    ):
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository
        self.token_blacklist_repository = token_blacklist_repository

    async def login(self, request: LoginRequest) -> tuple[str, str, bool] | None:
        """
        구글 로그인 (겸 가입)
        Returns: (access_token, refresh_token, is_new_user) or None (인증 실패)
        """
        if request.provider != "google":
            raise ProviderNotSupportedError("현재 google만 지원합니다")

        payload = _verify_google_token(request.id_token)
        if not payload:
            return None

        sub = payload.get("sub")
        email = payload.get("email", "")
        name = payload.get("name", email.split("@")[0] if email else "User")

        if not sub:
            return None

        user = await self.user_repository.find_by_provider_sub(request.provider, sub)
        is_new_user = False

        if user and user.status == UserStatus.DELETED:
            await self.user_repository.restore(user.id)

        if not user:
            user = await self.user_repository.create(
                email=email,
                name=name,
                provider=request.provider,
                provider_sub=sub,
            )
            is_new_user = True

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        await self.refresh_token_repository.create(
            user_id=user.id,
            token=refresh_token,
            expires_at=expires_at,
        )

        return access_token, refresh_token, is_new_user

    async def refresh(self, request: RefreshRequest) -> tuple[str, str] | None:
        """
        액세스 토큰 재발급 (리프레시 토큰 검증 + 토큰 로테이션)
        Returns: (access_token, refresh_token) or None (실패)
        """
        rt_entity = await self.refresh_token_repository.find_valid_by_token(
            request.refresh_token
        )
        if not rt_entity:
            return None

        # 토큰 로테이션: 기존 삭제, 새로 발급
        await self.refresh_token_repository.delete_by_token(request.refresh_token)

        access_token = create_access_token(rt_entity.user_id)
        new_refresh_token = create_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        await self.refresh_token_repository.create(
            user_id=rt_entity.user_id,
            token=new_refresh_token,
            expires_at=expires_at,
        )

        return access_token, new_refresh_token

    async def logout(self, request: LogoutRequest, access_token: str) -> None:
        """
        로그아웃: refresh token 삭제 + access token 블랙리스트 등록 (Redis)
        """
        await self.refresh_token_repository.delete_by_token(request.refresh_token)

        try:
            payload = jwt.decode(
                access_token,
                get_auth_settings().JWT_SECRET_KEY,
                algorithms=[ALGORITHM],
            )
            exp = payload.get("exp")
            if exp:
                expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
                await self.token_blacklist_repository.add(access_token, expires_at)
        except JWTError:
            pass

    async def withdraw(self, user: User, access_token: str) -> None:
        """
        회원 탈퇴: refresh token 전체 삭제 + access token 블랙리스트 + user soft delete
        """
        if user.status == UserStatus.DELETED:
            return  # idempotent: 이미 탈퇴한 경우 무시

        await self.refresh_token_repository.delete_by_user_id(user.id)

        try:
            payload = jwt.decode(
                access_token,
                get_auth_settings().JWT_SECRET_KEY,
                algorithms=[ALGORITHM],
            )
            exp = payload.get("exp")
            if exp:
                expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
                await self.token_blacklist_repository.add(access_token, expires_at)
        except JWTError:
            pass

        await self.user_repository.withdraw(user.id)
