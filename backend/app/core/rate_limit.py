"""Redis sliding-window rate limiter (§8).

10 requests per 60s per Clerk user. The window slides continuously rather than
resetting on a boundary, so a user cannot fire 10 requests at 11:59:59 and 10
more at 12:00:00.

Why Lua: the four operations below (trim, count, add, expire) have to be atomic.
Done as separate round trips, two concurrent requests can both read a count of 9
and both proceed. The script runs server-side in one shot, so they cannot. It is
also portable - the same script works against a hosted Redis in Phase 4 with no
change beyond REDIS_URL.

Fail open: if Redis is unreachable the request is allowed. A rate limiter that
takes down the app is worse than no rate limiter.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from redis.exceptions import RedisError

from app.config import settings
from app.core.redis_client import get_redis

log = logging.getLogger(__name__)

# KEYS[1] = the user's window key
# ARGV[1] = now (ms), ARGV[2] = window (ms), ARGV[3] = limit, ARGV[4] = unique member id
# Returns {allowed, count, oldest_timestamp_in_window}
_SLIDING_WINDOW_LUA = """
local key    = KEYS[1]
local now    = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit  = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local count = redis.call('ZCARD', key)

if count < limit then
  redis.call('ZADD', key, now, member)
  redis.call('PEXPIRE', key, window)
  return {1, count + 1, 0}
end

-- Denied. Report the oldest entry so the caller can compute retry_after.
local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
redis.call('PEXPIRE', key, window)
return {0, count, tonumber(oldest[2]) or now}
"""

_script_sha: str | None = None


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    count: int
    limit: int
    retry_after_s: int

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.count)


def key_for(user_id: str) -> str:
    return f"ratelimit:{user_id}"


async def check(user_id: str) -> RateLimitResult:
    """Record a request and report whether it is allowed."""
    global _script_sha

    limit = settings.rate_limit_requests
    window_ms = settings.rate_limit_window_s * 1000
    now_ms = int(time.time() * 1000)
    # Unique member per request: ZADD is a set, so two requests in the same
    # millisecond would otherwise collapse into one entry and undercount.
    member = f"{now_ms}-{time.perf_counter_ns()}"

    try:
        redis = get_redis()
        if _script_sha is None:
            _script_sha = await redis.script_load(_SLIDING_WINDOW_LUA)
        try:
            raw = await redis.evalsha(
                _script_sha, 1, key_for(user_id), now_ms, window_ms, limit, member
            )
        except RedisError as exc:
            # SCRIPT FLUSH or a failover drops the cached sha; reload once.
            if "NOSCRIPT" not in str(exc).upper():
                raise
            _script_sha = await redis.script_load(_SLIDING_WINDOW_LUA)
            raw = await redis.evalsha(
                _script_sha, 1, key_for(user_id), now_ms, window_ms, limit, member
            )
    except (RedisError, OSError) as exc:
        log.error("rate limiter unavailable, failing open: %s", type(exc).__name__)
        return RateLimitResult(allowed=True, count=0, limit=limit, retry_after_s=0)

    allowed, count, oldest = int(raw[0]), int(raw[1]), int(raw[2])
    retry_after_s = 0
    if not allowed:
        # The window frees a slot when the oldest entry ages out.
        retry_after_s = max(1, round((oldest + window_ms - now_ms) / 1000))

    return RateLimitResult(
        allowed=bool(allowed), count=count, limit=limit, retry_after_s=retry_after_s
    )


async def reset(user_id: str) -> None:
    """Clear a user's window. Used by tests."""
    try:
        await get_redis().delete(key_for(user_id))
    except (RedisError, OSError):
        pass
