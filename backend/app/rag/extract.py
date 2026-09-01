"""Document text extraction (§5).

Handles the formats a *browser* actually produces, not just what `curl` fetches.
`data/CORPUS_NOTES.md` tells you to save pages by hand - who.int, cdc.gov and
nhs.uk all block automated requests - so the browser's save formats are the
documented ingestion path and every one of them has to work.

What browsers produce from Ctrl+S:

| Browser        | Menu choice              | Result                                  |
|----------------|--------------------------|-----------------------------------------|
| Chrome / Edge  | Webpage, Single File     | `.mhtml` - MIME multipart, *not* HTML   |
| Chrome / Edge  | Webpage, Complete        | `.html` + `_files/` folder              |
| Firefox        | Web Page, complete       | `.html` + `_files/` folder              |
| any            | Webpage, HTML Only       | `.html`, close to what curl returns     |

Only the last was previously supported. The single-file `.mhtml` is Chrome's
*first* listed option, so it is the one a hurried person picks.

Format is decided by sniffing the bytes, never by the extension alone. Someone
who renames `page.mhtml` to `page.html` to "make it work" gets the right
handling instead of a misleading error.
"""

from __future__ import annotations

import email
import email.policy
import re
from pathlib import Path

# Below this, extraction has effectively failed even if it returned something -
# a cookie wall or a bot-block interstitial yields a few dozen characters.
MIN_USABLE_CHARS = 500

_HTML_SUFFIXES = frozenset({".html", ".htm", ".xhtml"})
_MHTML_SUFFIXES = frozenset({".mhtml", ".mht"})
_TEXT_SUFFIXES = frozenset({".txt", ".md"})

# Every extension the ingester knows how to read. `--all` probes data/raw/ with
# this, so a browser save lands without being renamed to something else first.
SUPPORTED_SUFFIXES: tuple[str, ...] = (
    ".html",
    ".htm",
    ".xhtml",
    ".mhtml",
    ".mht",
    ".pdf",
    ".txt",
    ".md",
)


class ExtractionError(Exception):
    """Extraction failed in a way the operator can act on."""


# --------------------------------------------------------------------- sniffing

# Chrome writes "Content-Type: multipart/related" plus a boundary in the leading
# headers. Edge and the Firefox MHTML add-ons write the same shape.
_MHTML_MARKER = re.compile(rb"content-type:\s*multipart/related", re.IGNORECASE)
_BOUNDARY = re.compile(rb"boundary\s*=", re.IGNORECASE)
_MARKUP_MARKER = re.compile(rb"<\s*(?:!doctype\s+html|html|head|body)\b", re.IGNORECASE)


def sniff_format(data: bytes, suffix: str) -> str:
    """Decide how to read these bytes. Content wins over the file extension.

    Extensions lie routinely here: browsers choose them, and people rename files
    when an import fails. The magic bytes do not lie.
    """
    head = data[:4096]

    if data.startswith(b"%PDF"):
        return "pdf"
    if _MHTML_MARKER.search(head) and _BOUNDARY.search(head):
        return "mhtml"

    suffix = suffix.lower()
    if suffix in _MHTML_SUFFIXES:
        return "mhtml"
    if suffix == ".pdf":
        return "pdf"
    if suffix in _HTML_SUFFIXES:
        return "html"
    if suffix in _TEXT_SUFFIXES:
        return "text"

    # No extension match: fall back to whether it looks like markup at all.
    if _MARKUP_MARKER.search(head):
        return "html"
    raise ExtractionError(
        f"Unsupported source type '{suffix or '(no extension)'}'. "
        f"Supported: {', '.join(SUPPORTED_SUFFIXES)}."
    )


# ------------------------------------------------------------------------ mhtml


def html_from_mhtml(data: bytes) -> bytes:
    """Pull the main document out of a Chrome/Edge single-file save.

    An MHTML archive holds the page *and* its stylesheets, images and iframes as
    MIME parts. Several parts can be `text/html` - every iframe is one - so the
    main frame is identified by matching the archive's `Snapshot-Content-Location`
    header, falling back to the largest HTML part, which an ad or consent iframe
    will never be.

    Returns undecoded bytes: quoted-printable and base64 are undone, but the
    charset is left for trafilatura to sniff, exactly as for a plain file.
    """
    message = email.message_from_bytes(data, policy=email.policy.default)

    main_location = (
        message.get("Snapshot-Content-Location") or message.get("Content-Location") or ""
    ).strip()

    candidates: list[tuple[str, bytes]] = []
    for part in message.walk():
        if part.get_content_type() != "text/html":
            continue
        payload = part.get_payload(decode=True)
        if payload:
            candidates.append(((part.get("Content-Location") or "").strip(), payload))

    if not candidates:
        raise ExtractionError(
            "This MHTML archive contains no HTML part. It may have been saved "
            "while the page was still loading - reopen the page, wait for it to "
            "finish, then save it again."
        )

    if main_location:
        for location, payload in candidates:
            if location == main_location:
                return payload

    return max(candidates, key=lambda c: len(c[1]))[1]


# ------------------------------------------------------------------------- html

# Text that means the saved file is an interstitial rather than the article.
# Worth naming explicitly: the sites in the manifest are exactly the ones that
# serve these, so saving one by accident is a realistic mistake.
_BLOCK_PAGE_SIGNS = (
    "access denied",
    "attention required",
    "just a moment",
    "checking your browser",
    "enable javascript and cookies to continue",
    "request blocked",
    "you have been blocked",
    "403 forbidden",
    "error 1020",
)


def _diagnose_html(data: bytes, name: str, extracted: str | None) -> str:
    """Explain *why* an HTML file yielded no usable text.

    The previous message said "probably a client-rendered shell - save the
    rendered DOM instead" for every failure, which is actively misleading when
    the user has already done that and hit some other problem.
    """
    lowered = data.decode("utf-8", errors="replace").lower()
    got = len((extracted or "").strip())

    for sign in _BLOCK_PAGE_SIGNS:
        if sign in lowered:
            return (
                f"{name} looks like a bot-block or CAPTCHA page, not the article "
                f"(it contains {sign!r}). Open the URL in a normal browser tab, "
                "confirm you can read the content, then save that page."
            )

    if len(data) < 2048:
        return (
            f"{name} is only {len(data):,} bytes - too small to be a saved "
            "article. The download was probably interrupted, or the page was "
            "saved before it finished loading. Save it again."
        )

    scripts = lowered.count("<script")
    if scripts >= 5 and got < MIN_USABLE_CHARS:
        return (
            f"{name} is {len(data):,} bytes but almost all of it is scripts "
            f"({scripts} <script> tags, {got} characters of text extracted). "
            "This is a client-rendered shell. In Chrome use "
            "'Save as -> Webpage, Single File (.mhtml)', which captures the "
            "rendered page, or copy the article text into a .txt file."
        )

    return (
        f"No article text could be extracted from {name} "
        f"({len(data):,} bytes in, {got} characters out). The page structure may "
        "be unusual. Fallback: select the article in your browser, copy it, and "
        f"save it as data/raw/{Path(name).stem}.txt - plain text ingests fine."
    )


def extract_html(data: bytes, name: str) -> str:
    """Run trafilatura over raw HTML bytes.

    Bytes rather than a decoded string on purpose: trafilatura sniffs the
    charset from the meta tag and the byte pattern. Forcing utf-8 with
    errors="replace" silently corrupts any page saved in another encoding, and
    the damage surfaces much later as mojibake inside an embedded chunk.
    """
    import trafilatura

    text = trafilatura.extract(
        data,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )
    if not text or len(text.strip()) < MIN_USABLE_CHARS:
        raise ExtractionError(_diagnose_html(data, name, text))
    return text


# -------------------------------------------------------------------- dispatch


def extract_bytes(data: bytes, name: str, suffix: str) -> str:
    """Extract article text from in-memory bytes. PDFs go through extract_file."""
    kind = sniff_format(data, suffix)

    if kind == "mhtml":
        return extract_html(html_from_mhtml(data), name)
    if kind == "html":
        return extract_html(data, name)
    if kind == "text":
        return data.decode("utf-8", errors="replace")
    raise ExtractionError(f"{name} is a PDF; read it from disk with extract_file().")


def extract_file(path: Path) -> str:
    """Read one source file and return its article text."""
    data = path.read_bytes()
    if not data:
        raise ExtractionError(f"{path.name} is empty (0 bytes).")

    if sniff_format(data, path.suffix) == "pdf":
        import fitz  # pymupdf

        with fitz.open(path) as doc:
            text = "\n\n".join(page.get_text("text") for page in doc)
        if len(text.strip()) < MIN_USABLE_CHARS:
            raise ExtractionError(
                f"{path.name} yielded {len(text.strip())} characters. A scanned "
                "PDF has no text layer - it needs OCR, which this pipeline does "
                "not do. Find an HTML version of the document instead."
            )
        return text

    return extract_bytes(data, path.name, path.suffix)
