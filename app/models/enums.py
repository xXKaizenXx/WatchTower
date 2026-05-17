import enum


class ServiceStatus(enum.StrEnum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    PAUSED = "PAUSED"


class Environment(enum.StrEnum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"


class EscalationLevel(int, enum.Enum):
    """How far alerting progressed for an incident."""

    LOGGED = 0
    DATABASE = 1
    WEBHOOK = 2  # Slack / Discord
    SMS = 3  # Twilio — critical production
