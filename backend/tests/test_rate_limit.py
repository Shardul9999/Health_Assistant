"""Sliding-window rate limiter (§8, §10).

Runs against the real Redis from docker-compose - the Lua script is the thing
under test, and a fake would not exercise it.
"""

import asyncio
import time
import uuid

import pytest

from app.config import settings
from app.core.rate_limit import check, key_for, reset
from app.core.redis_client import get_redis


@pytest.fixture
async def user_id(redis_available):
    uid = f"test_user_{uuid.uuid4().hex[:12]}"
    await reset(uid)
    yield uid
    await reset(uid)


async def test_requests_under_the_limit_are_allowed(user_id):
    for i in range(settings.rate_limit_requests):
        result = await check(user_id)
        assert result.allowed, f"request {i + 1} should be allowed"
        assert result.count == i + 1


async def test_the_eleventh_request_in_a_window_is_rejected(user_id):
    """The headline requirement from the phase 2 definition of done."""
    for _ in range(settings.rate_limit_requests):
        assert (await check(user_id)).allowed

    result = await check(user_id)
    assert not result.allowed
    assert result.count == settings.rate_limit_requests
    assert result.remaining == 0


async def test_rejection_reports_a_usable_retry_after(user_id):
    for _ in range(settings.rate_limit_requests):
        await check(user_id)
    result = await check(user_id)
    assert not result.allowed
    assert 1 <= result.retry_after_s <= settings.rate_limit_window_s


async def test_users_have_independent_windows(user_id):
    other = f"test_user_{uuid.uuid4().hex[:12]}"
    try:
        for _ in range(settings.rate_limit_requests):
            await check(user_id)
        assert not (await check(user_id)).allowed
        # A different user is unaffected.
        assert (await check(other)).allowed
    finally:
        await reset(other)


async def test_window_slides(user_id, monkeypatch):
    """Entries age out continuously; the window is not a fixed bucket."""
    monkeypatch.setattr(settings, "rate_limit_window_s", 2)
    monkeypatch.setattr(settings, "rate_limit_requests", 3)

    for _ in range(3):
        assert (await check(user_id)).allowed
    assert not (await check(user_id)).allowed

    # After the window passes, the old entries are trimmed and slots free up.
    await asyncio.sleep(2.2)
    result = await check(user_id)
    assert result.allowed, "window did not slide"
    assert result.count == 1


async def test_concurrent_requests_cannot_exceed_the_limit(user_id):
    """The reason the script is Lua: without atomicity, races slip past."""
    limit = settings.rate_limit_requests
    results = await asyncio.gather(*[check(user_id) for _ in range(limit + 15)])
    allowed = [r for r in results if r.allowed]
    assert len(allowed) == limit, f"expected exactly {limit} allowed, got {len(allowed)}"


async def test_key_is_scoped_per_user(redis_available):
    assert key_for("user_abc") == "ratelimit:user_abc"


async def test_fails_open_when_redis_is_unreachable(monkeypatch):
    """§8: a broken limiter must never take down the app.

    Deliberately does not use the `user_id` fixture: its teardown talks to Redis,
    which this test has replaced with something that refuses every connection.
    """
    import app.core.rate_limit as rl

    class DeadRedis:
        async def script_load(self, *a, **k):
            raise OSError("connection refused")

    monkeypatch.setattr(rl, "get_redis", lambda: DeadRedis())
    monkeypatch.setattr(rl, "_script_sha", None)

    result = await check(f"test_user_{uuid.uuid4().hex[:12]}")
    assert result.allowed, "limiter must fail open"
    assert result.retry_after_s == 0


async def test_expiry_is_set_so_keys_do_not_leak(user_id):
    await check(user_id)
    ttl = await get_redis().pttl(key_for(user_id))
    assert 0 < ttl <= settings.rate_limit_window_s * 1000


async def test_entries_in_the_same_millisecond_all_count(user_id):
    """ZADD is a set - identical members would collapse and undercount."""
    start = time.time()
    results = await asyncio.gather(*[check(user_id) for _ in range(5)])
    assert time.time() - start < 1.0
    assert max(r.count for r in results) == 5
