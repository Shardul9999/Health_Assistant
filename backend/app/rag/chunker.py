"""Semantic chunking (§5).

Strategy, in order of preference:
  1. Split on heading boundaries — a fact sheet's own section structure is the
     best available proxy for topical coherence.
  2. Within a section, pack paragraphs to 400-600 tokens.
  3. Only if a single paragraph busts the ceiling do we split it, and then only
     on sentence boundaries. Never mid-sentence.
Consecutive chunks carry an 80-token overlap so a fact that straddles a boundary
is retrievable from either side.

Token counts use tiktoken's cl100k_base. That is not Gemini's tokenizer, so the
numbers are an approximation — good enough for budgeting a 400-600 window, and
it avoids a network call per chunk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken

TARGET_MIN_TOKENS = 400
TARGET_MAX_TOKENS = 600
OVERLAP_TOKENS = 80

_encoder = tiktoken.get_encoding("cl100k_base")

# A heading is a markdown heading, or a short standalone line with no terminal
# punctuation — which is how extracted fact-sheet section titles usually land.
_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\"'“])")


def count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


@dataclass
class Chunk:
    content: str
    index: int
    token_count: int


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if _MD_HEADING.match(line):
        return True
    if len(stripped) > 90 or stripped.endswith((".", ",", ";", ":")):
        return False
    # Short, unpunctuated, and word-shaped: treat as a section title.
    return len(stripped.split()) <= 12 and any(c.isalpha() for c in stripped)


def _split_sections(text: str) -> list[str]:
    """Group the document into heading-led sections."""
    sections: list[list[str]] = [[]]
    for line in text.splitlines():
        if _is_heading(line) and any(s.strip() for s in sections[-1]):
            sections.append([line])
        else:
            sections[-1].append(line)
    return ["\n".join(s).strip() for s in sections if "\n".join(s).strip()]


def _split_paragraphs(section: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", section)]
    return [p for p in parts if p]


def _split_sentences(paragraph: str) -> list[str]:
    parts = [s.strip() for s in _SENTENCE_END.split(paragraph)]
    return [s for s in parts if s]


def _tail_overlap(text: str, budget: int = OVERLAP_TOKENS) -> str:
    """Last <=budget tokens of `text`, trimmed back to a sentence boundary."""
    sentences = _split_sentences(text)
    tail: list[str] = []
    used = 0
    for sentence in reversed(sentences):
        cost = count_tokens(sentence)
        if used + cost > budget and tail:
            break
        tail.insert(0, sentence)
        used += cost
        if used >= budget:
            break
    return " ".join(tail)


def chunk_text(text: str) -> list[Chunk]:
    """Split cleaned document text into overlapping, sentence-aligned chunks."""
    # Units are paragraphs, but never larger than the ceiling: oversized
    # paragraphs are pre-split on sentence boundaries so the packer below only
    # ever deals with pieces it can fit.
    units: list[str] = []
    for section in _split_sections(text):
        for paragraph in _split_paragraphs(section):
            if count_tokens(paragraph) <= TARGET_MAX_TOKENS:
                units.append(paragraph)
                continue
            buffer: list[str] = []
            size = 0
            for sentence in _split_sentences(paragraph):
                cost = count_tokens(sentence)
                if buffer and size + cost > TARGET_MAX_TOKENS:
                    units.append(" ".join(buffer))
                    buffer, size = [], 0
                buffer.append(sentence)
                size += cost
            if buffer:
                units.append(" ".join(buffer))

    chunks: list[Chunk] = []
    buffer: list[str] = []
    size = 0

    def flush() -> None:
        nonlocal buffer, size
        if not buffer:
            return
        content = "\n\n".join(buffer).strip()
        if content:
            chunks.append(Chunk(content=content, index=len(chunks), token_count=count_tokens(content)))
        overlap = _tail_overlap(content)
        buffer = [overlap] if overlap else []
        size = count_tokens(overlap) if overlap else 0

    for unit in units:
        cost = count_tokens(unit)
        if size + cost > TARGET_MAX_TOKENS and size >= TARGET_MIN_TOKENS:
            flush()
        elif size + cost > TARGET_MAX_TOKENS and buffer:
            # Under the minimum but over the ceiling: emitting a slightly short
            # chunk beats emitting an oversized one.
            flush()
        buffer.append(unit)
        size += cost

    if buffer:
        content = "\n\n".join(buffer).strip()
        if content:
            chunks.append(Chunk(content=content, index=len(chunks), token_count=count_tokens(content)))

    return chunks
