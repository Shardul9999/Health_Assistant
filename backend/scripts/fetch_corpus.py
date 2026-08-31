#!/usr/bin/env python3
"""Download manifest sources into data/raw/ as a frozen snapshot.

    python scripts/fetch_corpus.py                # everything
    python scripts/fetch_corpus.py --priority 1   # the 24-doc core set

who.int / cdc.gov / nhs.uk block the default python UA (see CORPUS_NOTES.md), so we
send a browser UA and go one request at a time with a delay. That is deliberate:
this runs once, and hammering public health sites to save four minutes is not a
trade worth making.

Files land as data/raw/<manifest-id>.html so ingest.py --manifest-id lines up.
Anything that fails here is expected to be saved by hand from a browser.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = BACKEND_ROOT.parent / "data" / "corpus_manifest.json"
RAW_DIR = BACKEND_ROOT.parent / "data" / "raw"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}
TIMEOUT = 30
DELAY_S = 1.5
MIN_BYTES = 5000


def fetch(source: dict, force: bool) -> tuple[str, str]:
    """Returns (status, detail) where status is ok | skip | thin | fail."""
    dest = RAW_DIR / f"{source['id']}.html"
    if dest.exists() and not force:
        return "skip", f"{dest.stat().st_size:,} B already on disk"

    # WHO slugs contain literal parentheses, e.g. influenza-(seasonal)
    url = quote(source["url"], safe=":/?#[]@!$&'*+,;=-._~()")
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except Exception as e:
        return "fail", f"{type(e).__name__}"

    if r.status_code != 200:
        return "fail", f"HTTP {r.status_code}"
    if len(r.content) < MIN_BYTES:
        # Almost always a client-rendered shell; ingesting it would produce
        # near-empty chunks that quietly degrade retrieval.
        return "thin", f"only {len(r.content):,} B"

    dest.write_bytes(r.content)
    return "ok", f"{len(r.content):,} B"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--priority", type=int, help="fetch sources at or above this priority")
    ap.add_argument("--force", action="store_true", help="re-download files already present")
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    sources = json.loads(MANIFEST.read_text(encoding="utf-8"))["sources"]
    if args.priority:
        sources = [s for s in sources if s.get("priority", 99) <= args.priority]

    print(f"Fetching {len(sources)} sources into {RAW_DIR}\n", flush=True)
    tally: dict[str, list[str]] = {"ok": [], "skip": [], "thin": [], "fail": []}

    for i, source in enumerate(sources, 1):
        status, detail = fetch(source, args.force)
        tally[status].append(source["id"])
        print(f"  [{i:>2}/{len(sources)}] {status.upper():<5} {source['id']:<34} {detail}", flush=True)
        if status not in ("skip",):
            time.sleep(DELAY_S)

    print(
        f"\n{len(tally['ok'])} downloaded, {len(tally['skip'])} already present, "
        f"{len(tally['thin'])} thin, {len(tally['fail'])} failed"
    )
    for label in ("thin", "fail"):
        if tally[label]:
            print(f"\n{label} - save these by hand from a browser into data/raw/<id>.html:")
            for sid in tally[label]:
                url = next(s["url"] for s in sources if s["id"] == sid)
                print(f"  {sid:<34} {url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
