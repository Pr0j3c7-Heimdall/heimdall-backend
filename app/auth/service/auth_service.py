from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from google.oauth2 import id_token  # type: ignore[attr-defined]
from google.auth.transport import requests as google_requests  # type: ignore[attr-defined]
from jose import jwt  # type: ignore[attr-defined]

from app.auth.exception import ProviderNotSupportedError
from app.auth.model import User
from app.auth.repository import RefreshTokenRepository, UserRepository
from app.auth.schema import LoginRequest
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
        refresh_token_repository: RefreshTokenRepository,
    ):
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository

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
