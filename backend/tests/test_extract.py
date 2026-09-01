"""Extraction must survive what a browser's Save As actually writes to disk.

`data/CORPUS_NOTES.md` instructs the operator to save pages by hand because the
manifest's sites block automated requests. That makes the browser save formats
the documented ingestion path, so they are tested here against fixtures built
the way Chrome builds them - quoted-printable MIME parts, sibling image parts,
iframes - rather than against hand-written snippets that happen to parse.

The failure this suite exists to prevent is silent: an unreadable save produces
a confusing error at ingest time, months after the corpus work was done, with
nobody around to debug it.
"""

from __future__ import annotations

import base64
import quopri

import pytest

from app.rag.extract import (
    MIN_USABLE_CHARS,
    SUPPORTED_SUFFIXES,
    ExtractionError,
    extract_bytes,
    html_from_mhtml,
    sniff_format,
)

# Long enough to clear MIN_USABLE_CHARS, and shaped like an article so
# trafilatura's precision mode keeps it.
ARTICLE_BODY = " ".join(
    [
        "A sore throat is usually a symptom of a viral infection such as a cold or flu.",
        "It normally gets better by itself within a week without any treatment at all.",
        "Symptoms include a painful throat, a mild cough, and a raised temperature.",
        "You can ease the discomfort by gargling with warm salty water several times.",
        "Drinking plenty of cool or warm fluids helps, and avoid anything very hot.",
        "Speak to a pharmacist about medicines that soothe the pain and reduce fever.",
        "Most people do not need antibiotics because they do not work on viruses.",
        "See a doctor if the sore throat does not improve after one full week passes.",
        "Also seek advice if you have a very high temperature or feel unusually hot.",
        "Children who cannot swallow fluids at all should be seen by a doctor today.",
    ]
    * 3
)

PAGE_HTML = (
    "<!DOCTYPE html><html><head><meta charset='utf-8'>"
    "<title>Sore throat</title></head><body>"
    "<nav>Home Health A-Z Services</nav>"
    f"<article><h1>Sore throat</h1><p>{ARTICLE_BODY}</p></article>"
    "<footer>Crown copyright</footer></body></html>"
).encode("utf-8")

PAGE_URL = "https://www.nhs.uk/conditions/sore-throat/"


def build_mhtml(
    parts: list[tuple[str, str, bytes]],
    snapshot_location: str | None = PAGE_URL,
) -> bytes:
    """Assemble an MHTML archive the way Chrome's 'Single File' save does.

    parts: (content_type, content_location, payload). HTML payloads are encoded
    quoted-printable and binary payloads base64, matching Blink's output.
    """
    boundary = "----MultipartBoundary--pytestFixture01234567--"
    head = ["From: <Saved by Blink>"]
    if snapshot_location:
        head.append(f"Snapshot-Content-Location: {snapshot_location}")
    head += [
        "Subject: Sore throat",
        "MIME-Version: 1.0",
        f'Content-Type: multipart/related;\r\n\ttype="text/html";\r\n\tboundary="{boundary}"',
        "",
        "",
    ]

    body = []
    for content_type, location, payload in parts:
        if content_type.startswith("text/"):
            encoding = "quoted-printable"
            encoded = quopri.encodestring(payload).decode("ascii")
        else:
            encoding = "base64"
            encoded = base64.b64encode(payload).decode("ascii")
        body += [
            f"--{boundary}",
            f"Content-Type: {content_type}",
            f"Content-Transfer-Encoding: {encoding}",
            f"Content-Location: {location}",
            "",
            encoded,
        ]
    body.append(f"--{boundary}--")

    return ("\r\n".join(head + body) + "\r\n").encode("utf-8")


SIMPLE_MHTML = build_mhtml(
    [
        ("text/html", PAGE_URL, PAGE_HTML),
        ("image/png", "https://assets.nhs.uk/logo.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64),
    ]
)


# ------------------------------------------------------------------- sniffing


def test_mhtml_recognised_by_extension():
    assert sniff_format(SIMPLE_MHTML, ".mhtml") == "mhtml"
    assert sniff_format(SIMPLE_MHTML, ".mht") == "mhtml"


def test_mhtml_recognised_when_renamed_to_html():
    """The exact mistake someone makes when .mhtml 'does not work'.

    Renaming used to produce advice to "save the rendered DOM instead", which is
    what they had just done - so they would try it again and fail again.
    """
    assert sniff_format(SIMPLE_MHTML, ".html") == "mhtml"


def test_plain_html_not_mistaken_for_mhtml():
    assert sniff_format(PAGE_HTML, ".html") == "html"
    assert sniff_format(PAGE_HTML, ".htm") == "html"
    assert sniff_format(PAGE_HTML, ".xhtml") == "html"


def test_pdf_recognised_by_magic_bytes_over_extension():
    assert sniff_format(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n", ".html") == "pdf"


def test_html_recognised_without_any_extension():
    assert sniff_format(PAGE_HTML, "") == "html"


def test_unknown_binary_is_rejected_by_name():
    with pytest.raises(ExtractionError, match="Unsupported source type"):
        sniff_format(b"\x00\x01\x02 not a document", ".bin")


def test_supported_suffixes_cover_every_browser_save_format():
    for suffix in (".html", ".htm", ".mhtml", ".mht"):
        assert suffix in SUPPORTED_SUFFIXES


# ---------------------------------------------------------------------- mhtml


def test_mhtml_yields_the_same_text_as_the_plain_html():
    """The whole point: a single-file save must ingest identically."""
    assert extract_bytes(SIMPLE_MHTML, "p.mhtml", ".mhtml") == extract_bytes(
        PAGE_HTML, "p.html", ".html"
    )


def test_mhtml_quoted_printable_soft_breaks_are_decoded():
    """Quoted-printable wraps at 76 chars with '=' soft breaks mid-word.

    Left undecoded, the text is littered with '=' and the chunker embeds
    garbage - the kind of corruption that survives ingestion silently.
    """
    text = extract_bytes(SIMPLE_MHTML, "p.mhtml", ".mhtml")
    assert "=\r\n" not in text
    assert "gets better by itself" in text


def test_main_frame_wins_over_a_larger_iframe():
    """Ad and consent iframes are text/html parts too.

    Size alone would pick the wrong one here, so Snapshot-Content-Location has
    to decide.
    """
    filler = ("<p>consent notice paragraph for the vendor list</p>" * 400).encode()
    archive = build_mhtml(
        [
            ("text/html", PAGE_URL, PAGE_HTML),
            ("text/html", "https://consent.example/iframe", filler),
        ]
    )
    assert b"Sore throat" in html_from_mhtml(archive)


def test_largest_html_part_wins_when_no_snapshot_header():
    """Some writers omit Snapshot-Content-Location; fall back to size."""
    tiny = b"<html><body><p>tracking pixel frame</p></body></html>"
    archive = build_mhtml(
        [("text/html", "https://x.example/px", tiny), ("text/html", PAGE_URL, PAGE_HTML)],
        snapshot_location=None,
    )
    assert b"Sore throat" in html_from_mhtml(archive)


def test_mhtml_with_no_html_part_explains_itself():
    archive = build_mhtml([("image/png", "https://x/y.png", b"\x89PNG\r\n\x1a\n")])
    with pytest.raises(ExtractionError, match="no HTML part"):
        html_from_mhtml(archive)


def test_non_utf8_page_is_not_mojibaked():
    """A page saved as latin-1 must decode via its meta charset, not utf-8.

    Reading bytes as utf-8 with errors="replace" turns every accented character
    into U+FFFD, and that corruption is invisible until it is already embedded.
    """
    body = ARTICLE_BODY.replace("temperature", "temp\xe9rature")
    page = (
        "<!DOCTYPE html><html><head>"
        "<meta http-equiv='Content-Type' content='text/html; charset=iso-8859-1'>"
        f"</head><body><article><h1>Fi\xe8vre</h1><p>{body}</p></article></body></html>"
    ).encode("iso-8859-1")

    text = extract_bytes(page, "fievre.html", ".html")
    assert "�" not in text
    assert "temp\xe9rature" in text


# ----------------------------------------------------------------- diagnostics


def test_bot_block_page_is_named_as_such():
    """The manifest's sites serve these, so saving one by accident is likely."""
    page = (
        "<html><body><h1>Access Denied</h1>"
        "<p>You don't have permission to access this resource on this server.</p>"
        "</body></html>"
    ).encode()
    with pytest.raises(ExtractionError, match="bot-block or CAPTCHA"):
        extract_bytes(page, "cdc-stroke-signs.html", ".html")


def test_cloudflare_interstitial_is_named_as_such():
    page = (
        "<html><body><h1>Just a moment...</h1>"
        "<p>Checking your browser before accessing the site.</p></body></html>"
    ).encode()
    with pytest.raises(ExtractionError, match="bot-block or CAPTCHA"):
        extract_bytes(page, "who-malaria.html", ".html")


def test_truncated_save_is_reported_as_too_small():
    with pytest.raises(ExtractionError, match="too small to be a saved"):
        extract_bytes(b"<html><body><p>hi</p></body></html>", "x.html", ".html")


def test_client_rendered_shell_recommends_the_single_file_save():
    """This is the case the old message assumed for *every* failure.

    Now it fires only when the page really is mostly scripts - and it points at
    the .mhtml save, which captures the rendered DOM.
    """
    shell = (
        "<html><head>"
        + "<script src='/static/app.js'></script>" * 8
        + "</head><body><div id='root'></div>"
        + "<script>window.__DATA__=" + "0" * 3000 + "</script>"
        + "</body></html>"
    ).encode()
    with pytest.raises(ExtractionError, match="client-rendered shell"):
        extract_bytes(shell, "spa.html", ".html")


def test_diagnostic_never_repeats_the_old_blanket_advice_for_a_block_page():
    """Regression guard on the misleading message itself."""
    page = b"<html><body><h1>Access Denied</h1><p>Request blocked.</p></body></html>"
    with pytest.raises(ExtractionError) as excinfo:
        extract_bytes(page, "cdc-flu-symptoms.html", ".html")
    assert "client-rendered shell" not in str(excinfo.value)


def test_error_messages_name_the_offending_file():
    """Across a 50-document `--all` run, a message without the filename is noise."""
    for page in (
        b"<html><body><h1>Access Denied</h1></body></html>",
        b"<html><body>tiny</body></html>",
    ):
        with pytest.raises(ExtractionError) as excinfo:
            extract_bytes(page, "who-dengue.html", ".html")
        assert "who-dengue.html" in str(excinfo.value)


# ----------------------------------------------------------------- plain paths


def test_plain_text_passes_through_unchanged():
    body = ARTICLE_BODY.encode("utf-8")
    assert extract_bytes(body, "notes.txt", ".txt") == ARTICLE_BODY


def test_good_html_clears_the_usable_threshold():
    assert len(extract_bytes(PAGE_HTML, "p.html", ".html")) >= MIN_USABLE_CHARS
