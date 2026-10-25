/* VoteBetter — single-page front end (no build step).
   All data comes from /api/guide; every piece of page text from the web is escaped before display. */

const ELECTION = new Date("2026-11-03T00:00:00-05:00");
const VOTE_GOV = { NY: "https://vote.gov/register/new-york", NJ: "https://vote.gov/register/new-jersey", CT: "https://vote.gov/register/connecticut" };
const SOURCE_TYPES = { campaign: "Candidate's campaign website", official: "Official government website", secondary: "News wire (AP / Reuters)" };
const OTHER_COLORS = ["var(--c3)", "var(--c4)"];  // parties other than Democratic and Republican
const USAGOV = "https://www.usa.gov/midterm-elections";
const flag = (code, cls = "flag") => `<img class="${cls}" src="/static/flags/${code}.svg" alt="Flag of ${esc(STATE_NAMES[code])}">`;
const STATE_NAMES = { NY: "New York", NJ: "New Jersey", CT: "Connecticut" };

/* Party symbols: simple generic donkey and elephant drawn here (not the parties' trademarked logos). */
const DONKEY = `<svg viewBox="0 0 64 48" aria-hidden="true"><g fill="currentColor">
  <ellipse cx="27" cy="27" rx="16" ry="9.5"/>
  <path d="M36 21 Q40 12 45 10 L50 13 Q46 20 43 29 Z"/>
  <path d="M44 9 Q50 6 54 10 L61 19 Q63 23 59 25 Q56 26 53 23 L46 16 Z"/>
  <ellipse cx="45.5" cy="3.5" rx="2.6" ry="7" transform="rotate(-18 45.5 3.5)"/>
  <ellipse cx="50" cy="3.5" rx="2.6" ry="7" transform="rotate(14 50 3.5)"/>
  <rect x="14" y="32" width="4.5" height="14" rx="2"/><rect x="21" y="33" width="4.5" height="13" rx="2"/>
  <rect x="31" y="33" width="4.5" height="13" rx="2"/><rect x="37.5" y="32" width="4.5" height="14" rx="2"/>
  <path d="M12 24 Q6 27 6 35 L8 35 Q8.5 29 13 27 Z"/><ellipse cx="7" cy="37" rx="2.4" ry="3.2"/></g></svg>`;
const ELEPHANT = `<svg viewBox="0 0 64 48" aria-hidden="true"><g fill="currentColor">
  <path d="M10 30 Q10 12 30 12 Q46 12 48 24 L48 34 L10 34 Z"/><circle cx="48" cy="22" r="10"/>
  <path d="M55 26 Q60 34 56 44 L52 44 Q55 35 50 30 Z"/><path d="M42 16 Q36 22 41 30 L46 28 Z" opacity=".55"/>
  <rect x="12" y="32" width="6" height="13" rx="2"/><rect x="21" y="32" width="6" height="13" rx="2"/>
  <rect x="31" y="32" width="6" height="13" rx="2"/><rect x="40" y="32" width="6" height="13" rx="2"/>
  <path d="M10 22 Q4 24 5 32 L7 32 Q7 26 11 25 Z"/></g></svg>`;
/* Issue icons: simple line drawings made for this guide (24x24, drawn in the current text color). */
const ISSUE_ICONS = {
  abortion: `<rect x="5" y="4" width="14" height="17" rx="2"/><rect x="9" y="2.5" width="6" height="3" rx="1"/><path d="M12 10v6M9 13h6"/>`,
  climate: `<path d="M5 19c0-8 5-14 14-14 0 9-6 14-14 14z"/><path d="M5 19l8-8"/>`,
  crime: `<path d="M12 4v16M8 20h8M5 7h14"/><path d="M5 7l-2.5 6h5zM19 7l-2.5 6h5z"/>`,
  economy: `<circle cx="12" cy="12" r="9"/><path d="M15 9.5c-.5-1.2-1.7-2-3-2-1.7 0-3 1-3 2.3 0 3.2 6 1.7 6 4.9 0 1.3-1.3 2.3-3 2.3-1.4 0-2.6-.8-3-2M12 6v12"/>`,
  education: `<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c0 1.5 3 3 6 3s6-1.5 6-3v-5M22 9v6"/>`,
  guns: `<path d="M3 7h17v4H3z"/><path d="M6 11h4l-1.5 8h-4zM10 11c0 2 1 3 3 3h1v-3"/>`,
  healthcare: `<path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z"/><path d="M7.5 12h2l1.5-2.5 2 5 1.5-2.5h2"/>`,
  housing: `<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10M10 20v-6h4v6"/>`,
  immigration: `<rect x="5" y="3" width="14" height="18" rx="2"/><circle cx="12" cy="10" r="3"/><path d="M9 16h6"/>`,
  foreign_policy: `<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>`,
  lgbtq: `<path d="M3 18a9 9 0 0 1 18 0M6.5 18a5.5 5.5 0 0 1 11 0M10 18a2 2 0 0 1 4 0"/>`,
  womens_childrens: `<circle cx="9" cy="5" r="2.5"/><path d="M5 21v-6a4 4 0 0 1 8 0v6"/><circle cx="17" cy="10" r="2"/><path d="M14.5 21v-4a2.5 2.5 0 0 1 5 0v4"/>`,
};
const issueIcon = (id) => `<svg class="issue-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
  stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ISSUE_ICONS[id] || ""}</svg>`;

function partyIcon(party) {
  if (party === "Democratic") return `<span class="party-icon" style="color:var(--dem)" title="Democratic Party (donkey symbol)">${DONKEY}</span>`;
  if (party === "Republican") return `<span class="party-icon" style="color:var(--rep)" title="Republican Party (elephant symbol)">${ELEPHANT}</span>`;
  return "";
}
const SENATE_CLASS2 = "https://www.senate.gov/senators/Class_II.htm";

const app = document.getElementById("app");
let GUIDE = null, STATUS = null, FACTS = {};
const SESSION = localStorage.getItem("mcg-session") || (() => {
  const id = crypto.randomUUID(); localStorage.setItem("mcg-session", id); return id; })();

/* ---------- helpers ---------- */
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
const initials = (name) => name.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
const lastName = (name) => name.trim().split(/\s+/).pop();
const issueLabel = (id) => (GUIDE.issues.find((i) => i.id === id) || {}).label || id;
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }) : "");

async function api(path, body) {
  const res = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json", "x-session-id": SESSION },
    body: JSON.stringify(body) } : { headers: { "x-session-id": SESSION } });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.error || `Request failed (${res.status})`), { data });
  return data;
}

// Democrats first, then Republicans, then other parties; alphabetical within a group.
const PARTY_RANK = { Democratic: 0, Republican: 1 };
const partyRank = (c) => PARTY_RANK[c.party] ?? 2;
function sortedCandidates(race) {
  let other = 0;
  return [...race.candidates]
    .sort((a, b) => partyRank(a) - partyRank(b) || lastName(a.name).localeCompare(lastName(b.name)))
    .map((c) => ({ ...c, color: c.party === "Democratic" ? "var(--dem)" : c.party === "Republican" ? "var(--rep)"
      : OTHER_COLORS[other++ % OTHER_COLORS.length] }));
}

/* Sources: each section numbers its facts with small footnote markers, and one
   "View sources" button at the bottom opens the full list for that section. */
let SOURCE_SETS = {};
function notes(title) {
  const id = `s${Object.keys(SOURCE_SETS).length}`;
  const facts = [];
  SOURCE_SETS[id] = { title, facts };
  return {
    cite(fact) {
      if (!fact) return "";
      let n = facts.indexOf(fact) + 1;
      if (!n) { facts.push(fact); n = facts.length; }
      return `<sup class="fn">${n}</sup>`;
    },
    button() {
      return facts.length ? `<button class="btn btn-sources" data-sources="${id}">View sources (${facts.length})</button>` : "";
    },
  };
}

/* ---------- countdown + how-to-vote ---------- */
function tickCountdown() {
  const el = document.getElementById("countdown");
  const ms = ELECTION - new Date();
  if (ms <= 0) {
    const sameDay = ms > -24 * 3600 * 1000;
    el.innerHTML = sameDay ? "<b>Today is Election Day</b>" : "Election Day was <b>Nov 3, 2026</b>";
    return;
  }
  const d = Math.floor(ms / 864e5), h = Math.floor((ms % 864e5) / 36e5), m = Math.floor((ms % 36e5) / 6e4);
  el.innerHTML = `Election Day · Nov 3, 2026<br><b>${d}d ${h}h ${m}m</b> to go`;
}
function setVoteLink(state) {
  document.getElementById("how-to-vote").href = VOTE_GOV[state] || "https://vote.gov/";
}

/* ---------- spectrum ---------- */
function spectrum(points, { mini = false } = {}) {
  const pos = (x) => `${((x + 1) / 2) * 100}%`;
  const ticks = [-1, -0.5, 0, 0.5, 1].map((t) => `<span class="tick" style="left:${pos(t)}"></span>`).join("");
  // Voting-record rings get their own lane under the line; within a lane, nudge markers apart so none overlap.
  const placed = { ai: [], vv: [] };
  const marks = points.map((p) => {
    const lane = p.vv ? placed.vv : placed.ai;
    let x = p.x; const near = lane.filter((q) => Math.abs(q - x) < 0.09).length; lane.push(x);
    const offset = near ? (near % 2 ? 1 : -1) * Math.ceil(near / 2) * 0.09 : 0;
    x = Math.max(-1, Math.min(1, x + offset));
    return p.vv
      ? `<span class="marker vv" style="left:${pos(x)};border-color:${p.color}" title="${esc(p.title)}">${esc(p.label)}</span>`
      : `<span class="marker" style="left:${pos(x)};background:${p.color}" title="${esc(p.title)}">${esc(p.label)}</span>`;
  }).join("");
  const hasVV = points.some((p) => p.vv);
  return `<div class="spectrum${mini ? " mini" : ""}${hasVV ? " has-vv" : ""}" role="img" aria-label="${esc(points.map((p) => `${p.title}`).join("; ") || "No positions estimated")}">
    <div class="track"></div>${ticks}${marks}
    <div class="labels"><span>Left</span><span>Center</span><span>Right</span></div></div>`;
}

/* ---------- sources dialog ---------- */
function sourceEntry(f, n) {
  const archived = f.archived_copy ? `<br><span class="small">Live page blocks automated readers; checked against the
    <a href="${esc(safeUrl(f.archived_copy))}" target="_blank" rel="noopener noreferrer">Internet Archive copy ↗</a>.</span>` : "";
  return `<li class="source-item">
    <div class="source-num">${n}</div>
    <div>
      <p style="margin:0"><b>${esc(f.claim)}</b> <span class="pill">${esc(SOURCE_TYPES[f.source_type] || "Source")}</span></p>
      <blockquote>“${esc(f.quote)}”</blockquote>
      <a class="src" href="${esc(safeUrl(f.url))}" target="_blank" rel="noopener noreferrer">${esc(f.source_title || f.url)} ↗</a>
      <span class="small muted">· retrieved ${esc(fmtDate(f.retrieved_at))}</span>${archived}
    </div></li>`;
}
function openSources(id) {
  const set = SOURCE_SETS[id]; if (!set) return;
  document.getElementById("source-body").innerHTML = `
    <h3 id="source-title">Sources · ${esc(set.title)}</h3>
    <p class="small muted">Each quote was confirmed word for word on its page by code, then checked by the Verifier agent.
    Numbers match the small markers in the text.</p>
    <ol class="source-list">${set.facts.map((f, i) => sourceEntry(f, i + 1)).join("")}</ol>`;
  document.getElementById("source-dialog").showModal();
}
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-sources]"); if (b) { e.preventDefault(); openSources(b.dataset.sources); }
});

/* ---------- pages ---------- */
function renderHome() {
  setVoteLink(null);
  const states = [
    ["NY", "New York", "Governor"], ["NJ", "New Jersey", "U.S. Senate"], ["CT", "Connecticut", "Governor"]];
  app.innerHTML = `
  <section class="hero">
    <div>
      <span class="pill">Nonpartisan · Every fact sourced</span>
      <h1 style="margin-top:12px">Vote for What Matters to You</h1>
      <p class="lead">This guide puts the candidates on your November ballot side by side across 12 issues. AI agents read
      the candidates' own websites and official government pages, and every statement is checked word for word against its
      source before it appears here. We do not give you recommendations, we help you make a more informed decision.</p>
      <p><a class="btn" href="#/methodology">How it works</a></p>
    </div>
    <div class="card">
      <h2>What are the midterms?</h2>
      <ul class="facts">
        <li>Midterm elections take place halfway between presidential elections. The next midterms are in November 2026.<span class="cite"><a href="${USAGOV}" target="_blank" rel="noopener noreferrer">[USA.gov]</a></span></li>
        <li>All 435 seats in the U.S. House and one-third of the Senate are up for election.<span class="cite"><a href="${USAGOV}" target="_blank" rel="noopener noreferrer">[USA.gov]</a></span></li>
        <li>Congressional elections decide which party holds the majority in each chamber for the next two years.<span class="cite"><a href="${USAGOV}" target="_blank" rel="noopener noreferrer">[USA.gov]</a></span></li>
        <li><b>Election Day is Tuesday, November 3, 2026.</b> This guide covers the statewide races in New York, New Jersey and Connecticut.</li>
      </ul>
    </div>
  </section>
  <div class="start-row"><span class="begin-tag">Begin here →</span><h2 id="start">Choose your state</h2></div>
  <p class="muted">Pick the state where you are registered to vote.</p>
  <div class="steps">
    ${states.map(([code, name, race]) => `
      <a class="card step-card" href="#/state/${code}">
        <div class="state-row">${flag(code)}<div class="state-code">${code}</div></div><h3>${name}</h3>
        <p class="muted small" style="margin:0">Statewide race in this guide: ${race}</p></a>`).join("")}
  </div>`;
}

function renderState(code) {
  setVoteLink(code);
  const races = GUIDE.races.filter((r) => r.state === code);
  if (!races.length) return renderNotFound();
  const name = races[0].state_name;
  const offices = ["Governor", "U.S. Senate"];
  const reasons = {
    "U.S. Senate": `Neither of ${esc(name)}'s U.S. Senate seats is up in 2026 (only Class II seats are).<span class="cite"><a href="${SENATE_CLASS2}" target="_blank" rel="noopener noreferrer">[Senate.gov]</a></span>`,
    Governor: `${esc(name)} does not elect a governor on November 3, 2026.<span class="cite"><a href="${esc(safeUrl(races[0].ballot_source.url))}" target="_blank" rel="noopener noreferrer">[official ballot list]</a></span>`,
  };
  app.innerHTML = `
    <h1 class="title-flag">${flag(code, "flag flag-lg")}${esc(name)}</h1>
    <p class="muted">Which race do you want to look into?</p>
    <div class="steps steps-2">
      ${offices.map((office) => {
        const race = races.find((r) => r.office === office);
        return race ? `
          <a class="card step-card" href="#/race/${race.id}">
            <span class="pill">On your ballot</span>
            <h3 style="margin-top:10px">${office}</h3>
            <p class="muted small">${race.candidates.length} candidates on the official ballot</p></a>` : `
          <div class="card race-off" aria-disabled="true"><span class="pill pill-off">⊘ Not available</span>
            <h3 style="margin-top:10px">${office}</h3><p class="small">${reasons[office]}</p></div>`;
      }).join("")}
    </div>`;
}

function overallPoints(cands) {
  const pts = [];
  cands.forEach((c) => {
    if (c.overall.score !== null) pts.push({ x: c.overall.score, color: c.color, label: initials(c.name),
      title: `${c.name}: AI estimate ${c.overall.score.toFixed(2)} from ${c.overall.issues_scored} issues` });
    if (c.voteview) pts.push({ x: c.voteview.dim1, color: c.color, label: initials(c.name), vv: true,
      title: `${c.name}: congressional voting-record score (Voteview DW-NOMINATE) ${c.voteview.dim1}` });
  });
  return pts;
}

function profileBlock(c, n) {
  const by = (k) => c.profile.filter((p) => p.issue_id === k);
  const line = (p) => `${esc(p.claim)}${n.cite(p)}`;
  const list = (arr) => (arr.length ? `<ul>${arr.map((p) => `<li>${line(p)}</li>`).join("")}</ul>` : `<span class="nodata">Not found in official sources.</span>`);
  const birth = by("profile:birth_date")[0];
  const age = c.age !== null && c.age !== undefined ? `${c.age} on Election Day${n.cite(birth)}` : birth ? line(birth) : "";
  return `
    <dl>
      <div><dt>Party</dt><dd>${esc(c.party)}</dd></div>
      ${c.running_mate ? `<div><dt>Running mate (Lt. Governor)</dt><dd>${esc(c.running_mate)}</dd></div>` : ""}
      ${age ? `<div><dt>Age</dt><dd>${age}</dd></div>` : ""}
      <div><dt>Current role</dt><dd>${by("profile:current_role").length ? line(by("profile:current_role")[0]) : `<span class="nodata">Not found in official sources.</span>`}</dd></div>
      <div><dt>Previous roles</dt><dd>${list(by("profile:previous_role"))}</dd></div>
      <div><dt>Higher education</dt><dd>${list(by("profile:education"))}</dd></div>
      <div><dt>Campaign priorities</dt><dd>${list(by("profile:top_policy"))}</dd></div>
      <div><dt>Contact the campaign</dt><dd>${contactBlock(c)}</dd></div>
    </dl>`;
}

// Contact links come only from the campaign's own website or the state's official candidate list (backend/contacts.py).
function contactBlock(c) {
  const k = c.contact || {};
  const ext = (url, text) => `<a href="${esc(safeUrl(url))}" target="_blank" rel="noopener noreferrer">${esc(text)} ↗</a>`;
  const rows = [];
  if (k.website) rows.push(`<li><span class="ck">Website</span>${ext(k.website, new URL(k.website).hostname.replace(/^www\./, ""))}</li>`);
  if (k.contact_page) rows.push(`<li><span class="ck">Contact form</span>${ext(k.contact_page, "Open")}</li>`);
  const email = k.email || k.official_email;
  if (email) rows.push(`<li><span class="ck">Email</span><a href="mailto:${esc(email)}">${esc(email)}</a></li>`);
  const social = Object.entries(k.social || {});
  if (social.length) rows.push(`<li><span class="ck">Social</span><span class="social">${social.map(([name, url]) => ext(url, name)).join(" · ")}</span></li>`);
  if (!rows.length) return `<span class="nodata">No official contact information found.</span>`;
  const fromState = k.official_email && !k.email;
  const notes = [];
  if (k.website || (k.email && !fromState) || social.length) notes.push("Links published on the candidate's own campaign website.");
  if (fromState) notes.push(`Email from the <a href="${esc(safeUrl(k.official_email_source))}" target="_blank" rel="noopener noreferrer">NJ official candidate list ↗</a>.`);
  const src = notes.join(" ");
  return `<ul class="contact-list">${rows.join("")}</ul><p class="small muted" style="margin:6px 0 0">${src}</p>`;
}

// Columns for candidate grids: never leave one card alone on a row (4 candidates -> 2x2).
const gridCols = (n) => (n === 4 ? 2 : Math.min(n, 3));

// Photos only where the image is a U.S. federal government work (public domain); otherwise initials.
function avatar(c) {
  return c.photo
    ? `<img class="avatar avatar-photo" src="/static/photos/${esc(c.photo.file)}" alt="${esc(c.name)}" style="border-color:${c.color}">`
    : `<div class="avatar" style="background:${c.color}" aria-hidden="true">${initials(c.name)}</div>`;
}

function candidateCard(c, race) {
  const empty = !c.profile.length && !c.findings.length;
  const n = notes(c.name);
  const profile = profileBlock(c, n);
  return `<article class="card cand">
    <div class="cand-top">
      ${avatar(c)}
      <div><h3 style="margin:0" class="name-row">${esc(c.name)}${partyIcon(c.party)}</h3>
        ${c.incumbent ? `<span class="pill">Incumbent</span>` : `<span class="pill">Challenger</span>`}</div>
    </div>
    ${empty ? `<p class="warn">No verified information yet. ${esc(c.campaign_domains_note || "")}
      The guide only shows facts it can confirm word for word on an allowed source, so nothing is shown rather than guessing.</p>` : ""}
    ${profile}
    <div style="margin-top:14px">${n.button()}</div>
    ${c.photo ? `<p class="small muted photo-credit">Photo: ${esc(c.photo.credit)} · ${esc(c.photo.license)} ·
      <a href="${esc(safeUrl(c.photo.source_url))}" target="_blank" rel="noopener noreferrer">file ↗</a></p>` : ""}
    <p class="small muted" style="margin-top:12px">On the ballot per <a href="${esc(safeUrl(race.ballot_source.url))}" target="_blank" rel="noopener noreferrer">${esc(race.ballot_source.title.split(" - ")[0])} ↗</a></p>
  </article>`;
}

function renderRace(id, tab = "issues", issueId = null) {  // races open on Issues, the guide's main feature
  const race = GUIDE.races.find((r) => r.id === id);
  if (!race) return renderNotFound();
  setVoteLink(race.state);
  SOURCE_SETS = {};
  setChatRace(race);
  const cands = sortedCandidates(race);
  const pts = overallPoints(cands);
  const unplaced = cands.filter((c) => c.overall.score === null);
  const tabs = [["issues", "Issues"], ["overview", "Candidates"], ["ask", "Ask a question"]];
  let body = "";

  if (tab === "overview") {
    body = `
    <section class="card">
      <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:baseline">
        <h2 style="margin:0">Overall political spectrum</h2><span class="ai-label">AI estimate · not verified by the candidates</span>
      </div>
      ${spectrum(pts)}
      <div class="legend">
        ${cands.map((c) => `<span><span class="dot" style="background:${c.color}"></span>${esc(c.name)} <span class="muted">(${esc(c.party)})</span></span>`).join("")}
        ${cands.some((c) => c.voteview) ? `<span><span class="dot ring"></span>Dashed ring = congressional voting record (Voteview), shown for comparison</span>` : ""}
      </div>
      ${unplaced.length ? `<p class="small muted" style="margin-top:12px">Not placed: ${unplaced.map((c) => `${esc(c.name)} (${c.overall.issues_scored} of 12 issues scored; at least 4 needed)`).join(", ")}.</p>` : ""}
      <p class="warn" style="margin-top:14px"><b>This line is a visualization, estimated by AI.</b> It averages the AI's issue-by-issue
      placements, which are based only on the verified statements in this guide. The candidates have not reviewed or confirmed it.
      <a href="#/methodology">How positions are estimated</a>.</p>
    </section>
    <h2 style="margin-top:28px">Candidates <span class="small muted">(Democrats, then Republicans, then other parties; this order follows party labels, not the spectrum)</span></h2>
    <div class="cands" style="--cols:${gridCols(cands.length)}">${cands.map((c) => candidateCard(c, race)).join("")}</div>`;
  }

  if (tab === "issues") {
    const issues = GUIDE.issues;
    const current = issueId && issues.some((i) => i.id === issueId) ? issueId : null;
    const counts = Object.fromEntries(issues.map((i) => [i.id, cands.filter((c) => c.findings.some((f) => f.issue_id === i.id)).length]));
    const tiles = `
    <div class="issue-grid${current ? " compact" : ""}" role="tablist" aria-label="Issues">
      ${issues.map((i) => `<button role="tab" data-issue="${i.id}" class="issue-tile${i.id === current ? " active" : ""}"
        aria-selected="${i.id === current}" title="Covers: ${esc(i.covers)}">
        <span class="tile-icon">${issueIcon(i.id)}</span>
        <span class="tile-label">${esc(i.label)}</span>
        <span class="tile-count">Verified info on ${counts[i.id]}/${cands.length} candidates</span></button>`).join("")}
    </div>`;
    if (!current) {
      body = `<div class="issues-intro"><h2>What is important to you?</h2>
        <p class="muted">Pick an issue to see where each candidate stands, in their own words.</p></div>${tiles}`;
    } else {
    const issue = issues.find((i) => i.id === current);
    const n = notes(`${race.state_name} ${race.office} · ${issue.label}`);
    const points = cands.filter((c) => c.scores[current]?.score !== null && c.scores[current]?.score !== undefined)
      .map((c) => ({ x: c.scores[current].score, color: c.color, label: initials(c.name),
        title: `${c.name}: AI estimate ${c.scores[current].score} (${c.scores[current].confidence} confidence)` }));
    body = `${tiles}
    <section class="card issue-panel" aria-labelledby="issue-title">
      <button class="panel-close" data-close-issue aria-label="Close and go back to all issues">✕</button>
      <h2 id="issue-title" class="panel-title"><span class="tile-icon">${issueIcon(issue.id)}</span>${esc(issue.label)}</h2>

      <div class="spectrum-box">
        ${points.length ? spectrum(points, { mini: true })
          : `<p class="nodata" style="margin:6px 0">No candidate has enough verified statements on this issue to place on the spectrum.</p>`}
        <p class="spectrum-note">AI estimate · not verified by the candidates · <a href="#/methodology">how it works</a></p>
      </div>

      <p class="small muted" style="margin:14px 0 0">Statements summarize what each candidate says on their own campaign
      or official websites. Open <b>View sources</b> to read their exact words.</p>
      <div class="issue-cols" style="--cols:${gridCols(cands.length)}">
        ${cands.map((c) => {
          const fs = c.findings.filter((f) => f.issue_id === current);
          const s = c.scores[current] || {};
          const placed = s.score !== null && s.score !== undefined;
          return `<article class="issue-col" style="--party:${c.color}">
            <h3>${esc(c.name)}${partyIcon(c.party)}</h3>
            ${fs.length ? `<ul>${fs.map((f) => `<li>${esc(f.claim)}${n.cite(f)}</li>`).join("")}</ul>` : `<p class="nodata">Not enough verified information.</p>`}
            <div class="col-foot">
              ${placed ? `<details class="why"><summary>Why this placement?</summary><p>${esc(s.rationale)} <i>(${esc(s.confidence)} confidence)</i></p></details>` : ""}
              <button class="link-btn" data-refresh="${esc(c.id)}" data-issue-id="${esc(current)}" ${STATUS?.ai_ready ? "" : "disabled"}
                title="Sends the Researcher agent to look for new statements. Uses 1 live AI request.">↻ Search again</button>
            </div>
          </article>`;
        }).join("")}
      </div>

      <div class="panel-foot">
        ${n.button()}
        <span class="small muted">"Search again" uses 1 live AI request and takes about a minute. <span id="limits-left">${limitsText()}</span></span>
      </div>
      <div id="refresh-status" aria-live="polite"></div>
    </section>`;
    }
  }

  if (tab === "ask") {
    body = `<section class="card"><h2>Ask about this race</h2>${chatUI("tab")}</section>`;
  }

  app.innerHTML = `
    <div class="race-head">
      <div><h1 class="title-flag">${flag(race.state, "flag flag-lg")}${esc(race.state_name)} · ${esc(race.office)} Race</h1>
        <p class="muted" style="margin:0">${cands.length} candidates on the official November 3, 2026 ballot</p></div>
    </div>
    <div class="tabs" role="tablist">${tabs.map(([k, l]) => `<button role="tab" data-tab="${k}" class="${k === tab ? "active" : ""}" aria-selected="${k === tab}">${l}</button>`).join("")}</div>
    ${body}`;

  app.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => { location.hash = `#/race/${id}/${b.dataset.tab}`; }));
  app.querySelectorAll("[data-issue]").forEach((b) => b.addEventListener("click", () => {
    location.hash = b.dataset.issue === issueId ? `#/race/${id}/issues` : `#/race/${id}/issues/${b.dataset.issue}`; }));
  app.querySelectorAll("[data-close-issue]").forEach((b) => b.addEventListener("click", () => { location.hash = `#/race/${id}/issues`; }));
  app.querySelectorAll("[data-refresh]").forEach((b) => b.addEventListener("click", () => doRefresh(b, id)));
  if (tab === "ask") wireChat("tab");
}

function limitsText() {
  const l = STATUS?.limits; if (!l) return "";
  return `Live AI requests left this session: <b>${l.session_left} of ${l.session_cap}</b>.`;
}
function updateLimits(l) {
  if (l) STATUS.limits = l;
  document.querySelectorAll(".limits-left, #limits-left").forEach((el) => { el.innerHTML = limitsText(); });
}

/* ---------- chat: one conversation per race, shown in the Ask tab and in the floating panel ---------- */
const CHAT = {};            // race id -> [{ role: "user" | "bot", text, refused, usage, error, pending }]
let CHAT_RACE = null;       // the race whose page is open
const SUGGESTIONS = ["What has each candidate said about housing?", "How do the candidates differ on taxes?",
  "What has each candidate said about immigration?"];

function chatUI(p) {
  return `
    <p class="muted small">Answers come only from the verified facts in this guide, each with its source. The chatbot does not
    search the web and will not recommend a candidate.</p>
    <div class="chat-log" id="${p}-log" aria-live="polite"></div>
    <div class="suggest">${SUGGESTIONS.map((s) => `<button type="button" data-suggest="${esc(s)}" data-for="${p}">${esc(s)}</button>`).join("")}</div>
    <form id="${p}-form" class="ask-box">
      <textarea id="${p}-q" maxlength="500" placeholder="Ask about the candidates in this race…" aria-label="Your question"></textarea>
      <button class="btn btn-primary" ${STATUS?.ai_ready ? "" : "disabled"}>Ask</button>
    </form>
    <p class="small muted" style="margin-top:6px">Max 500 characters. <span class="limits-left">${limitsText()}</span></p>
    ${STATUS?.ai_ready ? "" : `<p class="note">Live questions are off on this copy because no API key is set. Everything else works.</p>`}`;
}

function wireChat(p) {
  document.querySelectorAll(`[data-suggest][data-for="${p}"]`).forEach((b) =>
    b.addEventListener("click", () => { document.getElementById(`${p}-q`).value = b.dataset.suggest; }));
  const q = document.getElementById(`${p}-q`);
  q.addEventListener("keydown", (e) => {   // Enter sends, Shift+Enter adds a new line
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); document.getElementById(`${p}-form`).requestSubmit(); }
  });
  document.getElementById(`${p}-form`).addEventListener("submit", (e) => { e.preventDefault(); doAsk(p); });
  renderChat();
}

function renderChat() {
  const log = CHAT[CHAT_RACE] || [];
  const html = log.length ? log.map((m) => {
    if (m.role === "user") return `<div class="msg msg-user">${esc(m.text)}</div>`;
    if (m.pending) return `<div class="msg msg-bot"><span class="spinner"></span> Checking the verified facts…</div>`;
    if (m.error) return `<div class="msg msg-bot warn">${esc(m.error)}</div>`;
    const n = notes("Chat answer");
    const text = esc(m.text).replace(/\s*\[([a-z]+-\d+)\]/g, (x, fid) => n.cite(FACTS[fid]));
    return `<div class="msg msg-bot${m.refused ? " msg-refused" : ""}">${text}
      <div class="msg-foot">${n.button()}<span class="small muted">AI-written from verified facts · ${m.usage.input_tokens.toLocaleString()} tokens in,
      ${m.usage.output_tokens.toLocaleString()} out</span></div></div>`;
  }).join("") : `<p class="small muted chat-empty">No questions yet. Try one of the suggestions below.</p>`;
  ["tab", "drawer"].forEach((p) => {
    const el = document.getElementById(`${p}-log`);
    if (el) { el.innerHTML = html; el.scrollTop = el.scrollHeight; }
  });
}

async function doAsk(p) {
  const input = document.getElementById(`${p}-q`);
  const q = input.value.trim();
  if (!q || !CHAT_RACE) return;
  const log = (CHAT[CHAT_RACE] ||= []);
  if (log.some((m) => m.pending)) return;
  input.value = "";
  const reply = { role: "bot", pending: true };
  log.push({ role: "user", text: q }, reply);
  renderChat();
  try {
    const r = await api("/api/ask", { race_id: CHAT_RACE, question: q });
    updateLimits(r.limits);
    Object.assign(reply, { pending: false, text: r.answer, refused: r.refused, usage: r.usage });
  } catch (err) {
    updateLimits(err.data?.limits);
    Object.assign(reply, { pending: false, error: err.message });
  }
  renderChat();
}

/* floating chat button + side panel, shown on race pages */
function setChatRace(race) {
  CHAT_RACE = race ? race.id : null;
  const drawerOpen = document.getElementById("chat-drawer").classList.contains("open");
  if (!race) { if (drawerOpen) closeDrawer(); document.getElementById("chat-fab").hidden = true; return; }
  document.getElementById("chat-fab").hidden = drawerOpen;
  document.getElementById("drawer-title").textContent = `Ask about the ${race.state_name} ${race.office} Race`;
  if (drawerOpen) renderChat();
}
function openDrawer() {
  document.getElementById("drawer-body").innerHTML = chatUI("drawer");
  wireChat("drawer");
  document.getElementById("chat-drawer").classList.add("open");
  document.getElementById("chat-fab").hidden = true;
  document.getElementById("drawer-q").focus();
}
function closeDrawer() {
  document.getElementById("chat-drawer").classList.remove("open");
  document.getElementById("drawer-body").innerHTML = "";
  if (CHAT_RACE) document.getElementById("chat-fab").hidden = false;
}
document.getElementById("chat-fab").addEventListener("click", openDrawer);
document.getElementById("drawer-close").addEventListener("click", closeDrawer);

async function doRefresh(btn, raceId) {
  const st = document.getElementById("refresh-status");
  app.querySelectorAll("[data-refresh]").forEach((b) => (b.disabled = true));
  st.innerHTML = `<p><span class="spinner"></span> The Researcher agent is searching allowed sources… this takes about a minute.</p>`;
  try {
    const r = await api("/api/refresh", { candidate_id: btn.dataset.refresh, issue_id: btn.dataset.issueId });
    updateLimits(r.limits);
    await loadGuide();
    const msg = r.added ? `Added ${r.added} new verified statement(s).` : `No new statements passed the checks (found ${r.found}, ${r.passed_code_checks} passed the quote check). Nothing was changed.`;
    renderRace(raceId, "issues", btn.dataset.issueId);
    document.getElementById("refresh-status").innerHTML = `<p class="note">${esc(msg)}</p>`;
  } catch (err) {
    updateLimits(err.data?.limits);
    st.innerHTML = `<p class="warn">${esc(err.message)}</p>`;
    app.querySelectorAll("[data-refresh]").forEach((b) => (b.disabled = !STATUS?.ai_ready));
  }
}

function renderMethodology() {
  setVoteLink(null);
  const rubric = GUIDE.issues.map((i) => `<tr><th>${esc(i.label)}</th>${Object.values(i.anchors).map((a) => `<td>${esc(a)}</td>`).join("")}</tr>`).join("");
  app.innerHTML = `
  <h1>How this guide works</h1>
  <p class="lead muted" style="max-width:75ch">Four AI agents and a set of plain-code checks build every page. The only subjective part is the
  spectrum, and it is labelled as an AI estimate wherever it appears.</p>
  <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(250px,1fr));margin:20px 0">
    <div class="card"><span class="pill">1 · Researcher agent</span><p>Searches only allowed sources and copies the exact words that show each candidate's position, with the page address.</p></div>
    <div class="card"><span class="pill">2 · Code check</span><p>Plain code (not AI) opens the page and confirms the quote appears on it word for word, and that the site is on the allowed list.</p></div>
    <div class="card"><span class="pill">3 · Verifier agent</span><p>A separate agent checks the quote is the candidate's own position, the summary adds nothing, and the wording is neutral. When in doubt it rejects.</p></div>
    <div class="card"><span class="pill">4 · Scorer agent</span><p>Places each candidate on each issue's left-right scale using the fixed rubric below, from verified statements only.</p></div>
  </div>
  <details class="card" open><summary>Which sources count</summary>
    <ul><li><b>Allowed:</b> the candidate's own campaign website; official government websites (.gov, e.g., governor and Senate offices);
    AP and Reuters reporting of the candidate's own words (labelled as news wire).</li>
    <li><b>Never used:</b> Wikipedia and other publicly editable or third-party summary sites, opinion pieces, and social media posts.</li>
    <li>When an official site blocks automated readers, the quote is checked against the Internet Archive's copy of the same page, and the source note says so.</li>
    <li>If a candidate's position cannot be confirmed this way, the guide says <i>"Not enough verified information"</i> instead of guessing.</li></ul>
  </details>
  <details class="card" open><summary>How spectrum positions are estimated</summary>
    <p>Each issue has a fixed rubric with five anchor positions from −1.0 (furthest left position commonly held in U.S. politics) to +1.0 (furthest right).
    The Scorer reads only a candidate's verified statements on that issue, never their name or party, and picks the anchor they best match.
    The ends of the scale need statements matching the whole anchor; partial matches stop at ±0.75. Confidence is high, medium or low depending on how many clear statements support it.</p>
    <p>The <b>overall</b> position is the simple average of the issue placements, shown only when at least 4 of the 12 issues could be placed.</p>
    <p>For candidates who have served in Congress, a dashed ring shows their <b>Voteview DW-NOMINATE</b> score, a widely used academic measure built from
    every recorded vote they cast (<a href="https://voteview.com" target="_blank" rel="noopener noreferrer">voteview.com ↗</a>). It is shown for comparison only and is not mixed into the AI estimate.</p>
    <p class="warn"><b>Limits.</b> A placement reflects only what a candidate has published on allowed sources, so it can miss positions they hold.
    AI placements can shift slightly between runs. Foreign policy does not divide neatly into left and right. Candidates have not reviewed these estimates.</p>
  </details>
  <details class="card"><summary>The rubric for all 12 issues</summary>
    <div style="overflow-x:auto"><table class="rubric"><thead><tr><th>Issue</th><th>−1.0 (left)</th><th>−0.5</th><th>0 (center)</th><th>+0.5</th><th>+1.0 (right)</th></tr></thead>
    <tbody>${rubric}</tbody></table></div>
  </details>
  <details class="card"><summary>Safety and cost controls</summary>
    <ul><li>Every agent run has hard limits on model calls, tool calls, web searches and tokens, so a loop cannot run away.</li>
    <li>Live features (Ask and Search again) are capped per session, per network and per day for the whole site. Browsing is unlimited.</li>
    <li>Text read from web pages is treated as data, never as instructions (prompt-injection defense).</li>
    <li>Every answer is checked by code for voting recommendations and for citations that do not exist before you see it.</li>
    <li>Every candidate is shown in the same format, with the same fields. Democrats are listed first in blue and Republicans second in red,
    the usual U.S. convention; candidates of other parties follow in neutral colors. This order follows party labels only and says nothing about a candidate's positions.</li></ul>
  </details>`;
}

function renderAbout() {
  setVoteLink(null);
  app.innerHTML = `
  <h1>About this guide</h1>
  <div class="card" style="max-width:80ch">
    <p>This is an independent, nonpartisan student project built for a course at the Yale School of Management. It is
    <b>not affiliated with or endorsed by Yale University, the Yale School of Management, or any candidate, campaign, or party</b>,
    and it does not recommend any candidate or party.</p>
    <p>Its purpose is to make it quicker to see what the candidates on your ballot have said, in their own words, with the source
    one click away. It covers the November 3, 2026 statewide races in New York (Governor), New Jersey (U.S. Senate) and Connecticut (Governor).</p>
    <p><b>Report an error.</b> If anything here is wrong, out of date, or unfairly worded, please
    <a href="https://github.com/athamam/votebetter/issues" target="_blank" rel="noopener noreferrer">open an issue on GitHub ↗</a>. Corrections are made by re-running the same checks, never by hand-editing a candidate's positions.</p>
    <p class="small muted">Not legal, financial or voting advice. For official information on registering and voting, use the
    <a href="https://vote.gov/" target="_blank" rel="noopener noreferrer">vote.gov ↗</a> link at the top of every page or your state's election office.</p>
  </div>`;
}

function renderNotFound() { app.innerHTML = `<h1>Page not found</h1><p><a href="#/">Back to the start</a></p>`; }

/* ---------- router ---------- */
function route() {
  if (!GUIDE) return;
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  document.querySelectorAll(".nav a").forEach((a) => a.classList.toggle("active", a.getAttribute("href") === `#/${parts[0] || ""}`));
  if (parts[0] !== "race") setChatRace(null);
  if (!parts.length) renderHome();
  else if (parts[0] === "start") { renderHome(); document.getElementById("start").scrollIntoView(); return; }
  else if (parts[0] === "state") renderState(parts[1]);
  else if (parts[0] === "race") renderRace(parts[1], parts[2], parts[3]);
  else if (parts[0] === "methodology") renderMethodology();
  else if (parts[0] === "about") renderAbout();
  else renderNotFound();
  window.scrollTo(0, 0);
}

async function loadGuide() {
  GUIDE = await api("/api/guide");
  FACTS = {};
  GUIDE.races.forEach((r) => r.candidates.forEach((c) => [...c.profile, ...c.findings].forEach((f) => { FACTS[f.fid] = f; })));
  document.getElementById("built-at").textContent = `Data checked ${fmtDate(GUIDE.generated_at)}.`;
}

(async function start() {
  tickCountdown(); setInterval(tickCountdown, 30_000);
  try {
    [STATUS] = await Promise.all([api("/api/status"), loadGuide()]);
  } catch (e) {
    app.innerHTML = `<p class="warn">Could not load the guide: ${esc(e.message)}</p>`; return;
  }
  window.addEventListener("hashchange", route);
  route();
})();
