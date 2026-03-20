"""리프레시 토큰 저장소 (Protocol + Redis 구현)."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Protocol

from redis.asyncio import Redis

from app.auth.schema import RefreshTokenInfo

_RT_PREFIX = "rt:"
_RT_USER_PREFIX = "rt:user:"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _to_utc_ts(dt: datetime) -> int:
    """datetime을 UTC 기준 Unix timestamp로 변환."""
    if dt.tzinfo:
        return int(dt.timestamp())
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


class RefreshTokenRepositoryProtocol(Protocol):
    """리프레시 토큰 저장소 프로토콜."""

    async def create(
        self, user_id: int, token: str, expires_at: datetime
    ) -> None:
        ...

    async def find_valid_by_token(self, token: str) -> RefreshTokenInfo | None:
        ...

    async def delete_by_token(self, token: str) -> None:
        ...

    async def delete_by_user_id(self, user_id: int) -> None:
        ...


class RedisRefreshTokenRepository:
    """리프레시 토큰 Redis 저장소 (TTL로 만료 처리)."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def create(
        self, user_id: int, token: str, expires_at: datetime
    ) -> None:
        token_hash = _hash_token(token)
        key = f"{_RT_PREFIX}{token_hash}"
        user_set_key = f"{_RT_USER_PREFIX}{user_id}"
        expire_ts = _to_utc_ts(expires_at)

        pipe = self._redis.pipeline()
        pipe.set(key, str(user_id), exat=expire_ts)
        pipe.sadd(user_set_key, token_hash)
        await pipe.execute()

    async def find_valid_by_token(self, token: str) -> RefreshTokenInfo | None:
        token_hash = _hash_token(token)
        key = f"{_RT_PREFIX}{token_hash}"
        value = await self._redis.get(key)
        if value is None:
            return None
        return RefreshTokenInfo(user_id=int(value))

    async def delete_by_token(self, token: str) -> None:
        token_hash = _hash_token(token)
        key = f"{_RT_PREFIX}{token_hash}"
        value = await self._redis.get(key)
        if value is None:
            return
        user_id = int(value)
        user_set_key = f"{_RT_USER_PREFIX}{user_id}"
        pipe = self._redis.pipeline()
        pipe.delete(key)
        pipe.srem(user_set_key, token_hash)
        await pipe.execute()

    async def delete_by_user_id(self, user_id: int) -> None:
        user_set_key = f"{_RT_USER_PREFIX}{user_id}"
        hashes = await self._redis.smembers(user_set_key)
        if not hashes:
            return
        pipe = self._redis.pipeline()
        for token_hash in hashes:
            pipe.delete(f"{_RT_PREFIX}{token_hash}")
        pipe.delete(user_set_key)
        await pipe.execute()
