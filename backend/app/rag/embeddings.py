"""Gemini embedding wrapper (gemini-embedding-001, truncated to 768 dims).

Ingestion and query embedding MUST go through this module so both sides use the
same model and dimensionality. The only thing that differs is `task_type`:
Gemini embeds documents and queries into a shared space but asymmetrically, and
using RETRIEVAL_QUERY for a search query measurably improves recall over
embedding it as a document.

Two non-obvious details:

* gemini-embedding-001 is natively 3072-dimensional and uses Matryoshka
  representation learning, so asking for 768 dims returns a meaningful prefix
  rather than a different model's output. That keeps vector(768) and the HNSW
  index from plan §3 exactly as specified.
* Only the full 3072-dim output arrives pre-normalized. Truncated vectors come
  back with an L2 norm around 0.59, so we normalize here. Cosine distance is
  scale-invariant and would survive that, but the similarity floor of 0.65 (§5)
  is a raw number compared against raw scores - it is only meaningful against
  unit vectors, and any later switch to an inner-product index would silently
  break without this.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import re
import time

from google import genai
from google.genai import types

from app.config import settings

log = logging.getLogger(__name__)

# The API accepts up to 100 inputs per embed_content call. The free tier's real
# constraint is tokens-per-minute rather than requests, and a 100-chunk batch of
# 600-token chunks is a 60k-token request - enough to trip the limit on its own.
# 16 keeps each request small enough to be retryable without redoing much work.
MAX_BATCH = 16

# Free-tier embedding quota is per-minute, so a bulk ingest has to pace itself.
# Raise these if you move to a paid tier; ingestion is the only caller that
# comes anywhere near the limit.
MIN_INTERVAL_S = 0.5
MAX_RETRIES = 6

_client: genai.Client | None = None
_last_call_at: float = 0.0
_throttle = asyncio.Lock()

# Populated by every call; Phase 4 reads it for docs/BENCHMARKS.md (§11).
latencies_ms: list[float] = []

_RETRY_DELAY = re.compile(r"'?retryDelay'?\s*:\s*'?(\d+(?:\.\d+)?)s")


def _is_retryable(exc: Exception) -> bool:
    """429 (quota) and 5xx (transient) are worth retrying. 400/403 are not."""
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if status in (429, 500, 502, 503, 504):
        return True
    text = str(exc)
    return any(m in text for m in ("RESOURCE_EXHAUSTED", "UNAVAILABLE", "429", "503"))


def _retry_after(exc: Exception, attempt: int) -> float:
    """Honour the server's retryDelay when it sends one, else back off."""
    match = _RETRY_DELAY.search(str(exc))
    if match:
        return float(match.group(1)) + 0.5
    # Exponential with jitter, so parallel callers don't retry in lockstep.
    return min(60.0, 2.0**attempt) + random.uniform(0, 1)


def _normalize(vec: list[float]) -> list[float]:
    """Scale to unit length. See the module docstring for why this is required."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        raise RuntimeError("embedding API returned a zero vector")
    return [x / norm for x in vec]


def _get_client() -> genai.Client:
    global _client
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set — see backend/.env.example")
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def _embed_batch(batch: list[str], task_type: str) -> list[list[float]]:
    """One API call, throttled and retried. Records latency for benchmarking."""
    global _last_call_at
    client = _get_client()

    for attempt in range(MAX_RETRIES + 1):
        async with _throttle:
            gap = time.monotonic() - _last_call_at
            if gap < MIN_INTERVAL_S:
                await asyncio.sleep(MIN_INTERVAL_S - gap)
            _last_call_at = time.monotonic()

        t0 = time.perf_counter()
        try:
            result = await client.aio.models.embed_content(
                model=settings.embedding_model,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=settings.embedding_dimensions,
                ),
            )
        except Exception as exc:
            if attempt >= MAX_RETRIES or not _is_retryable(exc):
                raise
            delay = _retry_after(exc, attempt)
            log.warning(
                "embedding call failed (attempt %d/%d), retrying in %.1fs",
                attempt + 1,
                MAX_RETRIES,
                delay,
            )
            await asyncio.sleep(delay)
            continue

        latencies_ms.append((time.perf_counter() - t0) * 1000)
        return [_normalize(list(e.values)) for e in result.embeddings]

    raise RuntimeError("unreachable: retry loop exited without returning")


async def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    out: list[list[float]] = []
    for start in range(0, len(texts), MAX_BATCH):
        out.extend(await _embed_batch(texts[start : start + MAX_BATCH], task_type))

    if len(out) != len(texts):
        raise RuntimeError(f"embedding count mismatch: sent {len(texts)}, got {len(out)}")
    for vec in out:
        if len(vec) != settings.embedding_dimensions:
            raise RuntimeError(
                f"embedding dimension mismatch: expected {settings.embedding_dimensions}, got {len(vec)}"
            )
    return out


async def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed chunk text for storage."""
    return await _embed(texts, "RETRIEVAL_DOCUMENT")


async def embed_query(text: str) -> list[float]:
    """Embed a user query for similarity search."""
    return (await _embed([text], "RETRIEVAL_QUERY"))[0]
