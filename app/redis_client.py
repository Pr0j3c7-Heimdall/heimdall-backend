"""Redis 클라이언트 (lifespan에서 초기화/종료)"""

from redis.asyncio import Redis

_redis: Redis | None = None


def get_redis() -> Redis:
    """Redis 클라이언트 반환. lifespan에서 초기화된 후 사용."""
    if _redis is None:
        raise RuntimeError("Redis client not initialized. Check app lifespan.")
    return _redis


def get_redis_dep() -> Redis:
    """FastAPI Depends용 Redis 클라이언트 (get_redis 래퍼)"""
    return get_redis()


def set_redis(client: Redis) -> None:
    """lifespan에서 Redis 클라이언트 설정"""
    global _redis
    _redis = client


def clear_redis() -> None:
    """테스트 등에서 클라이언트 해제"""
    global _redis
    _redis = None
