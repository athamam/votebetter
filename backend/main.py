"""Web server: serves the guide and the two live AI features (Ask, Refresh).

Browsing reads data/guide.json and needs no API key. Ask and Refresh run agents,
so they need PORTKEY_API_KEY and are limited by the caps in guardrails.py.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_ai.exceptions import UsageLimitExceeded

from backend import agents, guardrails, pipeline
from backend.ask import ask
from backend.config import FRONTEND_DIR, GUIDE_PATH

app = FastAPI(title="VoteBetter", docs_url=None, redoc_url=None)
_refresh_lock = asyncio.Lock()  # one refresh at a time, so two never write the same file

try:
    MODEL = agents.build_model()
    MODEL_ERROR = None
except agents.MissingAPIKey as exc:
    MODEL, MODEL_ERROR = None, str(exc)


def load_guide() -> dict:
    return json.loads(GUIDE_PATH.read_text(encoding="utf-8"))


def find_race(race_id: str) -> dict | None:
    return next((r for r in load_guide()["races"] if r["id"] == race_id), None)


def _who(request: Request) -> tuple[str, str]:
    session = (request.headers.get("x-session-id") or "anonymous")[:64]
    ip = request.client.host if request.client else "unknown"
    return session, ip


@app.get("/api/guide")
def guide():
    return load_guide()


@app.get("/api/status")
def status(request: Request):
    session, _ = _who(request)
    return {"ai_ready": MODEL is not None, "ai_message": MODEL_ERROR, "limits": guardrails.remaining(session)}


class AskBody(BaseModel):
    race_id: str
    question: str


@app.post("/api/ask")
async def api_ask(body: AskBody, request: Request):
    if MODEL is None:
        return JSONResponse({"error": "Live questions are off because no API key is set. Browsing still works."}, 503)
    question, problem = guardrails.clean_question(body.question)
    if question is None:
        return JSONResponse({"error": problem}, 400)
    race = find_race(body.race_id)
    if race is None:
        return JSONResponse({"error": "Unknown race."}, 404)
    session, ip = _who(request)
    allowed, msg, left = guardrails.check_and_count(session, ip)
    if not allowed:
        return JSONResponse({"error": msg, "limits": left}, 429)
    try:
        result = await ask(MODEL, race, question)
    except UsageLimitExceeded:
        guardrails.log_safety("run_limit", "ask run hit its token/request limit", {"question": question})
        return JSONResponse({"error": "That question needed more work than one request allows. Try a narrower question.",
                             "limits": left}, 422)
    return {**result, "limits": left}


class RefreshBody(BaseModel):
    candidate_id: str
    issue_id: str


@app.post("/api/refresh")
async def api_refresh(body: RefreshBody, request: Request):
    if MODEL is None:
        return JSONResponse({"error": "Refresh is off because no API key is set. Browsing still works."}, 503)
    ids = {c["id"] for r in load_guide()["races"] for c in r["candidates"]}
    if body.candidate_id not in ids or body.issue_id not in pipeline.ISSUE_IDS:
        return JSONResponse({"error": "Unknown candidate or issue."}, 404)
    if _refresh_lock.locked():
        return JSONResponse({"error": "Another refresh is running. Please try again in a minute."}, 409)
    session, ip = _who(request)
    allowed, msg, left = guardrails.check_and_count(session, ip)
    if not allowed:
        return JSONResponse({"error": msg, "limits": left}, 429)
    async with _refresh_lock:
        try:
            summary = await pipeline.refresh_issue(MODEL, body.candidate_id, body.issue_id)
        except UsageLimitExceeded:
            guardrails.log_safety("run_limit", "refresh hit its token/request limit", body.model_dump())
            return JSONResponse({"error": "The search hit its spending limit before finishing. Nothing was changed.",
                                 "limits": left}, 422)
    return {**summary, "limits": left}


@app.middleware("http")
async def no_stale_pages(request: Request, call_next):
    """Browsers re-check page files on every load, so an update never shows an old cached copy."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")
