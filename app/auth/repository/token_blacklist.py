"""토큰 블랙리스트 저장소 (Redis 구현체 포함)"""

import hashlib
from datetime import datetime, timezone

from redis.asyncio import Redis
from typing import Protocol


class TokenBlacklistRepository(Protocol):
    """access token 블랙리스트 저장소 프로토콜"""

    async def add(self, token: str, expires_at: datetime) -> None:
        """블랙리스트에 토큰 추가 (만료 시점까지 보관)"""
        ...

    async def contains(self, token: str) -> bool:
        """블랙리스트에 토큰 존재 여부"""
        ...


class NullTokenBlacklistRepository:
    """no-op 구현 (테스트 등용)"""

    async def add(self, token: str, expires_at: datetime) -> None:
        pass

    async def contains(self, token: str) -> bool:
        return False


_BL_PREFIX = "bl:"


def _token_key(token: str) -> str:
    return f"{_BL_PREFIX}{hashlib.sha256(token.encode()).hexdigest()}"


class RedisTokenBlacklistRepository:
    """액세스 토큰 블랙리스트 Redis 저장 (TTL로 만료 처리)"""

    def __init__(self, redis: Redis):
        self._redis = redis

    async def add(self, token: str, expires_at: datetime) -> None:
        key = _token_key(token)
        expires_at_utc = (
            expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
        )
        expire_ts = int(expires_at_utc.timestamp())
        await self._redis.set(key, "1", exat=expire_ts)

    async def contains(self, token: str) -> bool:
        key = _token_key(token)
        return await self._redis.exists(key) > 0
