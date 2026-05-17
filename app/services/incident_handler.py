from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlmodel import col

from app.alerts.notifiers import run_escalation_pipeline
from app.models.enums import EscalationLevel, ServiceStatus
from app.models.incident import Incident
from app.models.service import Service
from app.services.heartbeat import is_still_overdue

logger = structlog.get_logger(__name__)


def get_service_sync(session: Session, service_id: UUID) -> Service | None:
    return session.get(Service, service_id)


def get_open_incident_sync(session: Session, service_id: UUID) -> Incident | None:
    stmt = select(Incident).where(
        Incident.service_id == service_id,
        col(Incident.resolved_at).is_(None),
    )
    return session.execute(stmt).scalar_one_or_none()


def handle_missed_heartbeat(session: Session, service_id: UUID) -> Incident | None:
    service = get_service_sync(session, service_id)
    if service is None:
        logger.warning("expiry_unknown_service", service_id=str(service_id))
        return None

    if service.status == ServiceStatus.PAUSED:
        logger.info("expiry_ignored_paused", service_id=str(service_id))
        return None

    if not is_still_overdue(service):
        logger.info("expiry_false_positive", service_id=str(service_id))
        return None

    existing = get_open_incident_sync(session, service_id)
    if existing:
        logger.info("incident_already_open", incident_id=str(existing.id))
        return existing

    service.status = ServiceStatus.UNHEALTHY
    session.add(service)

    incident = Incident(service_id=service.id, escalation_level=EscalationLevel.LOGGED)
    session.add(incident)
    session.flush()

    message = (
        f"No heartbeat within {service.max_silence_seconds}s "
        f"(interval={service.heartbeat_interval}s, grace={service.grace_period}s)."
    )
    level = run_escalation_pipeline(service, str(incident.id), message)
    incident.escalation_level = level
    session.add(incident)
    session.commit()
    session.refresh(incident)

    logger.warning(
        "incident_opened",
        service_id=str(service_id),
        incident_id=str(incident.id),
        escalation_level=level.value,
    )
    return incident
