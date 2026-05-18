from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_API_KEY_VALUES = frozenset(
    {
        "dev-api-key-change-in-production",
        "change-me-in-production",
        "changeme",
        "test-api-key",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "WatchTower"
    debug: bool = False
    environment: str = Field(default="development", alias="ENVIRONMENT")
    api_key: str = Field(default="dev-api-key-change-in-production", alias="WATCHTOWER_API_KEY")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    trusted_hosts: str = Field(default="*", alias="TRUSTED_HOSTS")
    enable_docs: bool | None = Field(default=None, alias="ENABLE_DOCS")
    port: int = Field(default=8000, alias="PORT")

    database_url: str = Field(
        default="postgresql+asyncpg://watchtower:watchtower@localhost:5432/watchtower",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg2://watchtower:watchtower@localhost:5432/watchtower",
        alias="DATABASE_URL_SYNC",
    )
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        alias="CELERY_RESULT_BACKEND",
    )

    heartbeat_key_prefix: str = "watchtower:heartbeat:"
    ping_rate_limit: str = Field(default="120/minute", alias="PING_RATE_LIMIT")

    slack_webhook_url: str | None = Field(default=None, alias="SLACK_WEBHOOK_URL")
    discord_webhook_url: str | None = Field(default=None, alias="DISCORD_WEBHOOK_URL")

    twilio_account_sid: str | None = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str | None = Field(default=None, alias="TWILIO_FROM_NUMBER")
    twilio_alert_number: str | None = Field(default=None, alias="TWILIO_ALERT_NUMBER")

    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return value.strip().lower()

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_test(self) -> bool:
        return self.environment == "test"

    @property
    def docs_enabled(self) -> bool:
        if self.enable_docs is not None:
            return self.enable_docs
        return not self.is_production

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        if self.trusted_hosts == "*":
            return ["*"]
        return [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if not self.is_production:
            return self
        if self.api_key in INSECURE_API_KEY_VALUES or len(self.api_key) < 32:
            msg = (
                "WATCHTOWER_API_KEY must be a unique secret (32+ chars) in production. "
                'Generate: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
            raise ValueError(msg)
        if self.cors_origins.strip() == "*":
            raise ValueError(
                "CORS_ORIGINS must not be '*' in production. Set your frontend domain(s)."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
