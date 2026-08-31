"""Shared test fixtures.

The Redis client and the SQLAlchemy engine are both module-level singletons. That
is right for the app - one process, one event loop for its lifetime - but wrong
for tests: pytest-asyncio gives each test a fresh event loop, and a connection
pool created on a now-closed loop fails on its next use. Symptom, if you skip
this: tests pass and fail in strict alternation.

Disposing both after every test means each one gets connections bound to its own
loop.
"""

import pytest

from app.core.redis_client import close_redis, get_redis
from app.db.session import engine


@pytest.fixture(autouse=True)
async def _isolate_connection_pools():
    yield
    await close_redis()
    await engine.dispose()


@pytest.fixture
async def redis_available():
    """Skip when docker-compose isn't up, rather than failing noisily."""
    try:
        await get_redis().ping()
    except Exception:
        pytest.skip("Redis unavailable - run `docker compose up -d`")
    return True
