from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "WatchTower"
    debug: bool = False
    environment: str = "development"
    api_key: str = Field(default="dev-api-key-change-in-production", alias="WATCHTOWER_API_KEY")
    cors_origins: str = "*"

    database_url: str = Field(
        default="postgresql+asyncpg://watchtower:watchtower@localhost:5432/watchtower",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg2://watchtower:watchtower@localhost:5432/watchtower",
        alias="DATABASE_URL_SYNC",
    )

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        alias="CELERY_RESULT_BACKEND",
    )

    heartbeat_key_prefix: str = "watchtower:heartbeat:"

    slack_webhook_url: str | None = Field(default=None, alias="SLACK_WEBHOOK_URL")
    discord_webhook_url: str | None = Field(default=None, alias="DISCORD_WEBHOOK_URL")

    twilio_account_sid: str | None = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str | None = Field(default=None, alias="TWILIO_FROM_NUMBER")
    twilio_alert_number: str | None = Field(default=None, alias="TWILIO_ALERT_NUMBER")

    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
