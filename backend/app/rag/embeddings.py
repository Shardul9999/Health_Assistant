"""Gemini embedding wrapper (text-embedding-004, 768-dim).

Ingestion and query embedding MUST go through this module so both sides use the
same model and dimensionality. The only thing that differs is `task_type`:
Gemini embeds documents and queries into a shared space but asymmetrically, and
using RETRIEVAL_QUERY for a search query measurably improves recall over
embedding it as a document.
"""

from __future__ import annotations

import time

from google import genai
from google.genai import types

from app.config import settings

# The API accepts up to 100 inputs per embed_content call.
MAX_BATCH = 100

_client: genai.Client | None = None

# Populated by every call; Phase 4 reads it for docs/BENCHMARKS.md (§11).
latencies_ms: list[float] = []


def _get_client() -> genai.Client:
    global _client
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set — see backend/.env.example")
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


async def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    client = _get_client()
    out: list[list[float]] = []
    for start in range(0, len(texts), MAX_BATCH):
        batch = texts[start : start + MAX_BATCH]
        t0 = time.perf_counter()
        result = await client.aio.models.embed_content(
            model=settings.embedding_model,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.embedding_dimensions,
            ),
        )
        latencies_ms.append((time.perf_counter() - t0) * 1000)
        out.extend(list(e.values) for e in result.embeddings)

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
