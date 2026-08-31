"""Retrieval and the similarity floor (§5, §10).

Runs the real pgvector query against the local database. The query embedding is
stubbed for most tests - the thing under test is the SQL and the threshold, and
stubbing keeps the suite off the network and out of the Gemini quota. One test at
the bottom does use a real embedding, because the floor is only meaningful if the
actual numbers separate in-corpus from out-of-corpus.
"""

import random

import pytest
from sqlalchemy import text

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.rag import retriever
from app.rag.retriever import retrieve


def _unit_vector(seed: int = 7) -> list[float]:
    rng = random.Random(seed)
    raw = [rng.gauss(0, 1) for _ in range(settings.embedding_dimensions)]
    norm = sum(x * x for x in raw) ** 0.5
    return [x / norm for x in raw]


@pytest.fixture
async def db():
    try:
        async with AsyncSessionLocal() as session:
            count = (await session.execute(text("SELECT count(*) FROM chunks"))).scalar()
            if not count:
                pytest.skip("no chunks ingested - run `python scripts/ingest.py --all`")
            yield session
    except pytest.skip.Exception:
        raise
    except Exception:
        pytest.skip("Postgres unavailable - run `docker compose up -d`")


@pytest.fixture
def stub_embedding(monkeypatch):
    async def _fake(_query: str) -> list[float]:
        return _unit_vector()

    monkeypatch.setattr(retriever, "embed_query", _fake)


async def test_returns_at_most_top_k(db, stub_embedding):
    chunks = await retrieve(db, "anything", threshold=0.0)
    assert len(chunks) <= settings.retrieval_top_k


async def test_results_are_ordered_by_similarity(db, stub_embedding):
    chunks = await retrieve(db, "anything", threshold=0.0)
    sims = [c.similarity for c in chunks]
    assert sims == sorted(sims, reverse=True)


async def test_below_threshold_results_are_dropped(db, stub_embedding):
    everything = await retrieve(db, "anything", threshold=0.0)
    assert everything, "expected the unfiltered query to return chunks"

    cutoff = everything[0].similarity
    filtered = await retrieve(db, "anything", threshold=cutoff + 0.0001)
    assert len(filtered) < len(everything)
    assert all(c.similarity >= cutoff for c in filtered)


async def test_an_impossible_threshold_returns_nothing(db, stub_embedding):
    """The no-context path: retrieval returning [] is the contract."""
    assert await retrieve(db, "anything", threshold=0.999999) == []


async def test_every_chunk_carries_its_provenance(db, stub_embedding):
    """Citations are only possible if retrieval hands back source metadata."""
    for chunk in await retrieve(db, "anything", threshold=0.0):
        assert chunk.title
        assert chunk.source_url.startswith("http")
        assert chunk.source_org
        assert chunk.license
        assert chunk.content


async def test_snippet_is_truncated_without_cutting_a_word(db, stub_embedding):
    for chunk in await retrieve(db, "anything", threshold=0.0):
        snippet = chunk.snippet(120)
        assert len(snippet) <= 124
        if snippet.endswith("..."):
            assert not snippet[:-3].endswith(" ")


async def test_latency_is_recorded_for_benchmarks(db, stub_embedding):
    before = len(retriever.latencies_ms)
    await retrieve(db, "anything", threshold=0.0)
    assert len(retriever.latencies_ms) == before + 1


# --------------------------------------------------------------------------- live

@pytest.mark.live
async def test_the_floor_separates_in_corpus_from_out_of_corpus(db):
    """The §12 demo moment, asserted.

    Uses real Gemini embeddings. Deselect with `-m "not live"` to run offline.
    """
    in_corpus = await retrieve(db, "what causes iron deficiency anaemia")
    assert in_corpus, "an in-corpus question must retrieve something above the floor"

    out_of_corpus = await retrieve(db, "how do I fix my laptop keyboard")
    assert out_of_corpus == [], "an off-corpus question must reach the no-context path"
