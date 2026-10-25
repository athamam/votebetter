# VoteBetter: Know where they stand (NY · NJ · CT, 2026)

A nonpartisan, source-checked guide to the November 3, 2026 statewide races in New York (Governor), New Jersey (U.S. Senate) and Connecticut (Governor). AI agents research each candidate on allowed sources only, every statement is checked word for word against its source page, and nothing is shown that cannot be traced.

> **Disclaimer.** Independent student project for MGT 409 at the Yale School of Management. Not affiliated with or endorsed by Yale University, the Yale School of Management, or any candidate, campaign, or party. It does not recommend any candidate or party. Spectrum positions are AI estimates and are not verified by the candidates.

---

## Run it (about 5 minutes)

You need **Python 3.11 or newer** (tested on 3.14). No Node.js, database, or other services.

**1. Get the code**

```bash
git clone <this-repo-url> midterm-guide
cd midterm-guide
```

**2. Create a virtual environment and install**

Windows (PowerShell):

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**3. Add your key**

Copy `.env.example` to `.env` and paste your key after `PORTKEY_API_KEY=`. The app looks for `.env` **in this folder first, then in the folder one level up**, so a `.env` placed next to the cloned folder also works.

**4. Start the app**

```bash
python app.py
```

Open **http://127.0.0.1:8000**. Stop it with `Ctrl+C`. (Auto-reload is off, so only one server process ever runs.)

**Without a key** the full guide still works (all candidates, issues, spectrums, and sources). Only the two live AI features, *Ask a question* and *Search again*, are switched off, and the page says so.

---

## What to try

1. **Home → pick a state → pick the race.** The race opens on **Issues**: *"What is important to you?"* with 12 issues.
2. Pick an issue: a mini spectrum and each candidate's verified statements, side by side. *Search again* sends the Researcher agent to look for new statements (about 30–60 seconds).
3. Click **View sources** to see each exact quote, the page it came from, and when it was checked.
4. **Candidates** tab: the overall spectrum and each candidate's profile (party, roles, education, priorities).
5. **Ask a question** tab, or the floating *Ask about this race* button: try *"How do the candidates differ on taxes?"*, then *"Who should I vote for?"* to see the refusal.
5. **How it works** page: the agents, source rules, and the full spectrum rubric.

---

## How it works

```
official ballot lists ─► candidates.json
                              │
      ┌───────────────────────┴────────────────────────┐
      ▼                                                │
 Researcher agent ── web search (allowed domains only) │
      │            └─ read_source (allow-list enforced) │
      ▼                                                │
 Code check: page readable? domain allowed? quote word-for-word on page?
      ▼
 Verifier agent: candidate's own position? summary adds nothing? neutral wording?
      ▼
 Scorer agent: fixed rubric, -1.0 (left) … +1.0 (right), verified findings only
      ▼
 data/guide.json ──► web app (FastAPI + plain HTML/JS)
                        ├─ Ask agent (answers only from verified facts, cites each)
                        └─ Search again (one candidate × one issue, same checks)
```

| Agent | Job | Tools |
|---|---|---|
| Researcher | Finds statements and copies exact quotes | Web search limited to allowed domains; `read_source` (refuses non-allowed sites) |
| Verifier | Independent check of each quote and summary | None (reads only the item) |
| Scorer | Places a candidate on each issue's scale | None (rubric + verified findings only) |
| Ask | Answers voter questions from verified facts | None (no web access) |

All agents use **gpt-6-luna** through Portkey (`PORTKEY_API_KEY`).

**Sources allowed:** candidates' own campaign sites, official government sites (`.gov`), and AP/Reuters for a candidate's own reported words. **Never:** Wikipedia, Ballotpedia, other summary sites, or social media. When an official site blocks automated readers, the quote is checked against the Internet Archive copy, and the source note says so.

## Guardrails

- Per run: caps on model requests, tool calls, web searches, and tokens (`backend/config.py`).
- Live features: 5 per browser session, 15 per network, 200 per day site-wide (`backend/guardrails.py`). Browsing is unlimited.
- Prompt injection: page text is passed as tagged, untrusted data; user questions are treated as questions only.
- Output checks in plain code: answers with voting recommendations or with no valid citations are blocked before display.
- Every rejected claim and every blocked request is logged to `output/safety_log.jsonl`. Every agent run's tokens are logged to `output/token_log.jsonl`.

Test the guardrails against a running app (uses about 10 live requests):

```bash
python tests/test_guardrails_live.py http://127.0.0.1:8000
```

## Rebuilding the data (optional, uses the API)

The repo ships with verified data, so you do not need this to run the app.

```bash
python -m backend.pipeline                      # all 8 candidates (about 10 minutes)
python -m backend.pipeline --candidate fazio    # one candidate
python -m backend.pipeline --assemble           # rebuild data/guide.json from saved results, no AI
```

## Project layout

```
app.py                  start the server
backend/config.py       model, limits, paths, .env lookup
backend/agents.py       Researcher, Verifier, Scorer
backend/ask.py          Ask agent + citation and recommendation checks
backend/pipeline.py     research -> code check -> verify -> score -> guide.json
backend/sources.py      allowed domains, page fetching, word-for-word quote check
backend/guardrails.py   spending caps, input limits, output checks
backend/contacts.py     official contact links (campaign's own site + NJ official list), plain code, no AI
backend/main.py         FastAPI routes
frontend/               index.html, styles.css, app.js (no build step)
data/candidates.json    official ballot list with sources
data/issues.json        the 12 issues and the spectrum rubric
data/guide.json         verified output the app reads
data/voteview/          Voteview DW-NOMINATE member files (voteview.com)
output/                 token and safety logs
```

**Credits.** Typeface: [Public Sans](https://github.com/uswds/public-sans) by the U.S. Web Design System, self-hosted under the SIL Open Font License (`frontend/fonts/OFL.txt`). Flags and candidate photos: public-domain files, credited in the app. Icons and logo: drawn for this project.

Full-text copies of source pages are kept locally for re-checking and are not committed, so this repo does not republish anyone's content. Only short quotes with links appear in the app.
