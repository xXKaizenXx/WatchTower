from datetime import UTC, datetime
from uuid import uuid4

from app.core.security import hash_ping_token
from app.models.enums import Environment, EscalationLevel, ServiceStatus
from app.models.incident import Incident
from app.models.service import Service


def test_service_max_silence_seconds():
    service = Service(
        name="Nightly Sync",
        environment=Environment.PRODUCTION,
        heartbeat_interval=900,
        grace_period=60,
        ping_token_hash=hash_ping_token("test"),
    )
    assert service.max_silence_seconds == 960


def test_service_record_ping_sets_healthy():
    service = Service(
        name="Report Job",
        heartbeat_interval=86400,
        status=ServiceStatus.UNHEALTHY,
        ping_token_hash=hash_ping_token("test"),
    )
    ping_time = datetime(2026, 5, 17, 12, 0, tzinfo=UTC)
    service.record_ping(at=ping_time)

    assert service.last_ping_at == ping_time
    assert service.status == ServiceStatus.HEALTHY


def test_service_record_ping_respects_paused():
    service = Service(
        name="Maintenance Window",
        heartbeat_interval=3600,
        status=ServiceStatus.PAUSED,
        ping_token_hash=hash_ping_token("test"),
    )
    service.record_ping()
    assert service.status == ServiceStatus.PAUSED


def test_incident_open_and_resolve():
    incident = Incident(
        service_id=uuid4(),
        escalation_level=EscalationLevel.WEBHOOK,
    )
    assert incident.is_open

    resolved = datetime(2026, 5, 17, 14, 0, tzinfo=UTC)
    incident.resolve(at=resolved)

    assert not incident.is_open
    assert incident.resolved_at == resolved
