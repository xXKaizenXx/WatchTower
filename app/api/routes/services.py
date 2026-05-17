from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import RedisDep, SessionDep, require_api_key
from app.models.service import ServiceCreate, ServiceRead, ServiceReadWithToken, ServiceUpdate
from app.services import service_manager

router = APIRouter(
    prefix="/services",
    tags=["services"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=list[ServiceRead])
async def list_services(session: SessionDep) -> list[ServiceRead]:
    services = await service_manager.list_services(session)
    return [ServiceRead.model_validate(s) for s in services]


@router.post("", response_model=ServiceReadWithToken, status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: ServiceCreate,
    session: SessionDep,
    redis: RedisDep,
) -> ServiceReadWithToken:
    service, token = await service_manager.create_service(session, redis, payload)
    data = ServiceRead.model_validate(service).model_dump()
    return ServiceReadWithToken(**data, ping_token=token)


@router.get("/{service_id}", response_model=ServiceRead)
async def get_service(service_id: UUID, session: SessionDep) -> ServiceRead:
    from app.services.heartbeat import get_service as fetch_service

    svc = await fetch_service(session, service_id)
    if not svc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return ServiceRead.model_validate(svc)


@router.patch("/{service_id}", response_model=ServiceRead)
async def update_service(
    service_id: UUID,
    payload: ServiceUpdate,
    session: SessionDep,
    redis: RedisDep,
) -> ServiceRead:
    service = await service_manager.update_service(session, redis, service_id, payload)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return ServiceRead.model_validate(service)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: UUID,
    session: SessionDep,
    redis: RedisDep,
) -> None:
    deleted = await service_manager.delete_service(session, redis, service_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")


@router.post("/{service_id}/rotate-token", response_model=ServiceReadWithToken)
async def rotate_token(
    service_id: UUID,
    session: SessionDep,
) -> ServiceReadWithToken:
    result = await service_manager.rotate_ping_token(session, service_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    token, service = result
    data = ServiceRead.model_validate(service).model_dump()
    return ServiceReadWithToken(**data, ping_token=token)
