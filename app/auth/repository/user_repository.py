from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.model import User


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
