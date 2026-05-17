"""
Redis keyspace expiry listener — fires Celery tasks when heartbeat TTLs expire.

Requires Redis: notify-keyspace-events Ex (set in docker-compose).
"""

import signal
import sys

import structlog
from redis import Redis

from app.core.logging import setup_logging
from app.core.redis_client import get_sync_redis, parse_service_id_from_expired_key
from app.workers.tasks import handle_missed_heartbeat_task

logger = structlog.get_logger(__name__)
_running = True


def _configure_redis_notifications(redis: Redis) -> None:
    try:
        current = redis.config_get("notify-keyspace-events")
        events = current.get("notify-keyspace-events", "") if current else ""
        if "E" not in events or "x" not in events:
            redis.config_set("notify-keyspace-events", "Ex")
            logger.info("redis_keyspace_notifications_enabled")
    except Exception as exc:
        logger.warning("redis_config_set_failed", error=str(exc))


def _shutdown(*_args) -> None:
    global _running
    _running = False


def run_listener() -> None:
    setup_logging()
    redis = get_sync_redis()
    _configure_redis_notifications(redis)

    pubsub = redis.pubsub()
    pubsub.psubscribe("__keyevent@0__:expired")

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("redis_expiry_listener_started")

    for message in pubsub.listen():
        if not _running:
            break
        if message["type"] != "pmessage":
            continue
        key = message["data"]
        if isinstance(key, bytes):
            key = key.decode()
        service_id = parse_service_id_from_expired_key(key)
        if not service_id:
            continue
        logger.info("heartbeat_ttl_expired", service_id=service_id, key=key)
        handle_missed_heartbeat_task.delay(service_id)

    pubsub.close()
    redis.close()
    logger.info("redis_expiry_listener_stopped")


def main() -> None:
    try:
        run_listener()
    except KeyboardInterrupt:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
