"""Builds the verified guide: research -> code checks -> verifier -> scorer.

    python -m backend.pipeline                      # every candidate
    python -m backend.pipeline --candidate fazio    # one candidate
    python -m backend.pipeline --assemble           # rebuild data/guide.json from saved results (no AI)

Each candidate's result is saved to data/build/<id>.json, then all of them are
assembled into data/guide.json, which the web app reads.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import date, datetime, timezone

from backend import agents
from backend.config import CANDIDATES_PATH, DATA_DIR, GUIDE_PATH, SAFETY_LOG_PATH, OUTPUT_DIR
from backend.sources import SourcePolicy, fetch_page, quote_in_text

BUILD_DIR = DATA_DIR / "build"
ISSUES = json.loads((DATA_DIR / "issues.json").read_text(encoding="utf-8"))["issues"]
ISSUE_IDS = [i["id"] for i in ISSUES]
ISSUE_BY_ID = {i["id"]: i for i in ISSUES}
MIN_ISSUES_FOR_OVERALL = 4  # an overall position needs scores on at least this many issues


def load_ballot() -> dict:
    return json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))


def all_candidates(ballot: dict):
    for race in ballot["races"]:
        for cand in race["candidates"]:
            yield race, cand


def log_rejection(candidate_id: str, stage: str, item: dict, reason: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with SAFETY_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "candidate": candidate_id,
                            "stage": stage, "reason": reason, "item": item}, ensure_ascii=False) + "\n")


def code_check(candidate_id: str, policy: SourcePolicy, item: dict, issue_required: bool = True) -> dict | None:
    """Plain-code checks the AI cannot talk its way past. Returns the item with source details, or None."""
    if issue_required and item.get("issue_id") not in ISSUE_IDS:
        log_rejection(candidate_id, "code", item, "unknown issue id")
        return None
    kind = policy.source_type(item.get("url", ""))
    if kind is None:
        log_rejection(candidate_id, "code", item, "source not on an allowed domain")
        return None
    page = fetch_page(item["url"])
    if not page.ok:
        log_rejection(candidate_id, "code", item, f"source page could not be read: {page.error}")
        return None
    if not quote_in_text(item.get("quote", ""), page.text):
        log_rejection(candidate_id, "code", item, "quote not found word-for-word on the source page")
        return None
    return {**item, "source_type": kind, "source_title": page.title, "retrieved_at": page.retrieved_at,
            "archived_copy": page.fetched_from if page.fetched_from != page.url else None}


# --- research ---------------------------------------------------------------------

def _issue_list(ids: list[str]) -> str:
    return "\n".join(f"- {i}: {ISSUE_BY_ID[i]['label']} ({ISSUE_BY_ID[i]['covers']})" for i in ids)


async def research_issues(model, race: dict, cand: dict, issue_ids: list[str], label: str,
                          per_issue: int = 3, known: list[str] | None = None) -> list[dict]:
    policy = SourcePolicy.for_candidate(cand)
    agent = agents.build_researcher(model, policy, "issues")
    deps = agents.ResearchDeps(candidate=cand, policy=policy)
    task = (
        f"Candidate: {cand['name']} ({cand['party']}), running for {race['office']} of {race['state_name']} "
        f"in the November 3, 2026 general election.\n"
        f"Campaign site(s): {', '.join(cand['campaign_domains']) or 'none'}. "
        f"Official site(s): {', '.join(cand['official_domains']) or 'none listed'}.\n\n"
        f"Find the candidate's positions on these issues:\n{_issue_list(issue_ids)}\n\n"
        f"Up to {per_issue} findings per issue; prefer the clearest and most recent. Skip an issue entirely if no allowed page covers it."
    )
    if len(issue_ids) == 1:  # deep, single-issue run: look past the home page
        task += ("\nThis run covers ONE issue, so dig: the campaign's page for this topic, its plan or policy pages, "
                 "press releases and news posts on the campaign site, and official statements on government sites. "
                 "Each finding should add something new (a different proposal, action, or position).")
    if known:
        task += "\nAlready in the guide (do not repeat these):\n" + "\n".join(f"- {k}" for k in known)
    t0 = time.time()
    result = await agent.run(task, deps=deps, usage_limits=agents.USAGE_LIMITS)
    agents.log_usage("researcher", f"{cand['id']}:{label}", result.usage, time.time() - t0,
                     pages_read=len(deps.pages_read))
    return [f.model_dump() for f in result.output.findings]


async def research_profile(model, race: dict, cand: dict, focus: str | None = None) -> dict:
    policy = SourcePolicy.for_candidate(cand)
    agent = agents.build_researcher(model, policy, "profile")
    deps = agents.ResearchDeps(candidate=cand, policy=policy)
    task = (
        f"Candidate: {cand['name']} ({cand['party']}), running for {race['office']} of {race['state_name']}.\n"
        f"Campaign site(s): {', '.join(cand['campaign_domains']) or 'none'}. "
        f"Official site(s): {', '.join(cand['official_domains']) or 'none listed'}.\n\n"
        "Build a short factual profile: date or year of birth (only if a page states it), current job or office, "
        "up to 4 earlier jobs or offices, higher education (degrees and schools after high school), "
        "and 3 priorities the campaign highlights on its home or issues page "
        "(phrase each as 'The campaign highlights ...', without claiming an order). "
        "Every item needs a word-for-word quote and its URL. Leave out anything you cannot quote. "
        "Each fact may say only what its quote says: if the quote says 'mayor' without naming the city, "
        "choose a longer quote that names it, or write just 'Mayor'."
    )
    if focus:
        task += f"\n\nThis run is ONLY about the '{focus}' field; leave every other field empty."
    t0 = time.time()
    result = await agent.run(task, deps=deps, usage_limits=agents.USAGE_LIMITS)
    agents.log_usage("researcher", f"{cand['id']}:profile{':' + focus if focus else ''}", result.usage, time.time() - t0,
                     pages_read=len(deps.pages_read))
    return result.output.model_dump()


# --- verification -------------------------------------------------------------------

async def verify(model, cand: dict, items: list[dict]) -> list[dict]:
    """Independent AI check of items that already passed the code checks."""
    if not items:
        return []
    agent = agents.build_verifier(model)
    lines = []
    for n, it in enumerate(items):
        topic = ISSUE_BY_ID[it["issue_id"]]["label"] if it["issue_id"] in ISSUE_BY_ID else it["issue_id"]
        lines.append(f"[{n}] issue: {topic}\n    claim: {it['claim']}\n    quote: \"{it['quote']}\"\n"
                     f"    source: {it['url']} ({it['source_type']})")
    task = f"Candidate: {cand['name']} ({cand['party']}).\n\n" + "\n".join(lines)
    t0 = time.time()
    result = await agent.run(task, usage_limits=agents.USAGE_LIMITS)
    agents.log_usage("verifier", f"{cand['id']}:verify", result.usage, time.time() - t0, items=len(items))
    verdicts = {v.index: v for v in result.output.verdicts}
    kept = []
    for n, it in enumerate(items):
        v = verdicts.get(n)
        if v is None or v.decision != "accept":
            log_rejection(cand["id"], "verifier", it, v.reason if v else "no verdict returned")
            continue
        if v.neutral_claim:
            it = {**it, "original_claim": it["claim"], "claim": v.neutral_claim}
        kept.append({**it, "verifier_note": v.reason})
    return kept


# --- scoring ------------------------------------------------------------------------

async def score(model, cand: dict, findings: list[dict], only: list[str] | None = None) -> dict[str, dict]:
    """Score every issue that has findings (or just the issues in `only`)."""
    by_issue = {i: [f for f in findings if f["issue_id"] == i] for i in ISSUE_IDS}
    to_score = [i for i in ISSUE_IDS if by_issue[i] and (only is None or i in only)]
    out = {i: {"score": None, "confidence": None, "rationale": "Not enough verified information."} for i in ISSUE_IDS}
    if not to_score:
        return out
    agent = agents.build_scorer(model)
    blocks = []
    for i in to_score:
        anchors = "\n".join(f"      {k}: {v}" for k, v in ISSUE_BY_ID[i]["anchors"].items())
        facts = "\n".join(f"      - {f['claim']} (quote: \"{f['quote']}\")" for f in by_issue[i])
        blocks.append(f"issue_id: {i}\n  rubric:\n{anchors}\n  verified findings:\n{facts}")
    t0 = time.time()
    result = await agent.run("Candidate A.\n\n" + "\n\n".join(blocks), usage_limits=agents.USAGE_LIMITS)
    agents.log_usage("scorer", f"{cand['id']}:score", result.usage, time.time() - t0, issues=len(to_score))
    for s in result.output.scores:
        if s.issue_id in to_score:
            val = None if s.score is None else max(-1.0, min(1.0, round(s.score, 2)))
            out[s.issue_id] = {"score": val, "confidence": s.confidence if val is not None else None,
                               "rationale": s.rationale}
    return out


# --- one candidate --------------------------------------------------------------------

def _profile_items(profile: dict) -> list[dict]:
    items = []
    if profile.get("birth_date") and profile.get("birth_date_quote"):
        items.append({"issue_id": "profile:birth_date", "claim": f"Born {profile['birth_date']}.",
                      "quote": profile["birth_date_quote"], "url": profile.get("birth_date_url") or "",
                      "value": profile["birth_date"]})
    if profile.get("current_role"):
        items.append({"issue_id": "profile:current_role", "claim": profile["current_role"]["text"], **_sq(profile["current_role"])})
    for r in profile.get("previous_roles", [])[:4]:
        items.append({"issue_id": "profile:previous_role", "claim": r["text"], **_sq(r)})
    for e in profile.get("education", [])[:4]:
        items.append({"issue_id": "profile:education", "claim": e["text"], **_sq(e)})
    for p in profile.get("top_policies", [])[:3]:
        items.append({"issue_id": "profile:top_policy", "claim": p["text"], **_sq(p)})
    return items


def _sq(x: dict) -> dict:
    return {"quote": x["quote"], "url": x["url"]}


async def build_candidate(model, race: dict, cand: dict) -> dict:
    policy = SourcePolicy.for_candidate(cand)
    print(f"[{cand['id']}] researching")
    profile_raw, raw = await asyncio.gather(
        research_profile(model, race, cand),
        research_issues(model, race, cand, ISSUE_IDS, "issues"),
    )
    checked = [c for f in raw if (c := code_check(cand["id"], policy, f))]

    missing = [i for i in ISSUE_IDS if not any(f["issue_id"] == i for f in checked)]
    if missing:  # one targeted follow-up search for the issues the first pass did not cover
        print(f"[{cand['id']}] follow-up on {len(missing)} issues")
        more = await research_issues(model, race, cand, missing, "follow-up")
        checked += [c for f in more if f.get("issue_id") in missing and (c := code_check(cand["id"], policy, f))]

    profile_checked = [c for it in _profile_items(profile_raw)
                       if (c := code_check(cand["id"], policy, it, issue_required=False))]
    print(f"[{cand['id']}] verifying {len(checked)} findings + {len(profile_checked)} profile facts")
    verified = await verify(model, cand, checked + profile_checked)
    findings = [f for f in verified if not f["issue_id"].startswith("profile:")]
    profile_ok = [f for f in verified if f["issue_id"].startswith("profile:")]

    print(f"[{cand['id']}] scoring")
    scores = await score(model, cand, findings)
    result = {
        "id": cand["id"],
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profile": profile_ok,
        "findings": findings,
        "scores": scores,
        "stats": {"raw_findings": len(raw) + (len(more) if missing else 0), "passed_code_checks": len(checked),
                  "verified": len(findings), "profile_facts": len(profile_ok)},
    }
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    (BUILD_DIR / f"{cand['id']}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[{cand['id']}] done: {result['stats']}")
    return result


# --- assemble the guide -----------------------------------------------------------------

def _age_on(birth: str, on: date) -> int | None:
    try:
        if len(birth) == 4:
            return None
        b = date.fromisoformat(birth)
        return on.year - b.year - ((on.month, on.day) < (b.month, b.day))
    except ValueError:
        return None


def _voteview(cand: dict) -> dict | None:
    vv = cand.get("voteview")
    if not vv:
        return None
    path = DATA_DIR / "voteview" / f"{vv['chamber'][0]}{vv['congress']}_members.csv"
    if not path.exists():
        return None
    import csv

    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["bioguide_id"] == vv["bioguide_id"] and row["nominate_dim1"]:
                return {**vv, "dim1": float(row["nominate_dim1"]),
                        "source_url": f"https://voteview.com/person/{row['icpsr']}",
                        "data_url": f"https://voteview.com/static/data/out/members/{path.name}"}
    return None


def assemble() -> dict:
    ballot = load_ballot()
    election_day = date.fromisoformat(ballot["election_date"])
    guide = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "election_date": ballot["election_date"], "issues": ISSUES, "races": []}
    for race in ballot["races"]:
        r = {k: v for k, v in race.items() if k != "candidates"}
        r["candidates"] = []
        for cand in race["candidates"]:
            path = BUILD_DIR / f"{cand['id']}.json"
            built = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            scored = [s["score"] for s in (built or {}).get("scores", {}).values() if s["score"] is not None]
            overall = round(sum(scored) / len(scored), 2) if len(scored) >= MIN_ISSUES_FOR_OVERALL else None
            if built:  # stable ids so answers can cite a specific fact
                for n, item in enumerate(built["profile"] + built["findings"], start=1):
                    item["fid"] = f"{cand['id']}-{n}"
            birth = next((p for p in (built or {}).get("profile", []) if p["issue_id"] == "profile:birth_date"), None)
            r["candidates"].append({
                **cand,
                "built": built is not None,
                "built_at": built and built["built_at"],
                "age": _age_on(birth["value"], election_day) if birth else None,
                "profile": built["profile"] if built else [],
                "findings": built["findings"] if built else [],
                "scores": built["scores"] if built else {},
                "overall": {"score": overall, "issues_scored": len(scored)},
                "voteview": _voteview(cand),
            })
        guide["races"].append(r)
    GUIDE_PATH.write_text(json.dumps(guide, indent=2, ensure_ascii=False), encoding="utf-8")
    return guide


async def refresh_issue(model, cand_id: str, issue_id: str) -> dict:
    """Live 'Refresh' in the app: look again for one candidate on one issue.

    New findings must pass the same code checks and verifier; existing verified
    findings are kept, so a refresh can add facts but never silently remove them.
    """
    race, cand = next((r, c) for r, c in all_candidates(load_ballot()) if c["id"] == cand_id)
    policy = SourcePolicy.for_candidate(cand)
    path = BUILD_DIR / f"{cand_id}.json"
    built = json.loads(path.read_text(encoding="utf-8"))
    raw = await research_issues(model, race, cand, [issue_id], f"refresh:{issue_id}")
    known = {f["quote"] for f in built["findings"]}
    checked = [c for f in raw if f.get("issue_id") == issue_id and f.get("quote") not in known
               and (c := code_check(cand_id, policy, f))]
    added = await verify(model, cand, checked)
    built["findings"] += added
    if added:  # re-score only this issue, so other issues' placements stay exactly as they were
        built["scores"][issue_id] = (await score(model, cand, built["findings"], only=[issue_id]))[issue_id]
    built["refreshed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path.write_text(json.dumps(built, indent=2, ensure_ascii=False), encoding="utf-8")
    assemble()
    return {"found": len(raw), "passed_code_checks": len(checked), "added": len(added)}


async def deepen_candidate(model, race: dict, cand: dict, sem: asyncio.Semaphore) -> dict:
    """Deep pass: one Researcher run per issue (up to 5 findings each), then the same code checks,
    Verifier and Scorer. Existing verified findings are kept; new ones are added."""
    policy = SourcePolicy.for_candidate(cand)
    path = BUILD_DIR / f"{cand['id']}.json"
    built = json.loads(path.read_text(encoding="utf-8"))
    before = len(built["findings"])

    async def one(issue_id: str) -> list[dict]:
        known = [f["claim"] for f in built["findings"] if f["issue_id"] == issue_id]
        async with sem:
            try:
                return await research_issues(model, race, cand, [issue_id], f"deep:{issue_id}", per_issue=5, known=known)
            except Exception as exc:  # one issue failing must not stop the rest
                print(f"[{cand['id']}] deep:{issue_id} failed: {type(exc).__name__}")
                return []

    raw = [f for batch in await asyncio.gather(*(one(i) for i in ISSUE_IDS)) for f in batch]
    seen = {f["quote"] for f in built["findings"]}
    checked = []
    for f in raw:
        if f.get("quote") in seen:
            continue
        if (c := code_check(cand["id"], policy, f)):
            checked.append(c)
            seen.add(c["quote"])
    added = await verify(model, cand, checked)
    built["findings"] += added
    built["scores"] = await score(model, cand, built["findings"])
    built["deepened_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    built.setdefault("stats", {})["deep_pass"] = {"found": len(raw), "passed_code_checks": len(checked),
                                                  "added": len(added), "before": before, "after": len(built["findings"])}
    path.write_text(json.dumps(built, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[{cand['id']}] deep pass: {built['stats']['deep_pass']}")
    return built["stats"]["deep_pass"]


async def edit_candidate(model, cand: dict) -> dict:
    """Editor pass: rewrite summaries in the house style, then have the Verifier re-check each rewrite
    against its quote. A rewrite that fails the check is dropped and the original wording stays."""
    path = BUILD_DIR / f"{cand['id']}.json"
    built = json.loads(path.read_text(encoding="utf-8"))
    items = [f for f in built["findings"] + built["profile"]
             if f["issue_id"] not in ("profile:birth_date",)]
    if not items:
        return {"edited": 0, "kept_original": 0}
    editor = agents.build_editor(model)
    t0 = time.time()
    result = await editor.run("\n".join(f"[{n}] {it['claim']}" for n, it in enumerate(items)), usage_limits=agents.USAGE_LIMITS)
    agents.log_usage("editor", f"{cand['id']}:edit", result.usage, time.time() - t0, items=len(items))
    proposals = {e.index: e.claim.strip() for e in result.output.edits
                 if 0 <= e.index < len(items) and e.claim.strip() and e.claim.strip() != items[e.index]["claim"]}
    candidates = [{**items[n], "claim": c, "_n": n} for n, c in proposals.items()]
    accepted = await verify(model, cand, candidates) if candidates else []
    for a in accepted:
        it = items[a["_n"]]
        it.setdefault("original_claim", it["claim"])
        it["claim"] = a.get("claim")
    path.write_text(json.dumps(built, indent=2, ensure_ascii=False), encoding="utf-8")
    stats = {"edited": len(accepted), "kept_original": len(items) - len(accepted)}
    print(f"[{cand['id']}] editor: {stats}")
    return stats


async def refresh_profile(model, cand_id: str, field: str | None = None) -> None:
    """Re-run the profile research for one candidate; new verified facts are added, none removed.

    field: keep only one kind of fact (e.g. 'education'), so a re-run cannot add near-duplicates of others.
    """
    race, cand = next((r, c) for r, c in all_candidates(load_ballot()) if c["id"] == cand_id)
    policy = SourcePolicy.for_candidate(cand)
    path = BUILD_DIR / f"{cand_id}.json"
    built = json.loads(path.read_text(encoding="utf-8"))
    known = {p["quote"] for p in built["profile"]}
    raw = _profile_items(await research_profile(model, race, cand, focus=field))
    if field:
        raw = [it for it in raw if it["issue_id"] == f"profile:{field}"]
    checked = [c for it in raw if it["quote"] not in known and (c := code_check(cand_id, policy, it, issue_required=False))]
    added = await verify(model, cand, checked)
    built["profile"] += added
    path.write_text(json.dumps(built, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[{cand_id}] profile: {len(raw)} found, {len(checked)} passed code checks, {len(added)} added")
    assemble()


async def rescore(only: str | None) -> None:
    """Re-run only the scorer on saved findings (after a rubric or scorer change)."""
    model = agents.build_model()
    for _, cand in all_candidates(load_ballot()):
        path = BUILD_DIR / f"{cand['id']}.json"
        if only not in (None, cand["id"]) or not path.exists():
            continue
        built = json.loads(path.read_text(encoding="utf-8"))
        built["scores"] = await score(model, cand, built["findings"])
        path.write_text(json.dumps(built, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[{cand['id']}] rescored")
    assemble()


async def main(only: str | None, concurrency: int) -> None:
    model = agents.build_model()
    ballot = load_ballot()
    jobs = [(race, cand) for race, cand in all_candidates(ballot) if only in (None, cand["id"])]
    sem = asyncio.Semaphore(concurrency)

    async def run(race, cand):
        async with sem:
            try:
                await build_candidate(model, race, cand)
            except Exception as exc:  # one candidate failing must not stop the others
                print(f"[{cand['id']}] FAILED: {type(exc).__name__}: {exc}")

    await asyncio.gather(*(run(r, c) for r, c in jobs))
    assemble()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate")
    ap.add_argument("--assemble", action="store_true")
    ap.add_argument("--rescore", action="store_true")
    ap.add_argument("--edit", action="store_true", help="Editor pass: rewrite summaries in house style (Verifier re-checks)")
    ap.add_argument("--deep", action="store_true", help="deep pass: one research run per issue (all, or --candidate)")
    ap.add_argument("--profile", action="store_true", help="re-run profile research (all, or --candidate)")
    ap.add_argument("--field", help="with --profile: only this profile field, e.g. education")
    ap.add_argument("--concurrency", type=int, default=3)
    args = ap.parse_args()
    if args.assemble:
        assemble()
    elif args.rescore:
        asyncio.run(rescore(args.candidate))
    elif args.deep:
        async def _deep():
            model = agents.build_model()
            sem = asyncio.Semaphore(args.concurrency)
            jobs = [(r, c) for r, c in all_candidates(load_ballot()) if args.candidate in (None, c["id"])]
            results = await asyncio.gather(*(deepen_candidate(model, r, c, sem) for r, c in jobs))
            summary = {c["id"]: s for (_, c), s in zip(jobs, results)}
            (OUTPUT_DIR / "deep_pass_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
            assemble()
        asyncio.run(_deep())
    elif args.edit:
        async def _edit():
            model = agents.build_model()
            jobs = [c for _, c in all_candidates(load_ballot()) if args.candidate in (None, c["id"])]
            await asyncio.gather(*(edit_candidate(model, c) for c in jobs))
            assemble()
        asyncio.run(_edit())
    elif args.profile:
        async def _profiles():
            model = agents.build_model()
            ids = [c["id"] for _, c in all_candidates(load_ballot()) if args.candidate in (None, c["id"])]
            await asyncio.gather(*(refresh_profile(model, i, args.field) for i in ids))
        asyncio.run(_profiles())
    else:
        asyncio.run(main(args.candidate, args.concurrency))
