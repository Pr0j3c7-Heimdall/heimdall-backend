import hashlib
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.model import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    async def create(self, user_id: int, token: str, expires_at: datetime) -> RefreshToken:
        token_hash = self._hash_token(token)
        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(refresh_token)
        await self.db.flush()
        await self.db.refresh(refresh_token)
        return refresh_token

    async def find_valid_by_token(self, token: str) -> RefreshToken | None:
        token_hash = self._hash_token(token)
        result = await self.db.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .where(RefreshToken.expires_at > datetime.now(timezone.utc))
        )
        return result.scalar_one_or_none()

    async def delete_by_token(self, token: str) -> None:
        token_hash = self._hash_token(token)
        await self.db.execute(delete(RefreshToken).where(RefreshToken.token_hash == token_hash))
