from datetime import UTC, datetime
from uuid import UUID

import structlog
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.core.redis_client import heartbeat_key
from app.core.security import verify_ping_token
from app.models.enums import ServiceStatus
from app.models.incident import Incident
from app.models.service import Service

logger = structlog.get_logger(__name__)


async def get_service(session: AsyncSession, service_id: UUID) -> Service | None:
    result = await session.execute(select(Service).where(Service.id == service_id))
    return result.scalar_one_or_none()


async def get_open_incident(session: AsyncSession, service_id: UUID) -> Incident | None:
    result = await session.execute(
        select(Incident).where(
            Incident.service_id == service_id,
            col(Incident.resolved_at).is_(None),
        )
    )
    return result.scalar_one_or_none()


async def refresh_redis_ttl(redis: Redis, service: Service) -> None:
    ttl = service.max_silence_seconds
    key = heartbeat_key(str(service.id))
    await redis.set(key, "1", ex=ttl)
    logger.debug("redis_ttl_refreshed", service_id=str(service.id), ttl=ttl)


async def process_ping(
    session: AsyncSession,
    redis: Redis,
    service_id: UUID,
    ping_token: str,
) -> Service:
    service = await get_service(session, service_id)
    if service is None:
        raise LookupError("Service not found")
    if service.status == ServiceStatus.PAUSED:
        raise PermissionError("Service is paused")
    if not verify_ping_token(ping_token, service.ping_token_hash):
        raise PermissionError("Invalid ping token")

    service.record_ping()
    session.add(service)

    open_incident = await get_open_incident(session, service_id)
    if open_incident:
        open_incident.resolve()
        session.add(open_incident)
        logger.info(
            "incident_auto_resolved",
            service_id=str(service_id),
            incident_id=str(open_incident.id),
        )

    await session.commit()
    await session.refresh(service)
    await refresh_redis_ttl(redis, service)
    return service


def is_still_overdue(service: Service, now: datetime | None = None) -> bool:
    """Re-check DB before alerting — ping may have landed after Redis expiry fired."""
    if service.last_ping_at is None:
        return True
    if service.status == ServiceStatus.PAUSED:
        return False
    now = now or datetime.now(UTC)
    last = service.last_ping_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    elapsed = (now - last).total_seconds()
    return elapsed > service.max_silence_seconds
