from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, incidents, ping, services
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import setup_logging
from app.core.redis_client import close_async_redis, init_async_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_async_redis()
    await init_db()
    yield
    await close_async_redis()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Production dead man's switch for distributed systems. "
            "External jobs POST heartbeats; Redis TTL expiry triggers tiered alerts."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(ping.router)
    app.include_router(services.router, prefix="/api/v1")
    app.include_router(incidents.router, prefix="/api/v1")

    return app


app = create_app()
