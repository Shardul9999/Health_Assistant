#!/usr/bin/env python3
"""Corpus ingestion CLI (§5).

    python scripts/ingest.py --source ../data/raw/who_dengue.html --manifest-id who-dengue
    python scripts/ingest.py --source ../data/raw/x.pdf --title "..." --url "..." --org "WHO" --license "..."

Pipeline: extract -> clean -> semantic chunk -> embed (Gemini) -> insert.

Idempotent: the cleaned text is SHA-256'd and stored on the documents row. Re-running
against unchanged source is a no-op; --force replaces the document and its chunks.

Licence and source_url are written for every document, always. That table is the
answer to "where did your medical data come from" (see data/CORPUS_NOTES.md).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import delete, select  # noqa: E402

from app.db.models import Chunk, Document  # noqa: E402
from app.db.session import AsyncSessionLocal, engine  # noqa: E402
from app.rag.chunker import chunk_text  # noqa: E402
from app.rag.embeddings import embed_documents  # noqa: E402

MANIFEST = BACKEND_ROOT.parent / "data" / "corpus_manifest.json"


# --------------------------------------------------------------------------- extract


def extract(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import fitz  # pymupdf

        with fitz.open(path) as doc:
            return "\n\n".join(page.get_text("text") for page in doc)
    if suffix in {".html", ".htm", ".xhtml"}:
        import trafilatura

        raw = path.read_text(encoding="utf-8", errors="replace")
        text = trafilatura.extract(
            raw,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
        if not text:
            raise SystemExit(
                f"trafilatura extracted nothing from {path.name}. The page is probably a "
                "client-rendered shell - save the rendered DOM instead (see CORPUS_NOTES.md)."
            )
        return text
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="replace")
    raise SystemExit(f"Unsupported source type: {suffix}")


# --------------------------------------------------------------------------- clean

# Standalone page numbers, and "Page 3 of 12" style furniture from PDFs.
_PAGE_NUMBER = re.compile(r"^\s*(?:page\s+)?\d+(?:\s+of\s+\d+)?\s*$", re.IGNORECASE)
_URL_ONLY = re.compile(r"^\s*https?://\S+\s*$")


def clean(text: str) -> str:
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").replace("\xa0", " ").splitlines()]

    # A line repeated on most pages is a running header/footer, not content.
    counts: dict[str, int] = {}
    for ln in lines:
        s = ln.strip()
        if 0 < len(s) <= 120:
            counts[s] = counts.get(s, 0) + 1
    boilerplate = {s for s, n in counts.items() if n >= 4}

    kept = [
        ln
        for ln in lines
        if not _PAGE_NUMBER.match(ln)
        and not _URL_ONLY.match(ln)
        and ln.strip() not in boilerplate
    ]

    out = "\n".join(kept)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- manifest


def manifest_entry(source_id: str) -> dict:
    if not MANIFEST.exists():
        raise SystemExit(f"Manifest not found at {MANIFEST}")
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for src in data["sources"]:
        if src["id"] == source_id:
            return src
    ids = ", ".join(s["id"] for s in data["sources"][:8])
    raise SystemExit(f"No manifest entry with id '{source_id}'. First few ids: {ids}, ...")


# --------------------------------------------------------------------------- ingest


async def ingest(path: Path, title: str, url: str, org: str, license_: str, force: bool) -> None:
    raw = extract(path)
    text = clean(raw)
    if len(text) < 500:
        raise SystemExit(
            f"Only {len(text)} characters survived extraction+cleaning. That is too thin to "
            "ingest - check the source file before continuing."
        )

    digest = content_hash(text)

    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(select(Document).where(Document.content_hash == digest))
        ).scalar_one_or_none()
        if existing and not force:
            print(f"unchanged: '{existing.title}' already ingested ({digest[:12]}). Skipping.")
            return
        if existing and force:
            await db.execute(delete(Document).where(Document.id == existing.id))
            await db.commit()
            print(f"--force: replaced existing document {existing.id}")

        chunks = chunk_text(text)
        if not chunks:
            raise SystemExit("Chunker produced no chunks.")

        sizes = sorted(c.token_count for c in chunks)
        print(
            f"extracted {len(text):,} chars -> {len(chunks)} chunks "
            f"(tokens min={sizes[0]} median={sizes[len(sizes) // 2]} max={sizes[-1]})"
        )

        print(f"embedding {len(chunks)} chunks via Gemini...")
        vectors = await embed_documents([c.content for c in chunks])

        doc = Document(
            title=title,
            source_url=url,
            source_org=org,
            license=license_,
            content_hash=digest,
        )
        db.add(doc)
        await db.flush()
        doc_id = doc.id

        db.add_all(
            Chunk(
                document_id=doc_id,
                content=c.content,
                embedding=v,
                chunk_index=c.index,
                token_count=c.token_count,
            )
            for c, v in zip(chunks, vectors, strict=True)
        )
        await db.commit()

    print(f"ingested '{title}' -> document {doc_id}, {len(chunks)} chunks")


async def _main_async(args: argparse.Namespace, meta: dict) -> None:
    try:
        await ingest(path=args.source, force=args.force, **meta)
    finally:
        await engine.dispose()


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest one document into the vector store.")
    ap.add_argument("--source", required=True, type=Path, help="path to a PDF/HTML/TXT file")
    ap.add_argument("--manifest-id", help="pull title/url/org/license from data/corpus_manifest.json")
    ap.add_argument("--title")
    ap.add_argument("--url")
    ap.add_argument("--org")
    ap.add_argument("--license", dest="license_")
    ap.add_argument("--force", action="store_true", help="re-ingest even if the content hash matches")
    args = ap.parse_args()

    if not args.source.exists():
        raise SystemExit(f"No such file: {args.source}")

    meta: dict = {}
    if args.manifest_id:
        entry = manifest_entry(args.manifest_id)
        meta = {
            "title": entry["title"],
            "url": entry["url"],
            "org": entry["org"],
            "license_": entry["license"],
        }
    # Explicit flags win over the manifest.
    for key, value in (
        ("title", args.title),
        ("url", args.url),
        ("org", args.org),
        ("license_", args.license_),
    ):
        if value:
            meta[key] = value

    missing = [k for k in ("title", "url", "org", "license_") if not meta.get(k)]
    if missing:
        raise SystemExit(
            "Missing metadata: "
            + ", ".join(m.rstrip("_") for m in missing)
            + ". Pass --manifest-id, or supply --title/--url/--org/--license."
        )

    asyncio.run(_main_async(args, meta))


if __name__ == "__main__":
    main()
