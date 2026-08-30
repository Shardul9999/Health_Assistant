#!/usr/bin/env python3
"""
Verify every URL in corpus_manifest.json still resolves before ingestion.

Slugs on who.int / cdc.gov / nhs.uk change without notice. Run this first —
a 404 caught here is a two-minute fix; a 404 caught during ingestion silently
gives you a smaller corpus than you think you have, and you won't notice until
retrieval starts missing.

Usage:
    python verify_corpus.py                 # check all
    python verify_corpus.py --priority 1    # check priority-1 sources only
    python verify_corpus.py --fix-hints     # print search URLs for anything broken
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlparse

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

HEADERS = {
    # Some gov sites 403 the default python-requests UA.
    "User-Agent": "Mozilla/5.0 (compatible; corpus-verifier/1.0; academic project)"
}
TIMEOUT = 15


def check(source):
    url = source["url"]
    # WHO slugs contain literal parentheses, e.g. influenza-(seasonal)
    safe_url = quote(url, safe=":/?#[]@!$&'*+,;=-._~()")
    try:
        r = requests.get(safe_url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        final = r.url
        redirected = urlparse(final).path.rstrip("/") != urlparse(safe_url).path.rstrip("/")
        return {
            "id": source["id"],
            "status": r.status_code,
            "ok": r.status_code == 200,
            "redirected_to": final if redirected else None,
            "bytes": len(r.content),
            "url": url,
            "title": source["title"],
        }
    except Exception as e:
        return {
            "id": source["id"],
            "status": None,
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "url": url,
            "title": source["title"],
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="corpus_manifest.json")
    ap.add_argument("--priority", type=int, help="only check sources at or above this priority")
    ap.add_argument("--fix-hints", action="store_true", help="print a search URL for each failure")
    args = ap.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)

    sources = manifest["sources"]
    if args.priority:
        sources = [s for s in sources if s.get("priority", 99) <= args.priority]

    print(f"Checking {len(sources)} sources...\n")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(check, sources))

    ok = [r for r in results if r["ok"]]
    # 403 is almost always bot-blocking (who.int, cdc.gov, nhs.uk all do this),
    # not a dead link. Treat it as "unknown", not "broken" — open it in a browser.
    blocked = [r for r in results if r["status"] == 403]
    broken = [r for r in results if not r["ok"] and r["status"] != 403]
    redirected = [r for r in ok if r.get("redirected_to")]
    thin = [r for r in ok if r.get("bytes", 0) < 5000]

    for r in ok:
        flag = ""
        if r.get("redirected_to"):
            flag = "  -> redirected"
        if r.get("bytes", 0) < 5000:
            flag += "  [THIN: likely a JS shell, check extraction]"
        print(f"  OK    {r['id']:<32} {r['bytes']:>7} B{flag}")

    for r in blocked:
        print(f"  BLOCK {r['id']:<32} HTTP 403 (bot-blocked, verify manually)")

    for r in broken:
        detail = r.get("error") or f"HTTP {r['status']}"
        print(f"  FAIL  {r['id']:<32} {detail}")

    print(f"\n{len(ok)} ok, {len(blocked)} blocked, {len(broken)} broken, "
          f"{len(redirected)} redirected, {len(thin)} thin")

    if blocked:
        print("\n403s are bot-blocking, not dead links. Options:")
        print("  1. Open each in a browser to confirm it loads, then save the HTML to data/raw/")
        print("  2. Use WHO's IRIS repository (apps.who.int/iris) for PDF versions of fact sheets")
        print("  3. Add a delay + rotate User-Agent (respect robots.txt and rate limits)")
        print("Manual download is the honest answer for a 50-document corpus. It's one afternoon.")

    if redirected:
        print("\nRedirects — update the manifest url field to the final URL:")
        for r in redirected:
            print(f"  {r['id']}: {r['redirected_to']}")

    if thin:
        print("\nThin responses — the page may render client-side.")
        print("Extraction will produce near-empty chunks. Verify with trafilatura before ingesting.")

    if broken and args.fix_hints:
        print("\nSearch these to find the new URL:")
        for r in broken:
            q = quote(f"{r['title']} site:{urlparse(r['url']).netloc}")
            print(f"  {r['id']}: https://duckduckgo.com/?q={q}")

    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
