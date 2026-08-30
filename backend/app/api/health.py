"""Liveness + dependency health.

GET /health reports whether Postgres and Redis are reachable. It stays 200 even
when a dependency is down so the endpoint itself is always a usable signal;
`status` is "ok" only when both are up.
"""

from fastapi import APIRouter

from app.core.redis_client import get_redis
from app.db.session import AsyncSessionLocal
from sqlalchemy import text

router = APIRouter(tags=["health"])


async def _check_db() -> dict:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            ext = await session.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            )
            return {"reachable": True, "pgvector": ext.scalar() is not None}
    except Exception as exc:
        return {"reachable": False, "error": type(exc).__name__}


async def _check_redis() -> dict:
    try:
        pong = await get_redis().ping()
        return {"reachable": bool(pong)}
    except Exception as exc:
        return {"reachable": False, "error": type(exc).__name__}


@router.get("/health")
async def health() -> dict:
    db = await _check_db()
    cache = await _check_redis()
    healthy = db["reachable"] and cache["reachable"]
    return {
        "status": "ok" if healthy else "degraded",
        "database": db,
        "redis": cache,
    }
