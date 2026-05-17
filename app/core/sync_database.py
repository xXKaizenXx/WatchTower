from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models import Incident, Service  # noqa: F401

settings = get_settings()

sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)


def get_sync_session() -> Generator[Session, None, None]:
    session = SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()
