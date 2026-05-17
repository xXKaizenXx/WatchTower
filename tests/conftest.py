import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("WATCHTOWER_API_KEY", "test-api-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///:memory:")

from app.core.config import get_settings
from app.core.database import get_session
from app.core.redis_client import get_async_redis
from app.main import create_app
from app.models import Incident, Service  # noqa: F401

get_settings.cache_clear()


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest_asyncio.fixture
async def fake_redis() -> FakeRedis:
    return FakeRedis(decode_responses=True)


@pytest_asyncio.fixture
async def client(session: AsyncSession, fake_redis: FakeRedis) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    async def override_redis() -> FakeRedis:
        return fake_redis

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_async_redis] = override_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def api_headers() -> dict[str, str]:
    return {"X-API-Key": "test-api-key"}
