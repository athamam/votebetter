"""Shared settings for VoteBetter.

The model is set in exactly one place: every agent uses MODEL_NAME through the
Portkey gateway. PORTKEY_API_KEY is read from .env in this repo folder first,
then from .env one folder up. It is never written to any file in the repo.
Without a key the guide still opens read-only; only agent runs are disabled.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent                       # the repo folder
DATA_DIR = ROOT / "data"
FRONTEND_DIR = ROOT / "frontend"
OUTPUT_DIR = ROOT / "output"
SOURCE_CACHE_DIR = DATA_DIR / "source_cache"    # saved copies of every page a fact was checked against
CANDIDATES_PATH = DATA_DIR / "candidates.json"  # official ballot list (hand-entered from state election offices)
GUIDE_PATH = DATA_DIR / "guide.json"            # verified output of the agent pipeline
TOKEN_LOG_PATH = OUTPUT_DIR / "token_log.jsonl"  # one line per agent run: tokens in / cached / out
SAFETY_LOG_PATH = OUTPUT_DIR / "safety_log.jsonl"  # every claim the verifier rejected, and why

# Repo folder first, then one level up (required by the project brief).
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

# --- Model: the ONLY model used anywhere in this app ---
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")

# --- Per-run limits (one agent run = one candidate profile, one issue, or one question) ---
MAX_MODEL_REQUESTS = 25          # model calls in one run
MAX_TOTAL_TOKENS = 250_000       # input + output tokens in one run
MAX_TOOL_CALLS = 30              # source reads in one run
MAX_WEB_SEARCHES = 8             # web searches in one run
MAX_OUTPUT_TOKENS = 6_000        # cap on any single model response

# --- App-wide spending caps (live features in the web app) ---
MAX_LIVE_RUNS_PER_SESSION = 15   # refresh + questions per browser session
MAX_LIVE_RUNS_PER_NETWORK = 30   # all sessions from one network (IP address)
MAX_LIVE_RUNS_PER_DAY = 200      # all users combined; resets at midnight
MAX_QUESTION_CHARS = 500         # longest question a user can send

# --- Source fetching ---
FETCH_TIMEOUT_S = 25
MAX_SOURCE_CHARS = 60_000        # longest page text handed to an agent
