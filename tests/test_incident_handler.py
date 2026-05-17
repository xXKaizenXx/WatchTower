from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlmodel import SQLModel

from app.core.security import hash_ping_token
from app.models.enums import Environment, EscalationLevel, ServiceStatus
from app.models.incident import Incident  # noqa: F401
from app.models.service import Service
from app.services.incident_handler import handle_missed_heartbeat


@pytest.fixture
def sync_session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    yield session
    session.close()


def test_handle_missed_heartbeat_opens_incident(sync_session: Session):
    service = Service(
        name="Stale Job",
        environment=Environment.PRODUCTION,
        heartbeat_interval=60,
        grace_period=0,
        status=ServiceStatus.HEALTHY,
        last_ping_at=datetime.now(UTC) - timedelta(seconds=120),
        ping_token_hash=hash_ping_token("x"),
    )
    sync_session.add(service)
    sync_session.commit()
    sync_session.refresh(service)

    incident = handle_missed_heartbeat(sync_session, service.id)
    assert incident is not None
    assert incident.escalation_level >= EscalationLevel.DATABASE
    sync_session.refresh(service)
    assert service.status == ServiceStatus.UNHEALTHY


def test_handle_missed_heartbeat_ignores_recent_ping(sync_session: Session):
    service = Service(
        name="Fresh Job",
        environment=Environment.PRODUCTION,
        heartbeat_interval=60,
        grace_period=30,
        status=ServiceStatus.HEALTHY,
        last_ping_at=datetime.now(UTC),
        ping_token_hash=hash_ping_token("x"),
    )
    sync_session.add(service)
    sync_session.commit()
    sync_session.refresh(service)

    incident = handle_missed_heartbeat(sync_session, service.id)
    assert incident is None
