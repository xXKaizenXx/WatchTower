from uuid import UUID

import structlog

from app.core.sync_database import SyncSessionLocal
from app.services.incident_handler import handle_missed_heartbeat
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="watchtower.handle_missed_heartbeat", bind=True, max_retries=3)
def handle_missed_heartbeat_task(self, service_id: str) -> dict:
    try:
        sid = UUID(service_id)
    except ValueError:
        logger.error("invalid_service_id", service_id=service_id)
        return {"status": "invalid_id"}

    session = SyncSessionLocal()
    try:
        incident = handle_missed_heartbeat(session, sid)
        if incident is None:
            return {"status": "no_action"}
        return {"status": "incident_opened", "incident_id": str(incident.id)}
    except Exception as exc:
        session.rollback()
        logger.exception("handle_missed_heartbeat_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
    finally:
        session.close()
