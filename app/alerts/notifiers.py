import httpx
import structlog
from twilio.rest import Client as TwilioClient

from app.alerts.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.core.config import get_settings
from app.models.enums import EscalationLevel
from app.models.service import Service

logger = structlog.get_logger(__name__)
settings = get_settings()

_webhook_breaker = CircuitBreaker(
    "webhook",
    settings.circuit_breaker_failure_threshold,
    settings.circuit_breaker_recovery_timeout,
)
_sms_breaker = CircuitBreaker(
    "sms",
    settings.circuit_breaker_failure_threshold,
    settings.circuit_breaker_recovery_timeout,
)


def _post_webhook(url: str, payload: dict) -> None:
    with httpx.Client(timeout=10.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()


def _slack_payload(service: Service, incident_id: str, message: str) -> dict:
    return {
        "text": f":rotating_light: *WatchTower Alert* — {service.name}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Service:* `{service.name}`\n"
                        f"*Environment:* `{service.environment.value}`\n"
                        f"*Incident:* `{incident_id}`\n"
                        f"*Detail:* {message}"
                    ),
                },
            }
        ],
    }


def _discord_payload(service: Service, incident_id: str, message: str) -> dict:
    return {
        "embeds": [
            {
                "title": "WatchTower Alert",
                "description": message,
                "color": 15158332,
                "fields": [
                    {"name": "Service", "value": service.name, "inline": True},
                    {"name": "Environment", "value": service.environment.value, "inline": True},
                    {"name": "Incident ID", "value": incident_id, "inline": False},
                ],
            }
        ]
    }


def notify_webhook(service: Service, incident_id: str, message: str) -> bool:
    url = service.webhook_url or settings.slack_webhook_url or settings.discord_webhook_url
    if not url:
        logger.info("webhook_skipped_no_url", service_id=str(service.id))
        return False

    if "discord.com" in url:
        payload = _discord_payload(service, incident_id, message)
    else:
        payload = _slack_payload(service, incident_id, message)

    try:
        _webhook_breaker.call(_post_webhook, url, payload)
        logger.info("webhook_sent", service_id=str(service.id), incident_id=incident_id)
        return True
    except CircuitOpenError:
        logger.error("webhook_circuit_open", service_id=str(service.id))
        return False
    except Exception as exc:
        logger.exception("webhook_failed", error=str(exc))
        return False


def notify_sms(service: Service, incident_id: str, message: str) -> bool:
    if not service.enable_sms_alerts:
        return False

    to_number = service.sms_phone or settings.twilio_alert_number
    if not to_number:
        logger.info("sms_skipped_no_number", service_id=str(service.id))
        return False

    if not all(
        [settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_from_number]
    ):
        logger.warning("sms_skipped_twilio_not_configured")
        return False

    body = (
        f"WatchTower CRITICAL: {service.name} ({service.environment.value}) "
        f"missed heartbeat. Incident {incident_id[:8]}. {message}"
    )

    def _send():
        client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
        client.messages.create(
            body=body[:1600],
            from_=settings.twilio_from_number,
            to=to_number,
        )

    try:
        _sms_breaker.call(_send)
        logger.info("sms_sent", service_id=str(service.id), incident_id=incident_id)
        return True
    except CircuitOpenError:
        logger.error("sms_circuit_open", service_id=str(service.id))
        return False
    except Exception as exc:
        logger.exception("sms_failed", error=str(exc))
        return False


def run_escalation_pipeline(service: Service, incident_id: str, message: str) -> EscalationLevel:
    """Tiered escalation: logged (DB) -> webhook -> SMS for production-critical."""
    level = EscalationLevel.DATABASE
    logger.warning(
        "incident_escalation_started",
        service_id=str(service.id),
        incident_id=incident_id,
        environment=service.environment.value,
    )

    if notify_webhook(service, incident_id, message):
        level = EscalationLevel.WEBHOOK

    if service.environment.value == "production" and service.enable_sms_alerts:
        if notify_sms(service, incident_id, message):
            level = EscalationLevel.SMS

    return level
