"""토큰 블랙리스트 저장소 (추후 Redis 도입 시 교체)"""

from datetime import datetime
from typing import Protocol


class TokenBlacklistRepository(Protocol):
    """access token 블랙리스트 저장소 프로토콜 (Redis 도입 시 구현체 교체)"""

    async def add(self, token: str, expires_at: datetime) -> None:
        """블랙리스트에 토큰 추가 (만료 시점까지 보관)"""
        ...

    async def contains(self, token: str) -> bool:
        """블랙리스트에 토큰 존재 여부"""
        ...


class NullTokenBlacklistRepository:
    """현재: no-op. 추후 RedisTokenBlacklistRepository로 교체"""

    async def add(self, token: str, expires_at: datetime) -> None:
        pass

    async def contains(self, token: str) -> bool:
        return False
