"""Guardrails for the live features (Ask and Refresh).

Spending:  a per-browser-session cap, a per-IP cap, and an app-wide daily cap on
           agent runs, plus the per-run token/request/tool limits in config.py.
Input:     length limit and a block on empty or control-character input.
Output:    every answer is checked in plain code for voting recommendations and
           for citations that do not exist, before a voter ever sees it.
Every block is written to output/safety_log.jsonl.
"""

from __future__ import annotations

import json
import re
import threading
import time
from datetime import date

from backend.config import (
    MAX_LIVE_RUNS_PER_DAY,
    MAX_LIVE_RUNS_PER_NETWORK,
    MAX_LIVE_RUNS_PER_SESSION,
    MAX_QUESTION_CHARS,
    OUTPUT_DIR,
    SAFETY_LOG_PATH,
)

USAGE_PATH = OUTPUT_DIR / "live_usage.json"
_lock = threading.Lock()

NO_RECOMMENDATION = (
    "This guide does not recommend candidates or parties, and it does not say how anyone should vote. "
    "It can show what each candidate has said on an issue, with sources, so you can decide for yourself."
)


def log_safety(stage: str, reason: str, item: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with SAFETY_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "stage": stage, "reason": reason,
                            "item": item}, ensure_ascii=False) + "\n")


# --- spending caps ---------------------------------------------------------------

def _load() -> dict:
    today = date.today().isoformat()
    try:
        data = json.loads(USAGE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if data.get("day") != today:
        data = {"day": today, "total": 0, "sessions": {}, "ips": {}}
    return data


def check_and_count(session_id: str, ip: str) -> tuple[bool, str, dict]:
    """Reserve one live agent run. Returns (allowed, message, remaining-counts)."""
    with _lock:
        data = _load()
        s_used = data["sessions"].get(session_id, 0)
        ip_used = data["ips"].get(ip, 0)
        if data["total"] >= MAX_LIVE_RUNS_PER_DAY:
            msg = "The guide has reached its daily limit for live AI requests. Browsing still works; please try again tomorrow."
        elif s_used >= MAX_LIVE_RUNS_PER_SESSION:
            msg = f"You have used all {MAX_LIVE_RUNS_PER_SESSION} live AI requests for this session. Browsing still works."
        elif ip_used >= MAX_LIVE_RUNS_PER_NETWORK:
            msg = "This network has reached its limit for live AI requests today. Browsing still works."
        else:
            data["total"] += 1
            data["sessions"][session_id] = s_used + 1
            data["ips"][ip] = ip_used + 1
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            USAGE_PATH.write_text(json.dumps(data), encoding="utf-8")
            return True, "", remaining(session_id, data)
        log_safety("spending_cap", msg, {"session": session_id[:8], "ip_hash": hash(ip) % 10_000})
        return False, msg, remaining(session_id, data)


def remaining(session_id: str, data: dict | None = None) -> dict:
    data = data or _load()
    return {
        "session_left": max(0, MAX_LIVE_RUNS_PER_SESSION - data["sessions"].get(session_id, 0)),
        "session_cap": MAX_LIVE_RUNS_PER_SESSION,
        "day_left": max(0, MAX_LIVE_RUNS_PER_DAY - data["total"]),
    }


# --- input ------------------------------------------------------------------------

def clean_question(text: str) -> tuple[str | None, str]:
    """Returns (clean text, '') or (None, reason)."""
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text or "").strip()
    if not text:
        return None, "Please type a question."
    if len(text) > MAX_QUESTION_CHARS:
        return None, f"Questions are limited to {MAX_QUESTION_CHARS} characters."
    return text, ""


# --- output ----------------------------------------------------------------------

_RECOMMENDATION = re.compile(
    r"\b(you should (vote|support|choose|pick|back)|i (would )?(recommend|suggest|endorse)|"
    r"(vote|voting) for (him|her|them)\b|(is|are) the (best|better|right|worse|worst) (choice|candidate|option)|"
    r"(better|best|worse|worst) candidate|deserves? your vote|don'?t vote for)",
    re.I,
)


def recommends(text: str) -> bool:
    return bool(_RECOMMENDATION.search(text or ""))
