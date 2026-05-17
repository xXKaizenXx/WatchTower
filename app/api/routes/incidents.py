from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlmodel import col

from app.api.deps import SessionDep, require_api_key
from app.models.incident import Incident, IncidentRead

router = APIRouter(
    prefix="/incidents",
    tags=["incidents"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=list[IncidentRead])
async def list_incidents(
    session: SessionDep,
    open_only: bool = False,
    service_id: UUID | None = None,
) -> list[IncidentRead]:
    stmt = select(Incident).order_by(col(Incident.triggered_at).desc())
    if open_only:
        stmt = stmt.where(col(Incident.resolved_at).is_(None))
    if service_id:
        stmt = stmt.where(Incident.service_id == service_id)
    result = await session.execute(stmt)
    incidents = result.scalars().all()
    return [IncidentRead.model_validate(i) for i in incidents]


@router.get("/{incident_id}", response_model=IncidentRead)
async def get_incident(incident_id: UUID, session: SessionDep) -> IncidentRead:
    incident = await session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return IncidentRead.model_validate(incident)
