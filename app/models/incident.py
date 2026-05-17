from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Index
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TimestampMixin, utc_now
from app.models.enums import EscalationLevel

if TYPE_CHECKING:
    from app.models.service import Service


class IncidentBase(SQLModel):
    triggered_at: datetime = Field(
        default_factory=utc_now,
        index=True,
        description="When WatchTower detected a missed heartbeat window.",
    )
    resolved_at: datetime | None = Field(
        default=None,
        index=True,
        description="When the service checked in again; null while open.",
    )
    escalation_level: EscalationLevel = Field(
        default=EscalationLevel.LOGGED,
        description="Furthest tier reached: 0=log, 1=DB, 2=webhook, 3=SMS.",
    )


class Incident(IncidentBase, TimestampMixin, table=True):
    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incidents_service_open", "service_id", "resolved_at"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    service_id: UUID = Field(foreign_key="services.id", index=True, ondelete="CASCADE")
    service: "Service" = Relationship(back_populates="incidents")

    @property
    def is_open(self) -> bool:
        return self.resolved_at is None

    def resolve(self, at: datetime | None = None) -> None:
        self.resolved_at = at or utc_now()


class IncidentCreate(IncidentBase):
    service_id: UUID


class IncidentRead(IncidentBase):
    id: UUID
    service_id: UUID
    created_at: datetime
    updated_at: datetime
