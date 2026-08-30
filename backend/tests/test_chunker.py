"""Chunker invariants (§5): size window, sentence alignment, overlap."""

from app.rag.chunker import (
    OVERLAP_TOKENS,
    TARGET_MAX_TOKENS,
    chunk_text,
    count_tokens,
)

SENTENCE = (
    "Iron deficiency anaemia is caused by a lack of iron in the body, which "
    "reduces the number of healthy red blood cells available to carry oxygen. "
)


def _document(paragraphs: int) -> str:
    body = "\n\n".join(SENTENCE * 6 for _ in range(paragraphs))
    return f"Symptoms\n\n{body}\n\nCauses\n\n{body}"


def test_chunks_stay_within_the_ceiling():
    chunks = chunk_text(_document(8))
    assert chunks
    # A little slack: the packer admits a unit before re-measuring, so a chunk
    # can land just over target. It must never approach double.
    assert all(c.token_count <= TARGET_MAX_TOKENS * 1.25 for c in chunks)


def test_chunk_indexes_are_sequential():
    chunks = chunk_text(_document(8))
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_consecutive_chunks_overlap():
    chunks = chunk_text(_document(10))
    assert len(chunks) >= 2
    for previous, current in zip(chunks, chunks[1:]):
        head = current.content[:200]
        assert head[:60] in previous.content, "chunk does not begin with prior tail"
        assert count_tokens(head) > 0


def test_never_splits_mid_sentence():
    chunks = chunk_text(_document(10))
    for chunk in chunks:
        stripped = chunk.content.strip()
        # Every chunk ends at a sentence terminator or a list/heading line.
        assert stripped.endswith((".", "!", "?", ":")) or "\n" in stripped


def test_oversized_paragraph_is_split_on_sentences():
    giant = SENTENCE * 120  # comfortably over the ceiling, one paragraph
    chunks = chunk_text(giant)
    assert len(chunks) > 1
    assert all(c.token_count <= TARGET_MAX_TOKENS * 1.25 for c in chunks)


def test_short_document_yields_one_chunk():
    chunks = chunk_text("Anaemia is a condition. It has several causes.")
    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].token_count == count_tokens(chunks[0].content)


def test_overlap_budget_is_respected():
    chunks = chunk_text(_document(10))
    for previous, current in zip(chunks, chunks[1:]):
        # The carried-over prefix is bounded; it must not swallow a whole chunk.
        carried = current.content.split("\n\n")[0]
        assert count_tokens(carried) <= OVERLAP_TOKENS * 2
