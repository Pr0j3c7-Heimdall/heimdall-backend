from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone

from google.oauth2 import id_token  # type: ignore[attr-defined]
from google.auth.transport import requests as google_requests  # type: ignore[attr-defined]
from jose import jwt  # type: ignore[attr-defined]

from app.auth.model import User
from app.auth.repository import RefreshTokenRepository, UserRepository
from app.auth.schema import LoginRequest

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간
REFRESH_TOKEN_EXPIRE_DAYS = 14


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def _verify_google_token(id_token_str: str) -> dict | None:
    """구글 ID Token 검증, 성공 시 payload 반환"""
    try:
        payload = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
        return payload
    except Exception:
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
            return None

        payload = _verify_google_token(request.id_token)
        if not payload:
            return None

        sub = payload.get("sub")
        email = payload.get("email", "")
        name = payload.get("name", email.split("@")[0] if email else "User")

        if not sub:
            return None

        user = await self.user_repository.find_by_provider_sub("google", sub)
        is_new_user = False

        if not user:
            user = await self.user_repository.create(
                email=email,
                name=name,
                provider="google",
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
