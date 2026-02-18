from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.user.model import User, UserStatus


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_provider_sub(self, provider: str, provider_sub: str) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.provider == provider,
                User.provider_sub == provider_sub,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, email: str, name: str, provider: str, provider_sub: str) -> User:
        user = User(
            email=email,
            name=name,
            provider=provider,
            provider_sub=provider_sub,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def find_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def withdraw(self, user_id: int) -> None:
        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(status=UserStatus.DELETED, deleted_at=now)
        )

    async def restore(self, user_id: int) -> None:
        """탈퇴한 계정 복구 (재가입)"""
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(status=UserStatus.ACTIVE, deleted_at=None)
        )
