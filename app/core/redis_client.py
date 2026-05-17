from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from app.core.config import get_settings

_settings = get_settings()
_async_redis: AsyncRedis | None = None


def get_sync_redis() -> Redis:
    return Redis.from_url(_settings.redis_url, decode_responses=True)


async def init_async_redis() -> AsyncRedis:
    global _async_redis
    if _async_redis is None:
        _async_redis = AsyncRedis.from_url(_settings.redis_url, decode_responses=True)
    return _async_redis


async def close_async_redis() -> None:
    global _async_redis
    if _async_redis is not None:
        await _async_redis.aclose()
        _async_redis = None


async def get_async_redis() -> AsyncRedis:
    return await init_async_redis()


def heartbeat_key(service_id: str) -> str:
    return f"{_settings.heartbeat_key_prefix}{service_id}"


def parse_service_id_from_expired_key(key: str) -> str | None:
    prefix = _settings.heartbeat_key_prefix
    if not key.startswith(prefix):
        return None
    return key[len(prefix) :]
