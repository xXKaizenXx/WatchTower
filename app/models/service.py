from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.models.base import TimestampMixin, utc_now
from app.models.enums import Environment, ServiceStatus

if TYPE_CHECKING:
    from app.models.incident import Incident


class ServiceBase(SQLModel):
    name: str = Field(max_length=255, index=True)
    environment: Environment = Field(
        default=Environment.PRODUCTION,
        sa_column_kwargs={"index": True},
    )
    heartbeat_interval: int = Field(
        ge=1,
        description="Expected seconds between successful check-ins.",
    )
    grace_period: int = Field(
        default=0,
        ge=0,
        description="Extra seconds after interval before alerting.",
    )
    status: ServiceStatus = Field(
        default=ServiceStatus.HEALTHY,
        sa_column_kwargs={"index": True},
    )
    last_ping_at: datetime | None = Field(default=None, index=True)
    webhook_url: str | None = Field(default=None, max_length=2048)
    sms_phone: str | None = Field(default=None, max_length=32)
    enable_sms_alerts: bool = Field(default=False)


class Service(ServiceBase, TimestampMixin, table=True):
    __tablename__ = "services"
    __table_args__ = (
        UniqueConstraint("name", "environment", name="uq_service_name_environment"),
        Index("ix_services_environment_status", "environment", "status"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    ping_token_hash: str = Field(max_length=64)
    incidents: list["Incident"] = Relationship(back_populates="service")

    @property
    def max_silence_seconds(self) -> int:
        """Total allowed silence before the watchdog opens an incident."""
        return self.heartbeat_interval + self.grace_period

    def record_ping(self, at: datetime | None = None) -> None:
        self.last_ping_at = at or utc_now()
        if self.status != ServiceStatus.PAUSED:
            self.status = ServiceStatus.HEALTHY


class ServiceCreate(ServiceBase):
    pass


class ServiceRead(ServiceBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class ServiceReadWithToken(ServiceRead):
    ping_token: str


class ServiceUpdate(SQLModel):
    name: str | None = None
    environment: Environment | None = None
    heartbeat_interval: int | None = Field(default=None, ge=1)
    grace_period: int | None = Field(default=None, ge=0)
    status: ServiceStatus | None = None
    webhook_url: str | None = None
    sms_phone: str | None = None
    enable_sms_alerts: bool | None = None
