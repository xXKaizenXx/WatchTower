from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.redis_client import heartbeat_key
from app.core.security import generate_ping_token, hash_ping_token
from app.models.enums import ServiceStatus
from app.models.service import Service, ServiceCreate, ServiceUpdate
from app.services.heartbeat import refresh_redis_ttl


async def create_service(
    session: AsyncSession,
    redis: Redis,
    payload: ServiceCreate,
) -> tuple[Service, str]:
    plain_token = generate_ping_token()
    service = Service(
        **payload.model_dump(),
        ping_token_hash=hash_ping_token(plain_token),
    )
    session.add(service)
    await session.commit()
    await session.refresh(service)
    if service.status != ServiceStatus.PAUSED:
        await refresh_redis_ttl(redis, service)
    return service, plain_token


async def update_service(
    session: AsyncSession,
    redis: Redis,
    service_id: UUID,
    payload: ServiceUpdate,
) -> Service | None:
    service = await session.get(Service, service_id)
    if not service:
        return None
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(service, key, value)
    session.add(service)
    await session.commit()
    await session.refresh(service)
    if service.status != ServiceStatus.PAUSED:
        await refresh_redis_ttl(redis, service)
    elif service.status == ServiceStatus.PAUSED:
        await redis.delete(heartbeat_key(str(service.id)))
    return service


async def delete_service(session: AsyncSession, redis: Redis, service_id: UUID) -> bool:
    service = await session.get(Service, service_id)
    if not service:
        return False
    await redis.delete(heartbeat_key(str(service_id)))
    await session.delete(service)
    await session.commit()
    return True


async def list_services(session: AsyncSession) -> list[Service]:
    result = await session.execute(select(Service).order_by(Service.name))
    return list(result.scalars().all())


async def rotate_ping_token(session: AsyncSession, service_id: UUID) -> tuple[str, Service] | None:
    service = await session.get(Service, service_id)
    if not service:
        return None
    plain = generate_ping_token()
    service.ping_token_hash = hash_ping_token(plain)
    session.add(service)
    await session.commit()
    await session.refresh(service)
    return plain, service
