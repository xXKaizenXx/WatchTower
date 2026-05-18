import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_production_rejects_weak_api_key(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("WATCHTOWER_API_KEY", "change-me-in-production")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    with pytest.raises(ValidationError, match="WATCHTOWER_API_KEY"):
        Settings()


def test_production_rejects_wildcard_cors(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("WATCHTOWER_API_KEY", "a" * 48)
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings()


def test_production_accepts_valid_config(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("WATCHTOWER_API_KEY", "x" * 48)
    monkeypatch.setenv("CORS_ORIGINS", "https://watchtower.example.com")
    settings = Settings()
    assert settings.is_production
    assert settings.docs_enabled is False
