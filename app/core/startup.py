import structlog
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import engine
from app.core.redis_client import get_async_redis

logger = structlog.get_logger(__name__)


async def validate_runtime_dependencies(settings: Settings) -> None:
    """Fail fast if Postgres or Redis are unreachable at boot."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("startup_database_ok")

    redis = await get_async_redis()
    if not await redis.ping():
        raise RuntimeError("Redis ping failed")
    logger.info("startup_redis_ok")


def log_production_banner(settings: Settings) -> None:
    if not settings.is_production:
        return
    logger.info(
        "watchtower_production_mode",
        docs_enabled=settings.docs_enabled,
        cors_origins=settings.cors_origins,
        trusted_hosts=settings.trusted_hosts,
    )


async def run_startup_checks() -> None:
    settings = get_settings()
    if settings.is_test:
        return
    log_production_banner(settings)
    await validate_runtime_dependencies(settings)
