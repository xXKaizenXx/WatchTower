from fastapi import APIRouter, status
from sqlalchemy import text

from app.api.deps import RedisDep, SessionDep

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def readiness(session: SessionDep, redis: RedisDep) -> dict[str, str]:
    from fastapi import HTTPException

    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable"
        ) from None
    if not await redis.ping():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis unavailable"
        )
    return {"status": "ready", "database": "up", "redis": "up"}
