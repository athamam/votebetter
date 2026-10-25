"""Source policy and page fetching.

Every fact in the guide must point to a page on an allowed domain and quote that
page word for word. This module decides which domains are allowed, fetches pages
(falling back to the Internet Archive's copy when a site blocks automated
readers), saves the text it checked, and does the word-for-word quote check in
plain code, outside the AI.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from backend.config import FETCH_TIMEOUT_S, MAX_SOURCE_CHARS, SOURCE_CACHE_DIR

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36 VoteBetter/1.0 (student research project)"
)

# Wire services: allowed only as a secondary source for the candidate's own reported words.
SECONDARY_DOMAINS = ["apnews.com", "reuters.com"]

# Never a source, even if a search returns it (publicly editable or third-party summaries).
BLOCKED_DOMAINS = [
    "wikipedia.org", "wikimedia.org", "ballotpedia.org", "ballotready.org", "isidewith.com",
    "ontheissues.org", "votesmart.org", "reddit.com", "x.com", "twitter.com", "facebook.com",
    "instagram.com", "tiktok.com", "youtube.com", "threads.net", "truthsocial.com",
]

MIN_QUOTE_CHARS = 25
MAX_QUOTE_CHARS = 600


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _on_domain(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


@dataclass(frozen=True)
class SourcePolicy:
    """Which websites count as sources for one candidate."""

    campaign_domains: tuple[str, ...]
    official_domains: tuple[str, ...]

    @classmethod
    def for_candidate(cls, candidate: dict) -> SourcePolicy:
        return cls(tuple(candidate.get("campaign_domains", [])), tuple(candidate.get("official_domains", [])))

    def source_type(self, url: str) -> str | None:
        """'campaign', 'official', 'secondary', or None when the URL is not allowed."""
        host = _host(url)
        if not host or urlparse(url).scheme not in ("http", "https"):
            return None
        if any(_on_domain(host, d) for d in BLOCKED_DOMAINS):
            return None
        if any(_on_domain(host, d) for d in self.campaign_domains):
            return "campaign"
        if host.endswith(".gov") or any(_on_domain(host, d) for d in self.official_domains):
            return "official"
        if any(_on_domain(host, d) for d in SECONDARY_DOMAINS):
            return "secondary"
        return None

    def search_domains(self) -> list[str]:
        """Domains handed to the web search tool (the search itself is limited to these)."""
        return sorted({*self.campaign_domains, *self.official_domains, *SECONDARY_DOMAINS})


# --- text handling -------------------------------------------------------------

_QUOTE_MAP = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                            "—": "-", " ": " ", "…": "..."})


def normalize(text: str) -> str:
    """Lower-case, unify quote marks and dashes, collapse spaces: used only for matching."""
    text = unicodedata.normalize("NFKC", text).translate(_QUOTE_MAP).lower()
    return re.sub(r"\s+", " ", text).strip()


def quote_in_text(quote: str, page_text: str) -> bool:
    """True when the quote appears word for word in the page (ignoring case, spacing and quote styles)."""
    q = normalize(quote).strip(" .\"'")
    return MIN_QUOTE_CHARS <= len(q) <= MAX_QUOTE_CHARS and q in normalize(page_text)


def html_to_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    text = soup.get_text("\n", strip=True)
    return title, re.sub(r"\n{2,}", "\n", text)


def pdf_to_text(data: bytes) -> str:
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)


# --- fetching ---------------------------------------------------------------------

@dataclass
class Page:
    url: str              # the page the fact is attributed to
    fetched_from: str     # where the text actually came from (the page, or its Internet Archive copy)
    title: str
    text: str
    retrieved_at: str
    ok: bool
    error: str = ""


def _cache_path(url: str):
    return SOURCE_CACHE_DIR / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".json")


def _download(url: str, client: httpx.Client) -> tuple[str, str]:
    r = client.get(url)
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    if "pdf" in ctype or url.lower().split("?")[0].endswith(".pdf"):
        return "", pdf_to_text(r.content)
    if "html" not in ctype and "text" not in ctype:
        raise ValueError(f"unsupported content type {ctype!r}")
    return html_to_text(r.text)


def _archive_copy(url: str, client: httpx.Client) -> str | None:
    """Most recent Internet Archive copy of the page, as a raw-content URL."""
    r = client.get("https://archive.org/wayback/available", params={"url": url})
    snap = r.json().get("archived_snapshots", {}).get("closest") if r.status_code == 200 else None
    if not snap or not snap.get("available"):
        return None
    return f"https://web.archive.org/web/{snap['timestamp']}id_/{url}"


def fetch_page(url: str, *, use_cache: bool = True) -> Page:
    """Fetch a page's text, from the saved copy when available. Never raises."""
    path = _cache_path(url)
    if use_cache and path.exists():
        return Page(**json.loads(path.read_text(encoding="utf-8")))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    page = Page(url=url, fetched_from=url, title="", text="", retrieved_at=now, ok=False)
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=FETCH_TIMEOUT_S) as client:
        try:
            page.title, page.text = _download(url, client)
            page.ok = bool(page.text.strip())
        except Exception as exc:  # blocked, missing, or not a readable page
            page.error = f"{type(exc).__name__}: {str(exc)[:160]}"
            try:
                archived = _archive_copy(url, client)
                if archived:
                    page.title, page.text = _download(archived, client)
                    page.fetched_from = archived.replace("id_/", "/", 1)
                    page.ok = bool(page.text.strip())
            except Exception as exc2:
                page.error += f" | archive: {type(exc2).__name__}"
    page.text = page.text[: MAX_SOURCE_CHARS * 2]
    if page.ok:
        SOURCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(page.__dict__, ensure_ascii=False), encoding="utf-8")
    return page
