"""Collect official contact links for each candidate (plain code, no AI).

    python -m backend.contacts

Only two kinds of source count:
  1. links the candidate's own campaign website publishes (contact page, email, social accounts), and
  2. the campaign email on the state's official candidate list (New Jersey publishes one).
Social media is only linked to, never read. Results go into data/candidates.json under "contact".
"""

from __future__ import annotations

import io
import json
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from backend.config import CANDIDATES_PATH
from backend.sources import USER_AGENT

SOCIAL = {"x.com": "X (Twitter)", "twitter.com": "X (Twitter)", "facebook.com": "Facebook", "instagram.com": "Instagram",
          "youtube.com": "YouTube", "tiktok.com": "TikTok", "threads.net": "Threads", "linkedin.com": "LinkedIn",
          "truthsocial.com": "Truth Social", "bsky.app": "Bluesky"}
SKIP_PATHS = re.compile(r"/(sharer|share|intent|plugins|dialog|watch|embed|hashtag|p/|reel|status)/?", re.I)
NJ_EMAIL_LIST = ("https://www.nj.gov/state/elections/assets/pdf/election-results/2026/"
                 "2026-unofficial-general-candidates-us-senate-emails-0727.pdf")


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.").removeprefix("m.")


def from_campaign_site(domain: str, client: httpx.Client) -> dict:
    home = f"https://{domain}/"
    try:
        r = client.get(home)
        r.raise_for_status()
    except Exception as exc:
        return {"error": f"{type(exc).__name__}"}
    soup = BeautifulSoup(r.text, "html.parser")
    out: dict = {"website": str(r.url), "social": {}, "email": None, "contact_page": None, "found_on": str(r.url)}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("mailto:") and not out["email"]:
            email = href[7:].split("?")[0].strip()
            if re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", email, re.I):
                out["email"] = email
            continue
        url = urljoin(str(r.url), href)
        host = _host(url)
        label = next((v for k, v in SOCIAL.items() if host == k or host.endswith("." + k)), None)
        if label and label not in out["social"] and not SKIP_PATHS.search(urlparse(url).path):
            path = urlparse(url).path.strip("/")
            if path and "/" not in path.removeprefix("@"):  # a profile, not a post or share link
                out["social"][label] = url.split("?")[0]
        elif (_host(url) == _host(str(r.url)) and "cdn-cgi" not in url
              and re.search(r"contact", href + a.get_text(" "), re.I) and not out["contact_page"]):
            out["contact_page"] = url
    return out


def nj_official_emails(client: httpx.Client) -> list[str]:
    """Lines of New Jersey's official candidate list that contain a campaign email."""
    r = client.get(NJ_EMAIL_LIST)
    text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(r.content)).pages)
    return [line.strip() for line in text.splitlines() if "@" in line]


def main() -> None:
    ballot = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=25) as client:
        nj = nj_official_emails(client)
        for race in ballot["races"]:
            for cand in race["candidates"]:
                domain = cand["campaign_domains"][0] if cand["campaign_domains"] else None
                has_site = domain and cand["id"] != "kuniansky"  # her listed domain is her party's newspaper
                contact = from_campaign_site(domain, client) if has_site else {"social": {}}
                line = next((ln for ln in nj if race["state"] == "NJ" and ln.lower().startswith(cand["name"].lower())), None)
                if line:
                    contact["official_email"] = line.split()[-1]
                    contact["official_email_source"] = NJ_EMAIL_LIST
                cand["contact"] = contact
                print(cand["id"], json.dumps(contact)[:300])
    CANDIDATES_PATH.write_text(json.dumps(ballot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
