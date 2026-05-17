from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status

from app.api.deps import RedisDep, SessionDep
from app.models.service import ServiceRead
from app.services.heartbeat import process_ping

router = APIRouter(prefix="/ping", tags=["ping"])


@router.post("/{service_id}", response_model=ServiceRead)
async def ping_service(
    service_id: UUID,
    session: SessionDep,
    redis: RedisDep,
    x_ping_token: str = Header(..., alias="X-Ping-Token"),
) -> ServiceRead:
    try:
        service = await process_ping(session, redis, service_id, x_ping_token)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service not found"
        ) from None
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return ServiceRead.model_validate(service)
