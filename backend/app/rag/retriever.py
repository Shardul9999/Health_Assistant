"""pgvector similarity search with a hard floor (§5).

The floor is the whole point. Retrieval returning *something* for every query is
what makes a RAG system hallucinate confidently: the model gets handed three
loosely-related chunks and dutifully writes a fluent answer from them. Dropping
everything below 0.65 means an off-corpus question reaches the no-context path
instead, which is a correct answer rather than a failure.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.rag.embeddings import embed_query

# Populated per call; Phase 4 reads this for docs/BENCHMARKS.md (§11).
latencies_ms: list[float] = []


@dataclass(frozen=True)
class RetrievedChunk:
    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    title: str
    source_url: str
    source_org: str
    license: str
    similarity: float

    def snippet(self, limit: int = 240) -> str:
        if len(self.content) <= limit:
            return self.content
        return self.content[:limit].rsplit(" ", 1)[0] + "..."


# `<=>` is pgvector's cosine distance, matching the HNSW index built with
# vector_cosine_ops. Similarity is 1 - distance. Ordering by the raw operator
# (not by the computed similarity alias) is what lets the index be used.
_SEARCH_SQL = text(
    """
    SELECT
        c.id,
        c.document_id,
        c.content,
        d.title,
        d.source_url,
        d.source_org,
        d.license,
        1 - (c.embedding <=> CAST(:query_vector AS vector)) AS similarity
    FROM chunks c
    JOIN documents d ON d.id = c.document_id
    ORDER BY c.embedding <=> CAST(:query_vector AS vector)
    LIMIT :top_k
    """
)


async def search(
    db: AsyncSession,
    query_vector: list[float],
    top_k: int | None = None,
    threshold: float | None = None,
) -> list[RetrievedChunk]:
    """The pgvector query alone, given an already-embedded query.

    Split out from `retrieve` so the vector search can be timed on its own.
    Measuring it as (retrieve - embed) differences two much larger numbers and
    produces noise - it reported a 0.0ms median and a 140ms max for the same work.
    """
    top_k = top_k if top_k is not None else settings.retrieval_top_k
    threshold = threshold if threshold is not None else settings.similarity_threshold

    t0 = time.perf_counter()
    rows = (
        await db.execute(_SEARCH_SQL, {"query_vector": str(query_vector), "top_k": top_k})
    ).all()
    latencies_ms.append((time.perf_counter() - t0) * 1000)

    return [
        RetrievedChunk(
            id=r.id,
            document_id=r.document_id,
            content=r.content,
            title=r.title,
            source_url=r.source_url,
            source_org=r.source_org,
            license=r.license,
            similarity=float(r.similarity),
        )
        for r in rows
        if float(r.similarity) >= threshold
    ]


async def retrieve(
    db: AsyncSession,
    query: str,
    top_k: int | None = None,
    threshold: float | None = None,
) -> list[RetrievedChunk]:
    """Embed the query, search, and drop everything below the similarity floor.

    Returns [] when nothing survives - the caller must treat that as the
    NO_CONTEXT_FOUND path and must not fall back to the model's own knowledge.
    """
    query_vector = await embed_query(query)
    return await search(db, query_vector, top_k=top_k, threshold=threshold)
