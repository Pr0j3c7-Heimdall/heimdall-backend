from __future__ import annotations

from app.user.model import User
from app.user.repository import UserRepository


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def get_me(self, user_id: int) -> User | None:
        """마이페이지 회원정보 조회"""
        return await self.user_repository.find_by_id(user_id)
