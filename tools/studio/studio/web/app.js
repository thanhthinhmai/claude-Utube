// @ts-check
// Film Studio: track jobs and review them (specs/003-studio-ui). Plain JavaScript, no build step.
"use strict";
const API = "/api/v1";
const $app = document.getElementById("app");
const STATUS = {
  queued: "In queue", running: "Running", waiting_review: "Needs review", waiting_resume: "Waiting to resume", done: "Done",
  failed: "Failed", stopped: "Stopped", inactive: "Inactive",
};
const KIND = { learn: "Learn a style", film: "Make a film" };
const REVIEW = { "style-1": "Review 1: style draft", "style-2": "Review 2: proof frame", question: "Question from the studio",
  treatment: "Treatment review" };
// Online mode (specs/007): the same page serves many customers; MODE comes from GET /health
let MODE = "local";
/** @type {any} */
let ME = null;
const DECISION = { approve: "Approve", revise: "Request changes", accept_anyway: "Accept anyway", stop: "Stop" };
const SOURCE = { ui: "the studio", chat: "the chat" };

// ---------- helpers ----------
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const when = (iso) => (iso ? new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" }) : "");
const num = (v, d = 3) => (v === null || v === undefined ? "–"
  : typeof v === "number" ? v.toLocaleString("en-US", { maximumFractionDigits: d }) : esc(v));
const METRIC = {
  luma_p50: "Brightness (median, 0–1)", luma_p2: "Brightness of the darkest areas", luma_p98: "Brightness of the brightest areas",
  contrast_p50: "Contrast", sat_p50: "Color saturation", dark_p50: "Share of very dark pixels", bright_p50: "Share of very bright pixels",
  still_ratio: "Share of frames with a still camera", motion720_p50: "Camera movement (px/frame, median)",
  motion720_p90: "Fast camera movement (px/frame)", shot_len_median: "Shot length (s, median)",
  shot_len_mean: "Shot length (s, mean)", cuts_per_min: "Cuts per minute",
  flashes_per_min: "Flashes per minute", lufs: "Loudness (LUFS)", lra: "Loudness range (LU)",
  silence_per_min: "Silence (s per minute)", first_voice_t: "First voice at (s)",
  speech_rate: "Speech rate (words/s)",
};
const head = (eyebrow, title, lead) => `<p class="eyebrow">${eyebrow}</p><h1>${title}</h1>${lead ? `<p class="lead">${lead}</p>` : ""}`;
const back = (href, text) => `<a class="back" href="${href}">← ${text}</a>`;
const SPARK = '<svg viewBox="0 0 24 24"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/></svg>';
const PROMPTS = [
  ["Learn a channel's style", "Learn the style of the channel https://www.youtube.com/@channel-name, last 5 videos."],
  ["Learn from your own videos", "Learn the style from the videos in references/my-set/videos, name the set my-set."],
  ["A film in a learned style", "Make a 30-second film in the Quiet Night style about a late-night bánh mì stall."],
  ["A film in a library style", "Make a 40-second watercolor film about my family's coffee shop."],
];
const ERR = {
  // specs/008: the owner account and the AI accounts
  already_set_up: "The studio already has an owner. Sign in instead.",
  last_owner: "The studio needs at least one owner who is switched on.",
  self: "You cannot do this to your own account here.",
  email_taken_password: "This email already has an account with another password. Use that password to make it the owner.",
  max_accounts: "There are 5 Claude accounts already: remove one to add another.",
  first_account: "The first Claude account cannot be removed. Sign it out instead.",
  no_login: "This sign-in is no longer waiting (it ends after 10 minutes). Press Sign in again.",
  bad_code: "Claude did not accept that code. Press Sign in again to get a new link.",
  login_failed: "Claude Code did not start the sign-in. Try again in a minute.",
  not_found: "Not found.", bad_name: "Invalid file name.", invalid: "Invalid request.", finished: "This job has already finished.",
  already_decided: "This review was already decided elsewhere.", note_required: "Add a note (at least 3 characters) before requesting changes.",
  value_not_allowed: "That choice is not allowed for this review.", csrf: "Request blocked (missing studio header).",
  bad_host: "Request blocked (wrong host).", not_local: "Request blocked (not from this machine).",
  auth_required: "Please log in.", locked: "This account is locked. Contact the studio.",
  bad_login: "Wrong email or password.", email_taken: "This email already has an account. Log in instead.",
  weak_password: "The password needs at least 10 characters.", terms_required: "Please accept the terms of use.",
  signup_closed: "There is no public sign-up. Ask the studio owner to add you.", token_expired: "This link was already used or has expired.",
  rate_limited: "Too many tries. Please wait a little and try again.", unverified: "Confirm your email first: open the link we sent you.",
  quota_exceeded: "You have used all your films for this month.", daily_cap: "The studio is fully booked today. Please try again tomorrow.",
  too_many_queued: "You already have 3 jobs in progress. Wait for one to finish.", too_long: "The film is too long.",
  content_rejected: "The studio cannot make this idea.", style_not_found: "This style does not exist any more.",
  in_use: "A job is still using this.", rights_required: "Please confirm your right to use the channel's videos.",
  too_many_questions: "The studio already asked 3 questions.", too_many_videos: "Too many videos for one style.", too_large: "The file is too large.", bad_video: "This file is not a video the studio can read.",
};
const errText = (body, status) => {
  const e = body?.error || {};
  let t = ERR[e.code] || `Error ${status}`;
  if (e.code === "quota_exceeded" && e.resets_at) t += ` Your films come back on ${when(e.resets_at)}.`;
  if (e.code === "content_rejected" && e.reason) t += ` ${e.reason}`;
  return t;
};
const fold = (s) => String(s ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const stylePrompt = (name) => `Make a 40-second film in the ${name} style about …`;
const useBtn = (name, slug = "") => (MODE === "online" && slug
  ? `<a class="button primary" href="#/new?style=${encodeURIComponent(slug)}">Make a film in this style</a>`
  : `<button class="primary use" data-name="${esc(name)}">Use this style</button>`);
async function copyPrompt(btn) {
  const text = stylePrompt(btn.dataset.name);
  const box = btn.parentElement;
  box.querySelector(".copied, .prompt-box")?.remove();
  try {
    await navigator.clipboard.writeText(text);
    btn.insertAdjacentHTML("afterend", '<span class="copied">✓ Copied: paste it into Claude Code</span>');
  } catch {   // clipboard blocked: show the prompt so it can be copied by hand
    btn.insertAdjacentHTML("afterend", `<textarea class="prompt-box" readonly rows="2" aria-label="Prompt to copy">${esc(text)}</textarea>`);
    const t = box.querySelector(".prompt-box"); t.focus(); t.select();
  }
}
function wireUse(root) {
  root.querySelectorAll("button.use").forEach((b) => b.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); copyPrompt(b); }));
}
const badge = (s) => `<span class="badge s-${esc(s)}">${esc(STATUS[s] || s)}</span>`;
function failed(r, body) {
  if (MODE === "online" && r.status === 401 && body?.error?.code === "auth_required" && !location.hash.startsWith("#/login")) {
    ME = null; location.hash = "#/login";
  }
  const e = /** @type {Error & {code?: string}} */ (new Error(errText(body, r.status))); e.code = body?.error?.code;
  return e;
}
async function get(path) {
  const r = await fetch(API + path);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw failed(r, body);
  return body;
}
async function send(method, path, data) {
  const r = await fetch(API + path, { method, headers: { "Content-Type": "application/json", "X-Studio": "1" },
    body: data === undefined ? undefined : JSON.stringify(data) });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw failed(r, body);
  return body;
}
const post = (path, data) => send("POST", path, data);
function zoomable(root) {
  root.querySelectorAll("img[data-zoom]").forEach((img) => img.addEventListener("click", () => {
    const lb = document.getElementById("lightbox"); lb.querySelector("img").src = img.src; lb.hidden = false;
  }));
}
document.getElementById("lightbox").addEventListener("click", (e) => { /** @type {HTMLElement} */ (e.currentTarget).hidden = true; });

// ---------- pages ----------
async function pageJobs() {
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  const st = params.get("status") || "", kd = params.get("kind") || "";
  const q = new URLSearchParams(); if (st) q.set("status", st); if (kd) q.set("kind", kd);
  const { jobs } = await get("/jobs" + (q.toString() ? "?" + q : ""));
  const opt = (map, cur) => Object.entries(map).map(([k, v]) => `<option value="${k}" ${k === cur ? "selected" : ""}>${v}</option>`).join("");
  const items = jobs.map((j) => {
    const p = j.progress ? `<div class="bar"><i style="width:${Math.round((100 * j.progress.done) / j.progress.total)}%"></i></div>` : "";
    return `<li><a class="panel job ${j.status === "waiting_review" ? "waiting" : ""}" href="#/jobs/${esc(j.id)}">
      <strong>${esc(j.name)}</strong> ${badge(j.status)}
      <span class="muted">${esc(KIND[j.kind] || j.kind)} · ${esc(j.step)}</span>
      <span class="muted">${when(j.updated_at)}</span>${p}</a></li>`;
  }).join("");
  if (!jobs.length && !st && !kd) return emptyJobs();
  $app.innerHTML = `${head("Track", "Jobs", "Everything Claude is doing for you: learning styles and making films. Jobs that need your review are highlighted in purple.")}
    ${MODE === "online" ? '<p><a class="button primary" href="#/new">New film</a></p>' : ""}
    <div class="row filters">
      <label>Status <select id="f-status"><option value="">All</option>${opt(STATUS, st)}</select></label>
      <label>Type <select id="f-kind"><option value="">All</option>${opt(KIND, kd)}</select></label>
    </div>
    ${jobs.length ? `<ul class="jobs">${items}</ul>` : `<p class="panel muted">No jobs match these filters.</p>`}`;
  const go = () => {
    const nq = new URLSearchParams();
    const s = (/** @type {HTMLInputElement} */ (document.getElementById("f-status"))).value, k = (/** @type {HTMLInputElement} */ (document.getElementById("f-kind"))).value;
    if (s) nq.set("status", s); if (k) nq.set("kind", k);
    location.hash = "#/" + (nq.toString() ? "?" + nq : "");
  };
  document.getElementById("f-status").onchange = go;
  document.getElementById("f-kind").onchange = go;
}

function emptyJobs() {
  if (MODE === "online") {
    $app.innerHTML = `<div class="empty"><span class="spark">${SPARK}</span><h1>What should we make today?</h1>
      <p class="muted">Pick a style, describe your idea, and the studio makes the film for you. You can follow every step here.</p>
      <p><a class="button primary" href="#/new">Make a film</a> <a class="button" href="#/learn">Learn a style</a></p></div>`;
    return;
  }
  $app.innerHTML = `<div class="empty"><span class="spark">${SPARK}</span>
      <h1>What should we make today?</h1>
      <p class="muted">Open Claude Code in the project folder and say what you want. Jobs show up here, with the steps that need your review.</p></div>
    <div class="prompts">${PROMPTS.map(([t, x]) => `<div class="panel prompt" tabindex="0" data-text="${esc(x)}">
      <strong>${esc(t)}</strong><p>${esc(x)}</p></div>`).join("")}</div>
    <p class="muted" style="text-align:center;margin-top:16px">Click a card to copy the example prompt.</p>`;
  (/** @type {NodeListOf<HTMLElement>} */ ($app.querySelectorAll(".prompt"))).forEach((el) => {
    const copy = async () => {
      try { await navigator.clipboard.writeText(el.dataset.text); } catch { return; }
      el.querySelector(".copied")?.remove();
      el.insertAdjacentHTML("beforeend", '<p class="copied">✓ Copied: paste it into Claude Code</p>');
    };
    el.onclick = copy; el.onkeydown = (e) => { if (e.key === "Enter") copy(); };
  });
}

async function pageJob(id) {
  const j = await get(`/jobs/${encodeURIComponent(id)}`);
  const pct = j.progress ? Math.round((100 * j.progress.done) / j.progress.total) : null;
  const links = [
    j.links.set && `<a href="#/sets/${esc(j.links.set)}">Measurements: ${esc(j.links.set)}</a>`,
    j.links.film && `<a href="#/films/${esc(j.links.film)}">Film: ${esc(j.links.film)}</a>`,
    j.links.style && `<a href="#/styles/${esc(j.links.style)}">Style: ${esc(j.links.style)}</a>`,
  ].filter(Boolean).join(" · ");
  const revs = j.reviews.map((r) => `<li class="panel"><a href="#/reviews/${esc(r.id)}">${esc(REVIEW[r.kind])}</a>
      ${r.decision ? `<span class="muted">${esc(DECISION[r.decision.value])} · via ${esc(SOURCE[r.decision.source])}</span>` : `<span class="badge s-waiting_review">Needs your review</span>`}</li>`).join("");
  const open = j.status === "waiting_review" ? j.reviews.find((r) => !r.decision) : null;
  $app.innerHTML = `${back("#/", "Jobs")}
    ${head(esc(KIND[j.kind] || j.kind), `${esc(j.name)} ${badge(j.status)}`, j.usage && j.usage.calls
      ? `Claude: ${num(j.usage.calls, 0)} call${j.usage.calls === 1 ? "" : "s"} · ${num(j.usage.tokens_in, 0)} tokens in · ${num(j.usage.tokens_out, 0)} out · ${num(j.usage.tokens, 0)} in total${j.cost_usd ? ` · ${usd(j.cost_usd)} through the API key` : ""}` : "")}
    <div class="split"><div>
    ${open && open.kind === "question" ? `<div class="panel decide" id="answer-box"><p class="section-title">The studio has a question</p>
      <div class="md">${open.summary_html}</div>
      <textarea id="answer" maxlength="4000" placeholder="Your answer"></textarea>
      <div class="row" style="margin-top:8px"><button class="primary" id="send-answer">Send</button></div><p id="answer-msg" class="muted" role="status"></p></div>`
    : open ? `<p class="notice">This job is waiting for your review: <a href="#/reviews/${esc(open.id)}">${open.kind === "treatment" ? "review the treatment" : "open the review"}</a>.</p>` : ""}
    ${j.status === "queued" ? `<p class="notice">${j.step === "Waiting for a Claude account" ? "Waiting for a Claude account: the studio owner needs to sign one in on AI accounts." : `In the queue${j.queue_position ? `: number ${j.queue_position}` : ""}. It starts by itself when the studio is free.`}</p>` : ""}
    ${MODE === "online" && j.status === "done" && j.links.film ? `<p><a class="button primary" href="${API}/films/${encodeURIComponent(j.links.film)}/download">Download the film</a>
      <a class="button" href="#/films/${esc(j.links.film)}">Watch it</a></p>
      <details class="panel" id="changes"><summary><strong>Request changes</strong> <span class="muted">· makes a new version and keeps this one</span></summary>
        <textarea id="change-note" maxlength="2000" placeholder="What should be different? For example: a slower ending, warmer colours."></textarea>
        <div class="row" style="margin-top:8px"><button class="primary" id="send-changes">Request changes (uses 1 film credit)</button></div>
        <p id="changes-msg" class="muted" role="status"></p></details>` : ""}
    ${j.status === "waiting_resume" ? `<p class="notice">You decided, but the Claude session is no longer waiting. Open Claude Code again and say “continue job ${esc(j.name)}”.</p>` : ""}
    ${j.status === "inactive" ? `<p class="notice">No updates for over 10 minutes: the Claude session may have closed or stopped.</p>` : ""}
    ${j.error ? `<p class="error">${esc(j.error)}</p>` : ""}
    <div class="panel"><p class="section-title">Current step</p><p style="font-size:16px;font-weight:600">${esc(j.step)}</p>
      ${pct !== null ? `<div class="bar"><i style="width:${pct}%"></i></div>` : ""}</div>
    ${revs ? `<h2>Reviews</h2><ul class="reviews">${revs}</ul>` : ""}
    <h2>Log</h2><pre class="log">${j.log.map((l) => `${new Date(l.t).toLocaleTimeString("en-GB")}  ${esc(l.line)}`).join("\n") || "No lines yet."}</pre>
    </div><aside class="aside panel"><p class="section-title">Summary</p><dl class="kv">
      <dt>Type</dt><dd>${esc(KIND[j.kind] || j.kind)}</dd>
      <dt>Status</dt><dd>${esc(STATUS[j.status] || j.status)}</dd>
      <dt>Progress</dt><dd>${pct !== null ? `${j.progress.done}/${j.progress.total}` : "—"}</dd>
      <dt>Started</dt><dd>${when(j.started_at)}</dd>
      <dt>Updated</dt><dd>${when(j.updated_at)}</dd></dl>
      ${MODE === "online" && !["done", "failed", "stopped"].includes(j.status) ? `<p style="margin-top:14px"><button class="danger" id="stop">Stop this job</button></p>
        <p class="muted" style="font-size:13px">Stopping keeps the film credit used.</p>` : ""}
      ${links ? `<p class="section-title" style="margin-top:18px">Results</p><p style="display:grid;gap:4px;margin:0">${links.replaceAll(" · ", "")}</p>` : ""}
    </aside></div>`;
  const sendAnswer = /** @type {HTMLButtonElement | null} */ (document.getElementById("send-answer"));
  if (sendAnswer) sendAnswer.onclick = async () => {
    const note = field("answer").value.trim(), msg = document.getElementById("answer-msg");
    if (!note) { msg.className = "fail"; msg.textContent = "Write your answer first."; return; }
    sendAnswer.disabled = true;
    try { await post(`/reviews/${encodeURIComponent(open.id)}/decision`, { value: "approve", note }); route(); }
    catch (e) { msg.className = "fail"; msg.textContent = e.message; sendAnswer.disabled = false; }
  };
  const sendChanges = /** @type {HTMLButtonElement | null} */ (document.getElementById("send-changes"));
  if (sendChanges) sendChanges.onclick = async () => {
    const note = field("change-note").value.trim(), msg = document.getElementById("changes-msg");
    if (note.length < 3) { msg.className = "fail"; msg.textContent = "Say what should change (at least 3 characters)."; return; }
    sendChanges.disabled = true;
    try {
      const nj = await post("/jobs", { kind: "film", revise_of: j.links.film, note });
      await loadMe(); location.hash = `#/jobs/${nj.id}`;
    } catch (e) { msg.className = "fail"; msg.textContent = e.message; sendChanges.disabled = false; }
  };
  const stop = /** @type {HTMLButtonElement | null} */ (document.getElementById("stop"));
  if (stop) stop.onclick = async () => {
    if (!confirm("Stop this job? The film credit is not given back.")) return;
    stop.disabled = true;
    try { await post(`/jobs/${encodeURIComponent(id)}/stop`); } catch (e) { alert(e.message); }
    route();
  };
}

function metricRows(c) {
  const rows = [
    ["Brightness difference", c.luma_diff, "≤ 0.05", c.luma_diff <= 0.05],
    ["Saturation difference", c.sat_median_diff, "≤ 0.08", c.sat_median_diff <= 0.08],
    ["Very dark area difference (pp)", c.dark_diff_pp, "≤ 5", c.dark_diff_pp <= 5],
    ["Colors matched", c.palette_matched, `≥ ${c.palette_needed}`, c.palette_matched >= c.palette_needed],
  ];
  return rows.map(([n, v, lim, ok]) => `<tr><td>${n}</td><td class="num">${num(v)}</td><td>${lim}</td>
    <td class="${ok ? "pass" : "fail"}">${ok ? "✓ pass" : "✗ not yet"}</td></tr>`).join("");
}

async function pageReview(id) {
  const r = await get(`/reviews/${encodeURIComponent(id)}`);
  const c = r.compare;
  const file = (p) => (p || "").split("/").pop();
  const proof = c ? `<div class="pair">
      <figure><img data-zoom src="${API}/sets/${esc(r.set)}/proof/${esc(file(c.ref))}" alt="Reference frame"><figcaption>Reference frame (click to zoom)</figcaption></figure>
      <figure><img data-zoom src="${API}/sets/${esc(r.set)}/proof/${esc(file(c.ours))}" alt="Our frame"><figcaption>Our frame, drawn in code · round ${num(c.round, 0)}</figcaption></figure></div>
      <h2>Four checks</h2><table><tr><th>Check</th><th>Value</th><th>Limit</th><th></th></tr>${metricRows(c)}</table>
      <p>${c.pass ? '<span class="pass">All 4 checks pass.</span>' : '<span class="fail">Not all 4 checks pass yet.</span>'}
      ${r.final_round ? " No revision rounds left." : ""}</p>` : "";
  const d = r.decision;
  const extra = r.final_round ? `<button data-v="accept_anyway">Accept anyway</button><button class="danger" data-v="stop">Stop</button>` : "";
  $app.innerHTML = `${back(`#/jobs/${esc(r.job_id)}`, "Job")}
    ${head("Review", esc(REVIEW[r.kind]), `${r.set ? `Reference set <a href="#/sets/${esc(r.set)}">${esc(r.set)}</a> · ` : ""}sent ${when(r.created_at)}`)}
    ${proof}
    <h2>${c ? "Notes from Claude" : "Summary"}</h2><div class="panel md">${r.summary_html}</div>
    <div class="panel decide" id="decide">${d ? decidedHtml(d, r.kind) : r.kind === "question" ? `
      <p><strong>Your answer</strong> <span class="muted">· the job continues on its own</span></p>
      <textarea id="note" maxlength="4000" placeholder="Your answer"></textarea>
      <div class="row" style="margin-top:8px"><button class="primary" data-v="approve">Send</button></div>
      <p id="msg" class="muted"></p>` : `
      <p><strong>Your decision</strong> <span class="muted">· the job continues on its own, no need to type in the chat</span></p>
      <textarea id="note" placeholder="Note (required when requesting changes)"></textarea>
      <div class="row" style="margin-top:8px"><button class="primary" data-v="approve">Approve</button><button data-v="revise">Request changes</button>${extra}</div>
      <p id="msg" class="muted"></p>`}</div>`;
  zoomable($app);
  (/** @type {NodeListOf<HTMLElement>} */ ($app.querySelectorAll("#decide button[data-v]"))).forEach((b) => b.addEventListener("click", async () => {
    const v = b.dataset.v, note = (/** @type {HTMLInputElement} */ (document.getElementById("note"))).value.trim(), msg = document.getElementById("msg");
    if (v === "revise" && note.length < 3) { msg.textContent = ERR.note_required; msg.className = "fail"; return; }
    if (r.kind === "question" && !note) { msg.textContent = "Write your answer first."; msg.className = "fail"; return; }
    (/** @type {NodeListOf<HTMLButtonElement>} */ ($app.querySelectorAll("#decide button"))).forEach((x) => (x.disabled = true));
    try {
      const res = await post(`/reviews/${encodeURIComponent(id)}/decision`, { value: v, note });
      document.getElementById("decide").innerHTML = decidedHtml(res, r.kind);
      askNotify();
    } catch (e) {
      msg.textContent = e.message; msg.className = "fail";
      if (e.code === "already_decided") setTimeout(route, 800); else (/** @type {NodeListOf<HTMLButtonElement>} */ ($app.querySelectorAll("#decide button"))).forEach((x) => (x.disabled = false));
    }
  }));
}
const decidedHtml = (d, kind = "") => (kind === "question"
  ? `<p class="done-box">You answered (${when(d.at)}): ${esc(d.note)}</p>`
  : `<p class="done-box">Decided: <strong>${esc(DECISION[d.value])}</strong> (via ${esc(SOURCE[d.source])}, ${when(d.at)})
  ${d.note ? `<br>Note: ${esc(d.note)}` : ""}</p>`);

async function pageFilms() {
  const { films } = await get("/films");
  $app.innerHTML = `${head("Results", "Films", MODE === "online" ? "Your finished films." : "Rendered films in the films/ folder.")}${films.length ? `<div class="grid">${films.map((f) => `<a class="panel card" href="#/films/${esc(f.name)}">
      ${f.has_poster ? `<img src="${API}/films/${esc(f.name)}/poster" alt="">` : ""}<p><strong>${esc(f.name)}</strong>
      ${f.rendering ? '<span class="badge s-running">Rendering</span>' : ""}</p></a>`).join("")}</div>`
    : `<p class="panel muted">No films in the films/ folder yet.</p>`}`;
}

async function pageFilm(name) {
  const f = await get(`/films/${encodeURIComponent(name)}`);
  const base = `${API}/films/${encodeURIComponent(name)}`;
  $app.innerHTML = `${back("#/films", "Films")}${head("Film", esc(f.name), "")}
    ${f.has_video ? `<video controls preload="metadata" ${f.has_poster ? `poster="${base}/poster"` : ""}>
        <source src="${base}/video" type="video/mp4">
        ${f.has_subtitles ? `<track kind="subtitles" srclang="vi" label="Subtitles" src="${base}/subtitles.vtt" default>` : ""}
      </video><p class="muted">Turn subtitles on or off with the player’s CC button.</p>
      ${MODE === "online" ? `<p><a class="button primary" href="${base}/download">Download</a> <button class="danger" id="del-film">Delete this film</button></p>` : ""}`
    : `<p class="notice">${f.rendering ? "The film is still rendering: see progress on the Jobs page." : "No film file yet."}</p>`}
    ${f.treatment_html ? `<h2>Script (TREATMENT)</h2><div class="panel md">${f.treatment_html}</div>` : ""}
    ${f.credits ? `<h2>Third-party assets (CREDITS)</h2><pre class="log">${esc(f.credits)}</pre>` : ""}`;
  const del = document.getElementById("del-film");
  if (del) del.onclick = async () => {
    if (!confirm("Delete this film for good?")) return;
    try { await send("DELETE", `/films/${encodeURIComponent(name)}`); location.hash = "#/films"; } catch (e) { alert(e.message); }
  };
}

async function pageSets() {
  const { sets } = await get("/sets");
  $app.innerHTML = `${head("Browse", "Measurements", "Frame-by-frame measurements of the reference video sets you learned from.")}${sets.length ? `<ul class="jobs">${sets.map((s) => `<li><a class="panel job" href="#/sets/${esc(s.set)}">
      <strong>${esc(s.set)}</strong><span class="muted">${s.measured}/${s.videos} videos measured</span>
      <span class="muted">${s.media_removed ? "Reference videos deleted" : MODE === "online" ? "Learning in progress" : "Reference videos still on this machine"}</span></a></li>`).join("")}</ul>`
    : `<p class="panel muted">No reference sets yet.</p>`}`;
}

async function pageSet(name) {
  const s = await get(`/sets/${encodeURIComponent(name)}`);
  const sh = await get(`/sets/${encodeURIComponent(name)}/sheets`);
  const sum = s.summary || {};
  const groups = Object.entries(sum.by_orientation || {}).map(([o, g]) => `<h2>${esc({ landscape: "Landscape", portrait: "Portrait", square: "Square" }[o] || o)} · ${g.videos} video${g.videos === 1 ? "" : "s"}</h2>
    <div class="swatches">${(g.palette || []).map((c) => `<span class="swatch" title="${esc(c.hex)} ${Math.round(c.share * 100)}%" style="background:${esc(c.hex)}"></span>`).join("")}</div>
    <table><tr><th>Measure</th><th>Median</th><th>Min</th><th>Max</th></tr>
    ${Object.entries(g.metrics).map(([k, m]) => `<tr><td title="${esc(k)}">${esc(METRIC[k] || k)}</td><td class="num">${num(m.median)}</td><td class="num">${num(m.min)}</td><td class="num">${num(m.max)}</td></tr>`).join("")}</table>`).join("");
  const warns = [sum.low_count_warning && "Fewer than 5 videos: conclusions are less reliable.",
    (sum.dispersion_warnings || []).length && `Large spread: ${sum.dispersion_warnings.join(", ")}.`,
    (sum.no_speech || []).length && `No speech found: ${sum.no_speech.join(", ")}.`,
    (sum.audio_unverified || []).length && `Original audio not confirmed: ${sum.audio_unverified.join(", ")}.`].filter(Boolean);
  const vids = Object.keys(sh.sheets || {});
  $app.innerHTML = `${back("#/sets", "Measurements")}${head("Measurements", esc(s.set), `${sum.videos_measured ?? 0} videos · ${num(sum.measured_seconds, 1)} seconds measured`)}
    ${warns.map((w) => `<p class="notice">${esc(w)}</p>`).join("")}${groups || '<p class="muted">No summary yet.</p>'}
    <h2>Contact sheets (one tile every 2 seconds)</h2>${sh.removed ? '<p class="muted">Deleted together with the reference videos.</p>' : `
      <div class="row"><select id="sv">${vids.map((v) => `<option>${esc(v)}</option>`).join("")}</select>
      <button id="prev">←</button><span id="pos" class="muted"></span><button id="next">→</button></div>
      <p><img id="sheet" class="shot" data-zoom alt="Contact sheet"></p>`}`;
  if (!sh.removed) {
    let i = 0;
    const show = () => {
      const files = sh.sheets[(/** @type {HTMLInputElement} */ (document.getElementById("sv"))).value]; i = Math.max(0, Math.min(i, files.length - 1));
      (/** @type {HTMLImageElement} */ (document.getElementById("sheet"))).src = `${API}/sets/${encodeURIComponent(name)}/sheets/${files[i]}`;
      document.getElementById("pos").textContent = `${i + 1}/${files.length} · seconds ${i * 2}–${i * 2 + 2}`;
    };
    document.getElementById("sv").onchange = () => { i = 0; show(); };
    document.getElementById("prev").onclick = () => { i--; show(); };
    document.getElementById("next").onclick = () => { i++; show(); };
    show();
  }
  zoomable($app);
}

async function pageStyles() {
  const { styles } = await get("/styles");
  $app.innerHTML = `${head("Browse", "My styles", "Styles you learned and saved in my-styles/, ready for making films.")}${styles.length ? `<div class="grid">${styles.map((s) => `<article class="panel card my-card" data-slug="${esc(s.slug)}" tabindex="0">
      ${s.has_styleframe ? `<img src="${API}/styles/${esc(s.slug)}/styleframe" alt="">` : ""}
      <p><strong>${esc(s.en || s.slug)}</strong><br><span class="muted">based on ${s.based_on_in_library
        ? `<a class="base-link" href="#/library/${esc(s.based_on)}">${esc(s.based_on)}</a>` : esc(s.based_on || "–")}${s.source === "learned" ? " · learned from videos" : ""}</span></p>
      <div class="use-row">${useBtn(s.en || s.slug, s.slug)}</div></article>`).join("")}</div>`
    : `<p class="panel muted">No styles yet. Learn one by telling Claude: “Learn the style of the channel …”.</p>`}`;
  (/** @type {NodeListOf<HTMLElement>} */ ($app.querySelectorAll(".my-card"))).forEach((c) => {
    const open = () => { location.hash = `#/styles/${c.dataset.slug}`; };
    c.onclick = (e) => { if (!(/** @type {Element} */ (e.target)).closest("a, button")) open(); };   // the base link and the button do their own thing
    c.onkeydown = (e) => { if (e.key === "Enter" && e.target === c) open(); };
  });
  wireUse($app);
}

async function pageStyle(slug) {
  const s = await get(`/styles/${encodeURIComponent(slug)}`);
  const ref = s.reference || {};
  $app.innerHTML = `${back("#/styles", "My styles")}${head(esc(slug), esc(s.en || slug), `Base technique ${s.based_on_in_library ? `<a href="#/library/${esc(s.based_on)}">${esc(s.based_on)}</a>` : esc(s.based_on || "–")} · ${s.source === "learned" ? `learned from ${ref.videos ?? "?"} videos, ${num(ref.measured_seconds, 0)} seconds measured` : "custom style"}${s.created ? ` · saved ${esc(s.created)}` : ""}`)}
    <div class="use-row">${useBtn(s.en || slug, slug)}</div>
    ${s.has_styleframe ? `<p><img class="shot" data-zoom src="${API}/styles/${esc(slug)}/styleframe" alt="Proof frame"></p>` : ""}
    <h2>STYLE.md</h2><div class="panel md">${s.style_html}</div>
    ${s.evidence_html ? `<h2>Evidence</h2><div class="panel md">${s.evidence_html}</div>` : ""}`;
  zoomable($app); wireUse($app);
}

// ---------- style library (004) ----------
let libHash = "#/library";
async function pageLibrary() {
  const lib = await get("/library");
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  let group = params.get("group") || "", q = params.get("q") || "";
  if (!lib.installed) {
    $app.innerHTML = `${head("Browse", "Library", "")}<p class="notice">The style library is not installed yet. Run <code>sh bin/studio setup</code>, then reload this page.</p>`;
    return;
  }
  const n = lib.styles.length;
  $app.innerHTML = `${head("Browse", "Library", `${n} styles from the pinned library (version ${esc(lib.version)}). Pick one, then make a film with it in Claude Code.`)}
    ${lib.posters.have < lib.posters.total ? `<p class="notice">Posters: ${lib.posters.have}/${lib.posters.total}. Run <code>sh bin/studio setup</code> to download the rest.</p>` : ""}
    ${lib.skipped ? `<p class="muted">${lib.skipped} style${lib.skipped === 1 ? " was" : "s were"} skipped because their files are missing or broken.</p>` : ""}
    <div class="lib-tools">
      <label class="search"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
        <input id="lib-q" type="search" placeholder="Search by name or use…" value="${esc(q)}" aria-label="Search styles"></label>
      <div class="chips" id="lib-groups"></div>
    </div>
    <p class="muted" id="lib-count"></p>
    <div class="lib-grid" id="lib-grid"></div>`;
  const chips = document.getElementById("lib-groups"), grid = document.getElementById("lib-grid"), count = document.getElementById("lib-count");
  const card = (s) => `<article class="panel lib-card" data-slug="${esc(s.slug)}" tabindex="0">
      ${s.has_poster ? `<img src="${API}/library/styles/${esc(s.slug)}/poster" alt="" loading="lazy" decoding="async">`
        : `<div class="poster-ph"><span>${esc(s.en)}</span></div>`}
      <div class="lib-body"><p class="lib-num">#${esc(s.num)} · ${esc(s.category)}</p>
        <h3>${esc(s.en)}</h3>
        <p class="lib-film"><em>${esc(s.film)}</em></p><p class="muted lib-line">${esc(s.line)}</p>
        <p class="pills">${s.uses.map((u) => `<span class="pill">${esc(u)}</span>`).join("")}</p>
        <div class="use-row">${useBtn(s.en, s.slug)}</div></div></article>`;
  const draw = () => {
    const words = fold(q).split(/\s+/).filter(Boolean);
    const hits = lib.styles.filter((s) => (!group || s.category === group)
      && words.every((w) => fold([s.en, s.cn, s.slug, ...s.uses].join(" ")).includes(w)));
    chips.innerHTML = [{ name: "", count: n }, ...lib.groups].map((g) =>
      `<button class="chip ${g.name === group ? "on" : ""}" data-g="${esc(g.name)}">${esc(g.name || "All")} <span>${g.count}</span></button>`).join("");
    count.textContent = hits.length === n ? "" : `${hits.length} of ${n} styles`;
    grid.innerHTML = hits.length ? hits.map(card).join("")
      : `<div class="panel empty-results"><p>No styles match.</p><button id="lib-clear">Clear filters</button></div>`;
    const qs = new URLSearchParams(); if (group) qs.set("group", group); if (q) qs.set("q", q);
    libHash = "#/library" + (qs.toString() ? "?" + qs : "");
    if (location.hash !== libHash) history.replaceState(null, "", libHash);
    (/** @type {NodeListOf<HTMLElement>} */ (chips.querySelectorAll(".chip"))).forEach((c) => (c.onclick = () => { group = c.dataset.g; draw(); }));
    document.getElementById("lib-clear")?.addEventListener("click", () => { group = ""; q = ""; (/** @type {HTMLInputElement} */ (document.getElementById("lib-q"))).value = ""; draw(); });
    (/** @type {NodeListOf<HTMLElement>} */ (grid.querySelectorAll(".lib-card"))).forEach((c) => {
      const open = () => { location.hash = `#/library/${c.dataset.slug}`; };
      c.onclick = open; c.onkeydown = (e) => { if (e.key === "Enter" && e.target === c) open(); };
    });
    wireUse(grid);
  };
  document.getElementById("lib-q").addEventListener("input", (e) => { q = (/** @type {HTMLInputElement} */ (e.target)).value; draw(); });
  draw();
}

async function pageLibStyle(slug) {
  const s = await get(`/library/styles/${encodeURIComponent(slug)}`);
  $app.innerHTML = `${back(libHash, "Library")}${head(`#${esc(s.num)} · ${esc(s.category)}`, esc(s.en), `${esc(s.cn)} · <code>${esc(s.slug)}</code>`)}
    <div class="split"><div>
      ${s.has_poster ? `<img class="shot" data-zoom src="${API}/library/styles/${esc(s.slug)}/poster" alt="Poster of ${esc(s.en)}">`
        : `<div class="poster-ph big"><span>${esc(s.en)}</span></div>`}
      <h2>Style rules (STYLE.md)</h2><div class="panel md">${s.style_html}</div>
    </div><aside class="aside panel"><p class="section-title">Demo film</p>
      <p style="font-weight:600;margin:0 0 4px"><em>${esc(s.film)}</em></p>
      <p class="muted" style="margin:0 0 12px">${esc(s.line)}${s.dur ? ` (${num(s.dur, 1)} s)` : ""}</p>
      ${s.github_url ? `<p><a href="${esc(s.github_url)}" target="_blank" rel="noopener">Watch the demo film on GitHub ↗</a></p>` : ""}
      <p class="section-title" style="margin-top:18px">Good for</p>
      <p class="pills">${s.uses.map((u) => `<span class="pill">${esc(u)}</span>`).join("")}</p>
      <div class="use-row">${useBtn(s.en, s.slug)}</div>
    </aside></div>`;
  zoomable($app); wireUse($app);
}

// ---------- online mode: accounts and new films (specs/007) ----------
const field = (id) => /** @type {HTMLInputElement} */ (document.getElementById(id));
function authPage(title, lead, body, foot = "") {
  document.body.classList.add("guest");
  $app.innerHTML = `<div class="auth-wrap"><div class="auth-brand"><span class="logo">F</span><span>Film Studio</span></div>
    <div class="auth panel"><h1>${title}</h1>${lead ? `<p class="muted">${lead}</p>` : ""}${body}
    <p id="msg" class="muted" role="status"></p></div>${foot ? `<div class="auth-foot">${foot}</div>` : ""}</div>`;
}
/** Wire a form: `fn` sends it; its result is shown, an error is shown in red. The button may say what it is
 *  doing while it waits (data-busy="Signing in…"). */
function onSubmit(fn) {
  const form = /** @type {HTMLFormElement} */ ($app.querySelector("form"));
  const msg = document.getElementById("msg");
  form.onsubmit = async (e) => {
    e.preventDefault();
    const btn = /** @type {HTMLButtonElement} */ (form.querySelector("button[type=submit]"));
    const label = btn.textContent;
    btn.disabled = true; msg.className = "muted"; msg.textContent = "";
    if (btn.dataset.busy) btn.textContent = btn.dataset.busy;
    try { const t = await fn(); if (t) msg.textContent = t; } catch (err) { msg.className = "fail"; msg.textContent = err.message; }
    btn.disabled = false; btn.textContent = label;
  };
}
async function pageLogin() {
  const setup = await get("/auth/setup").catch(() => ({ needed: false }));
  if (setup.needed) { location.hash = "#/setup"; return; }
  authPage("Welcome back", "Sign in to continue.", `<form class="form">
    <label>Email <input id="email" type="email" autocomplete="email" autofocus required></label>
    <label>Password <input id="password" type="password" autocomplete="current-password" required></label>
    <button class="primary wide" type="submit" data-busy="Signing in…">Sign in</button></form>`,
  `<a href="#/forgot">Forgot your password?</a> · No account? Ask the studio owner to add you.
    <br><a href="/terms" target="_blank" rel="noopener">Terms of use and content policy</a>`);
  onSubmit(async () => {
    await post("/auth/login", { email: field("email").value, password: field("password").value });
    await loadMe(); location.hash = "#/";
    return "";
  });
}
/** First visit, no owner yet (specs/008 FR-118): the owner account is made here, with the setup code. */
async function pageSetup() {
  const setup = await get("/auth/setup").catch(() => ({ needed: false }));
  if (!setup.needed) { location.hash = "#/login"; return; }
  authPage("Create the owner account", "The studio has no owner yet. This account owns it: it alone sees Admin and AI accounts and can invite other people. Already signed up with this email? Use the same password: that account becomes the owner.", `<form class="form">
    <label>Email <input id="email" type="email" autocomplete="email" autofocus required></label>
    <label>Password <span class="hint">At least 10 characters.</span>
      <input id="password" type="password" autocomplete="new-password" minlength="10" required></label>
    <label>Password again <input id="password2" type="password" autocomplete="new-password" required></label>
    <button class="primary wide" type="submit" data-busy="Creating…">Create the owner account</button></form>`,
  `<a href="/terms" target="_blank" rel="noopener">Terms of use and content policy</a>`);
  onSubmit(async () => {
    if (field("password").value !== field("password2").value) throw new Error("The two passwords differ.");
    await post("/auth/setup", { email: field("email").value, password: field("password").value });
    await loadMe(); location.hash = "#/admin/claude";
    return "";
  });
}
async function pageVerify(token) {
  authPage("Confirm your email", "", "");
  const msg = document.getElementById("msg");
  try {
    await post("/auth/verify", { token });
    msg.innerHTML = 'Your email is confirmed. <a href="#/login">Log in</a> to make your first film.';
    if (ME) { await loadMe(); msg.innerHTML = 'Your email is confirmed. <a href="#/new">Make your first film</a>.'; }
  } catch (e) { msg.className = "fail"; msg.textContent = e.message; }
}
async function pageForgot() {
  authPage("Forgot your password", "We send a link to choose a new one.", `<form class="form">
    <label>Email <input id="email" type="email" autocomplete="email" required></label>
    <button class="primary" type="submit">Send the link</button></form>`, `<p><a href="#/login">Back to log in</a></p>`);
  onSubmit(async () => {
    await post("/auth/forgot", { email: field("email").value });
    return "If this email has an account, the link is on its way. It works for 1 hour.";
  });
}
async function pageReset(token) {
  authPage("Choose a new password", "You are logged out everywhere after the change.", `<form class="form">
    <label>New password <span class="hint">At least 10 characters.</span>
      <input id="password" type="password" autocomplete="new-password" minlength="10" required></label>
    <button class="primary" type="submit">Save the password</button></form>`, `<p><a href="#/login">Log in</a></p>`);
  onSubmit(async () => {
    await post("/auth/reset", { token, password: field("password").value });
    $app.querySelector("form").remove();
    return "Your password is changed. Log in with the new one.";
  });
}

async function pageNew() {
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  const [lib, mine] = await Promise.all([get("/library"), get("/styles")]);
  const q = ME.quota.films, left = Math.max(0, q.limit - q.used), max = ME.limits?.film_max_seconds || 60;
  const want = params.get("style") || "";
  const opt = (slug, name, img) => `<label><input type="radio" name="style" value="${esc(slug)}" ${slug === want ? "checked" : ""} required>
      ${img ? `<img src="${img}" alt="" loading="lazy">` : `<div class="poster-ph"><span>${esc(name)}</span></div>`}<span>${esc(name)}</span></label>`;
  const cards = [...mine.styles.map((s) => opt(s.slug, `${s.en || s.slug} (yours)`, s.has_styleframe ? `${API}/styles/${esc(s.slug)}/styleframe` : "")),
    ...(lib.styles || []).map((s) => opt(s.slug, s.en, s.has_poster ? `${API}/library/styles/${esc(s.slug)}/poster` : ""))].join("");
  $app.innerHTML = `${head("Make", "New film", `You have ${left} of ${q.limit} films left this month.`)}
    ${!ME.verified ? `<p class="notice">Confirm your email first: open the link we sent to ${esc(ME.email)}.</p>` : ""}
    ${left === 0 ? `<p class="notice">You have used all your films for this month. They come back on ${when(ME.quota.resets_at)}.</p>` : ""}
    <form class="form panel">
      <label>Style <span class="hint">Pick the look of the film. <a href="#/library">See the whole library</a>.</span></label>
      <div class="pick" role="radiogroup" aria-label="Style">${cards}</div>
      <label>Your idea <span class="hint">What happens in the film, who is in it, the mood. Up to 2000 characters.</span>
        <textarea id="idea" minlength="3" maxlength="2000" required placeholder="A late-night bánh mì stall in Saigon, told by the old man who runs it."></textarea></label>
      <label>Length in seconds <span class="hint">Up to ${max} seconds.</span>
        <input id="seconds" type="number" min="5" max="${max}" value="${Math.min(30, max)}" required></label>
      <label class="check"><input id="treat" type="checkbox"> <span>Let me review the treatment (the written plan) before the picture is made</span></label>
      <div><button class="primary" type="submit" ${left === 0 || !ME.verified ? "disabled" : ""}>Make the film (uses 1 credit)</button></div>
    </form><p id="msg" class="muted" role="status"></p>`;
  $app.querySelector("input[name=style]:checked")?.closest("label")?.scrollIntoView({ block: "nearest" });
  onSubmit(async () => {
    const style = /** @type {HTMLInputElement | null} */ ($app.querySelector("input[name=style]:checked"));
    if (!style) throw new Error("Pick a style first.");
    const j = await post("/jobs", { kind: "film", style: style.value, idea: field("idea").value.trim(),
      seconds: Number(field("seconds").value), review_treatment: field("treat").checked });
    await loadMe();
    location.hash = `#/jobs/${j.id}`;
    return "";
  });
}

async function pageLearn() {
  const L = ME.limits, q = ME.quota.learns, left = Math.max(0, q.limit - q.used);
  $app.innerHTML = `${head("Learn", "Learn a style", `The studio watches every frame of a few videos, measures the look and sound,
      and writes a style you can make films with. You review it twice on the way. You have ${left} of ${q.limit} learns left this month.`)}
    ${left === 0 ? `<p class="notice">You have used all your learns for this month. They come back on ${when(ME.quota.resets_at)}.</p>` : ""}
    <form class="form panel" id="learn-form">
      <div class="row" role="radiogroup" aria-label="Source">
        <label class="check"><input type="radio" name="src" value="youtube" checked> <span>From a YouTube channel</span></label>
        <label class="check"><input type="radio" name="src" value="upload"> <span>From my own videos</span></label></div>
      <div id="src-youtube" class="form">
        <label>Channel address <span class="hint">For example https://www.youtube.com/@channel-name</span>
          <input id="channel" type="text" inputmode="url" autocomplete="off" placeholder="https://www.youtube.com/@channel-name"></label>
        <label>Number of recent videos <span class="hint">1 to ${L.learn_max_videos}.</span>
          <input id="count" type="number" min="1" max="${L.learn_max_videos}" value="${Math.min(5, L.learn_max_videos)}"></label>
        <label class="check"><input id="rights" type="checkbox"> <span>${esc(L.rights_text)}</span></label>
      </div>
      <div id="src-upload" class="form" hidden>
        <label>Videos <span class="hint">Up to ${L.learn_max_videos} files, ${L.upload_max_mb} MB and ${L.upload_max_minutes} minutes each.
          They are used only for learning, never shown again, and deleted when the job ends.</span>
          <input id="files" type="file" accept="video/*" multiple></label>
        <ul id="up-list" class="uploads"></ul>
      </div>
      <div><button class="primary" type="submit" ${left === 0 ? "disabled" : ""}>Learn the style (uses 1 learn)</button></div>
    </form><p id="msg" class="muted" role="status"></p>`;
  const show = () => {
    const src = /** @type {HTMLInputElement} */ ($app.querySelector("input[name=src]:checked")).value;
    document.getElementById("src-youtube").hidden = src !== "youtube";
    document.getElementById("src-upload").hidden = src !== "upload";
  };
  $app.querySelectorAll("input[name=src]").forEach((r) => r.addEventListener("change", show));
  onSubmit(async () => {
    const src = /** @type {HTMLInputElement} */ ($app.querySelector("input[name=src]:checked")).value;
    let body;
    if (src === "youtube") {
      if (!field("rights").checked) throw new Error(ERR.rights_required);
      body = { kind: "learn", source: "youtube", channel: field("channel").value.trim(), count: Number(field("count").value), rights_confirmed: true };
    } else {
      const files = Array.from(field("files").files || []);
      if (!files.length) throw new Error("Choose at least one video.");
      if (files.length > L.learn_max_videos) throw new Error(ERR.too_many_videos);
      const list = document.getElementById("up-list"), ids = [];
      list.innerHTML = files.map((f, i) => `<li>${esc(f.name)} <progress id="up-${i}" max="100" value="0"></progress></li>`).join("");
      for (const [i, f] of files.entries()) ids.push(await uploadFile(f, /** @type {HTMLProgressElement} */ (document.getElementById(`up-${i}`))));
      body = { kind: "learn", source: "upload", uploads: ids };
    }
    const j = await post("/jobs", body);
    await loadMe();
    location.hash = `#/jobs/${j.id}`;
    return "";
  });
}
/** Send one video with a progress bar; resolves to its upload id. */
function uploadFile(file, bar) {
  return new Promise((resolve, reject) => {
    const x = new XMLHttpRequest(), form = new FormData();
    form.append("file", file);
    x.open("POST", API + "/uploads");
    x.setRequestHeader("X-Studio", "1");
    x.upload.onprogress = (e) => { if (e.lengthComputable) bar.value = Math.round((100 * e.loaded) / e.total); };
    x.onload = () => {
      let body = {};
      try { body = JSON.parse(x.responseText); } catch { /* not JSON */ }
      if (x.status === 201) { bar.value = 100; resolve(/** @type {any} */ (body).upload_id); }
      else reject(new Error(`${file.name}: ${errText(body, x.status)}`));
    };
    x.onerror = () => reject(new Error(`${file.name}: the upload was interrupted.`));
    x.send(form);
  });
}

// ---------- Settings, owner only (specs/007 US3; tabs and Users after neb-creative-tool, specs/008) ----------
const SETTING = [
  ["quota_films_default", "Films per month (default)", "int"],
  ["quota_learns_default", "Learns per month (default)", "int"], ["film_max_seconds", "Longest film (seconds)", "int"],
  ["learn_max_videos", "Videos per learn", "int"], ["upload_max_mb", "Upload size (MB)", "int"],
  ["upload_max_minutes", "Upload length (minutes)", "int"], ["job_token_cap", "Token limit per job", "int"],
  ["concurrency", "Jobs at the same time", "int"],
  ["review_timeout_days", "Stop a job after waiting (days)", "int"], ["model", "Claude model", "text"],
];
const SETTINGS_TABS = [["general", "General"], ["users", "Users"], ["usage", "Usage"]];
const ROLE = { admin: "Owner", customer: "Member" };
const usd = (v) => `$${Number(v || 0).toFixed(2)}`;
async function pageSettings(tab = "general") {
  if (ME.role !== "admin") { $app.innerHTML = `<p class="error">This page is for the studio owner.</p>`; return; }
  if (!SETTINGS_TABS.some(([k]) => k === tab)) tab = "general";
  const top = `${head("Owner", "Settings", 'How the studio is run. The AI plans themselves are on the <a href="#/admin/claude">AI accounts</a> page.')}
    <div class="tabs" role="tablist">${SETTINGS_TABS.map(([k, label]) =>
      `<a role="tab" href="#/settings/${k}" class="${k === tab ? "on" : ""}" aria-selected="${k === tab}">${label}</a>`).join("")}</div>`;
  if (tab === "users") return settingsUsers(top);
  if (tab === "usage") return settingsUsage(top);
  const st = await get("/admin/settings");
  const input = ([k, label, t]) => `<label>${label}<input id="s-${k}" type="${t === "text" ? "text" : "number"}" ${t === "num" ? 'step="0.01"' : ""} value="${esc(st[k])}"></label>`;
  $app.innerHTML = `${top}<section class="panel card-pad"><h2>Studio</h2><p class="muted">Limits for every member, and how many films run at once.</p>
    <form class="form" id="settings"><div class="admin-grid">${SETTING.map(input).join("")}</div>
      <div><button class="primary" type="submit">Save settings</button></div></form><p id="msg" class="muted" role="status"></p></section>`;
  onSubmit(async () => {
    const data = {};
    for (const [k, , t] of SETTING) {
      const el = field(`s-${k}`);
      data[k] = t === "text" ? el.value.trim() : Number(el.value);
    }
    await send("PUT", "/admin/settings", data);
    return "Saved.";
  });
}

/** Settings → Users: people who can sign in (specs/008 FR-112). */
async function settingsUsers(top) {
  const { users, me } = await get("/admin/users");
  const row = (u) => {
    const self = u.id === me;
    const menu = [
      '<button data-act="password">Reset password</button>',
      !self && `<button data-act="role">${u.role === "admin" ? "Make member" : "Make owner"}</button>`,
      `<button data-act="signout">Sign out everywhere</button>`,
      !self && `<button data-act="toggle">${u.disabled ? "Turn on" : "Turn off"}</button>`,
      !self && '<button data-act="remove" class="danger">Remove</button>',
    ].filter(Boolean).join("");
    return `<li data-id="${esc(u.id)}" data-email="${esc(u.email)}" data-role="${u.role}" data-disabled="${u.disabled}">
      <div class="u-name"><strong title="${esc(u.email)}">${esc(u.email)}</strong>${self ? ' <span class="muted">(you)</span>' : ""}</div>
      <div>${pill(ROLE[u.role] || u.role, u.role === "admin" ? "accent" : "")}${u.disabled ? pill("Off", "bad") : ""}</div>
      <div class="muted"><span class="m-label">Last sign-in: </span>${u.last_login_at ? when(u.last_login_at) : "Never"}</div>
      <div class="num" title="Browsers signed in now">${u.sessions}<span class="m-label"> browser${u.sessions === 1 ? "" : "s"} signed in</span></div>
      <div><details class="menu"><summary aria-label="Actions for ${esc(u.email)}">⋯</summary><div class="menu-list">${menu}</div></details></div></li>`;
  };
  $app.innerHTML = `${top}<section class="panel card-pad">
      <h2>People who can sign in</h2>
      <p class="muted"><strong>Owner</strong>: everything, including AI accounts and Settings. <strong>Member</strong>: makes films and learns styles, but cannot see AI accounts or Settings.</p>
      <p><button class="primary" id="add-user">Add user</button></p>
      <form id="user-form" class="user-form" hidden>
        <input id="u-email" type="email" placeholder="Email" aria-label="Email" autocomplete="off" required>
        <input id="u-password" type="text" placeholder="Password (at least 10 characters)" aria-label="Password" autocomplete="off" minlength="10" required>
        <select id="u-role" aria-label="Role"><option value="customer">Member</option><option value="admin">Owner</option></select>
        <button class="primary" type="submit">Add</button><button type="button" id="u-cancel">Cancel</button>
      </form>
      <p id="msg" class="muted" role="status"></p>
      <ul class="users"><li class="u-head"><div>User</div><div>Role</div><div>Last sign-in</div><div class="num">Browsers</div><div></div></li>${users.map(row).join("")}</ul>
      <p class="muted small">Give each person their password yourself. They can change it on their account page.</p></section>`;
  const msg = document.getElementById("msg");
  const act = async (fn, done = "") => {
    msg.className = "muted"; msg.textContent = "";
    try { await fn(); await route(); const m = document.getElementById("msg"); if (m && done) m.textContent = done; }
    catch (e) { msg.className = "error"; msg.textContent = e.message; }
  };
  const form = /** @type {HTMLFormElement} */ (document.getElementById("user-form"));
  const addBtn = document.getElementById("add-user");
  addBtn.addEventListener("click", () => { form.hidden = false; addBtn.hidden = true; field("u-email").focus(); });
  document.getElementById("u-cancel").addEventListener("click", () => { form.hidden = true; addBtn.hidden = false; });
  form.onsubmit = (e) => {
    e.preventDefault();
    const email = field("u-email").value.trim();
    act(() => post("/admin/users", { email, password: field("u-password").value,
      role: /** @type {HTMLSelectElement} */ (document.getElementById("u-role")).value }), `Added ${email}. Give them the password.`);
  };
  (/** @type {NodeListOf<HTMLButtonElement>} */ ($app.querySelectorAll(".users button[data-act]"))).forEach((b) => b.addEventListener("click", () => {
    const li = /** @type {HTMLElement} */ (b.closest("li")), id = encodeURIComponent(li.dataset.id), email = li.dataset.email;
    b.closest("details")?.removeAttribute("open");
    const a = b.dataset.act;
    if (a === "password") {
      const pw = prompt(`New password for ${email} (at least 10 characters). They are signed out everywhere.`);
      if (pw) act(() => send("PUT", `/admin/users/${id}`, { password: pw }), `New password set for ${email}.`);
    }
    if (a === "role") {
      const role = li.dataset.role === "admin" ? "customer" : "admin";
      if (confirm(`Make ${email} ${role === "admin" ? "an owner? Owners see AI accounts and Settings." : "a member?"}`))
        act(() => send("PUT", `/admin/users/${id}`, { role }));
    }
    if (a === "signout") act(() => post(`/admin/users/${id}/signout`), `${email} is signed out everywhere.`);
    if (a === "toggle") {
      const off = li.dataset.disabled !== "true";
      if (!off || confirm(`Turn off ${email}? They are signed out and their running jobs stop.`))
        act(() => send("PUT", `/admin/users/${id}`, { disabled: off }));
    }
    if (a === "remove" && confirm(`Remove ${email}? They are signed out now; their films and styles are erased within 30 days.`))
      act(() => send("DELETE", `/admin/users/${id}`));
  }));
}

/** Settings → Usage: films, learns, tokens and storage per member; calls and tokens per Claude account, member and
 *  day, all from the studio's own record of each call (specs/008 US4). USD only for the API-key part. */
async function settingsUsage(top) {
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  const q = params.get("q") || "";
  const [acc, use] = await Promise.all([get("/admin/accounts?q=" + encodeURIComponent(q)), get("/admin/usage")]);
  const [claude] = await Promise.all([get("/admin/claude")]);
  const money = use.cost_usd_total > 0;                     // USD only when calls went through the API key (FR-117)
  const cost = (v) => (money ? `<td class="num">${usd(v)}</td>` : "");
  const via = (v) => {
    if (v === "api") return "API key";
    const a = claude.accounts.find((x) => `plan:${x.slot}` === v);
    return `${claudeLabel(Number(v.split(":")[1]))}${a && a.email ? ` · ${esc(a.email)}` : ""}`;
  };
  const rows = acc.accounts.map((a) => `<tr data-id="${esc(a.id)}"><td>${esc(a.email)}${a.role === "admin" ? " (owner)" : ""}</td>
      <td>${a.quota.films.used} / <input type="number" min="0" data-f="quota_films" value="${a.quota_films ?? ""}" placeholder="${a.quota.films.limit}" aria-label="Films limit"></td>
      <td>${a.quota.learns.used} / <input type="number" min="0" data-f="quota_learns" value="${a.quota_learns ?? ""}" placeholder="${a.quota.learns.limit}" aria-label="Learns limit"></td>
      <td class="num">${num(a.tokens_month, 0)}</td><td class="num">${num(a.storage_mb, 1)} MB</td></tr>`).join("");
  const table = (head1, list, first) => `<div class="table-wrap"><table><tr><th>${head1}</th><th>Jobs</th><th>Calls</th><th>Tokens</th>${money ? "<th>Cost</th>" : ""}</tr>
      ${list.map((d) => `<tr><td>${first(d)}</td><td class="num">${d.jobs}</td><td class="num">${num(d.calls, 0)}</td><td class="num">${num(d.tokens, 0)}</td>${cost(d.cost_usd)}</tr>`).join("")
        || `<tr><td colspan="${money ? 5 : 4}" class="muted">No calls yet.</td></tr>`}</table></div>`;
  $app.innerHTML = `${top}<p class="lead">Last 30 days: ${num(use.calls_total, 0)} Claude calls · ${num(use.tokens_total, 0)} tokens${money ? ` · ${usd(use.cost_usd_total)} through the API key` : ""} · storage ${num(use.storage_mb_total, 1)} MB</p>
    <h2>Members</h2>
    <div class="row filters"><label class="search"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
      <input id="acc-q" type="search" placeholder="Search by email" value="${esc(q)}" aria-label="Search by email"></label></div>
    <p class="muted">Films and learns: used / own limit (empty = the default on General). Tokens: this month. To turn someone off, use Users.</p>
    <div class="table-wrap"><table><tr><th>Email</th><th>Films</th><th>Learns</th><th>Tokens this month</th><th>Storage</th></tr>${rows}</table></div>
    <p id="acc-msg" class="muted" role="status"></p>
    <h2>Per Claude account</h2>${table("Account", use.by_claude, (d) => via(d.via))}
    <h2>Per member</h2>${table("Member", use.by_account, (d) => esc(d.email || "(deleted)"))}
    <h2>Per day</h2>${table("Day", use.days.slice().reverse(), (d) => esc(d.day))}`;
  const msg = document.getElementById("acc-msg");
  (/** @type {NodeListOf<HTMLInputElement>} */ ($app.querySelectorAll("tr[data-id] input[data-f]"))).forEach((el) => el.addEventListener("change", async () => {
    const id = /** @type {HTMLElement} */ (el.closest("tr")).dataset.id, f = el.dataset.f;
    const body = el.value === "" ? { [f === "quota_films" ? "use_default_films" : "use_default_learns"]: true } : { [f]: Number(el.value) };
    try { await send("PUT", `/admin/accounts/${encodeURIComponent(id)}`, body); msg.className = "muted"; msg.textContent = "Saved."; }
    catch (e) { msg.className = "fail"; msg.textContent = e.message; }
  }));
  const qi = field("acc-q");
  let t = 0;
  qi.addEventListener("input", () => {
    clearTimeout(t);
    t = setTimeout(() => {
      history.replaceState(null, "", "#/settings/usage?q=" + encodeURIComponent(qi.value));
      route().then(() => { const n = field("acc-q"); n.focus(); n.setSelectionRange(n.value.length, n.value.length); });
    }, 400);
  });
}

// ---------- AI accounts (specs/008; layout from neb-creative-tool's Accounts page) ----------
const MAX_CLAUDE = 5;
const claudeLabel = (slot) => (slot > 1 ? `Claude #${slot}` : "Claude");
const pill = (text, tone = "", extra = "") => `<span class="badge ${tone ? `t-${tone}` : ""} ${extra}">${esc(text)}</span>`;
/** "in 3 h 20 min (Tue 17:50)", or a date when it is days away. */
function resetLabel(iso) {
  const at = new Date(iso).getTime(), ms = at - Date.now();
  const clock = new Date(at).toLocaleString("en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit" });
  if (ms <= 0) return clock;
  const total = Math.round(ms / 60_000), h = Math.floor(total / 60), m = total % 60;
  if (h >= 48) return new Date(at).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  return `in ${h ? `${h} h ` : ""}${m} min (${clock})`;
}
/** One window of a plan: how full it is and when it resets. Amber from 75 %, red from 90 % (FR-119). */
function quotaBar(label, w) {
  const past = w && w.resets_at && new Date(w.resets_at).getTime() < Date.now();
  const pct = !w || w.percent == null ? null : past ? 0 : Math.max(0, Math.min(100, w.percent));
  const tone = pct == null || past ? "none" : pct >= 90 ? "bad" : pct >= 75 ? "warn" : "ok";
  const reset = w && w.resets_at ? (past ? "reset since" : `resets ${resetLabel(w.resets_at)}`) : "";
  return `<div class="quota"><span class="q-label">${label}</span>
    <span class="q-track"><span class="q-fill q-${tone}" style="width:${pct ?? 0}%"></span></span>
    <span class="q-pct">${pct == null ? "?" : `${Math.round(pct)}%`}</span>${reset ? `<span class="muted">${esc(reset)}</span>` : ""}</div>`;
}
function readAgo(iso) {
  const min = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  return min < 1 ? "read just now" : min < 90 ? `read ${min} min ago` : `read ${when(iso)}`;
}
async function pageClaude() {
  if (ME.role !== "admin") { $app.innerHTML = `<p class="error">This page is for the studio admin.</p>`; return; }
  const c = await get("/admin/claude");
  const list = c.accounts, login = c.login;
  const live = list.filter((a) => a.state !== "signed_out" && a.state !== "needs_signin" && !a.same_as);
  const rested = (a) => a.state === "limited" && a.rest_until && new Date(a.rest_until).getTime() > Date.now();
  const ready = live.filter((a) => !rested(a)).length, resting = live.filter(rested).length;
  const needs = list.filter((a) => a.state === "needs_signin").length;
  const several = list.length > 1;
  const canAdd = list[0].state !== "signed_out" && list.length < MAX_CLAUDE && !login;
  const row = (a) => {
    const name = a.email || claudeLabel(a.slot);
    const title = several && a.email ? `${claudeLabel(a.slot)} · ${a.email}` : name;
    const waiting = login && login.slot === a.slot;
    const signedIn = a.state === "signed_in" || a.state === "limited";
    const badges = signedIn
      ? `${pill("Signed in", "ok")}${a.plan ? pill(a.plan) : ""}${rested(a) ? pill("At its limit", "bad") : ""}`
      : waiting ? pill("Signing in", "accent", "pulse") : a.state === "needs_signin" ? pill("Needs sign-in", "bad") : pill("Not signed in");
    const meta = rested(a) ? `Back ${resetLabel(a.rest_until)}. Calls use the other accounts until then.`
      : a.state === "needs_signin" ? "Its sign-in stopped working: sign in again." : !signedIn && !waiting && a.slot === 1 && !several
        ? (c.api_key ? "The API key is used until you sign in." : "Jobs cannot run until you sign in.") : "";
    const menu = [signedIn && '<button data-act="login">Sign in again</button>', a.state !== "signed_out" && '<button data-act="logout" class="danger">Sign out</button>',
      a.slot > 1 && '<button data-act="remove" class="danger">Remove</button>'].filter(Boolean).join("");
    return `<li data-slot="${a.slot}"><div class="acc-head">
        <div class="acc-name"><h3 title="${esc(name)}">${esc(title)}</h3>${badges}</div>
        <div class="acc-actions">${signedIn ? "" : `<button class="primary" data-act="login" ${waiting ? "disabled" : ""}>${waiting ? "Signing in…" : "Sign in"}</button>`}
          ${menu ? `<details class="menu"><summary aria-label="More for ${esc(name)}">⋯</summary><div class="menu-list">${menu}</div></details>` : ""}</div></div>
      ${meta ? `<p class="acc-meta">${esc(meta)}</p>` : ""}
      ${a.same_as ? `<p class="notice warn">Same Claude account as ${claudeLabel(a.same_as)}: it shares those limits and adds nothing. Sign out here and sign in to another account.</p>` : ""}
      ${a.plan_warning ? `<p class="notice warn">This is a ${esc(a.plan)} plan, not Pro or Max: its limits are small for making films.</p>` : ""}
      ${waiting ? `<div class="signin-box"><p>Sign in with a Claude Pro or Max account in the tab that opened. No tab opened?
          <a href="${esc(login.url)}" target="_blank" rel="noopener noreferrer">Open the sign-in</a>. At the end Claude shows a code: paste it here.</p>
          <form id="code-form" class="code-row"><input id="code" type="text" autocomplete="off" spellcheck="false" placeholder="Code" aria-label="Code" required>
          <button type="submit">Send</button></form><p class="muted small">The link works for 10 minutes.</p></div>` : ""}
      ${signedIn && !a.same_as ? `<div class="usage">${a.usage ? `${quotaBar("5-hour", a.usage.five_hour)}${quotaBar("Weekly", a.usage.seven_day)}
          <p class="muted small">${readAgo(a.usage.at)} · shared with Claude Code and claude.ai</p>`
        : '<p class="muted small">Usage not read yet: it is noted with the next call.</p>'}
        <p class="muted small">The studio used ${num(a.tokens_5h, 0)} tokens on it in the last 5 hours.</p></div>` : ""}
    </li>`;
  };
  $app.innerHTML = `${head("Studio", "AI accounts", "The AI plans and keys the studio makes films with.")}
    <div class="summary panel"><strong>${list.length} account${list.length === 1 ? "" : "s"}</strong>${pill(`${ready} ready`, "ok")}
      ${resting ? pill(`${resting} resting`, "warn") : ""}${needs ? pill(`${needs} need${needs === 1 ? "s" : ""} signing in`, "bad") : ""}
      <span class="summary-end">API key: ${c.api_key ? "set, used only as a fallback" : "not set"}</span></div>
    ${c.ready ? "" : '<p class="error">No Claude account signed in. Jobs cannot run.</p>'}
    <section class="provider panel" id="claude-plan">
      <div class="provider-head"><div><div class="acc-name"><h2>Claude · plan</h2>${live.length ? pill(live.length > 1 ? `${live.length} signed in` : "Signed in", "ok") : pill("Not signed in")}</div>
        <p class="muted">Films, styles and the content check run on your Claude Pro or Max plan. When an account reaches its limit, calls move to the next signed-in account.</p></div>
        <button id="refresh">Check again</button></div>
      <p id="msg" class="muted" role="status"></p>
      <ul class="acc-rows">${list.map(row).join("")}</ul>
      <div class="provider-foot">
        ${canAdd ? '<div class="foot-row"><button id="add">Add account</button><span class="muted">Sign in with a different Claude account: calls then rotate over them.</span></div>' : ""}
        <details class="how"><summary>How it works</summary><div>
          <p>The sign-in is Claude Code's own, kept on this server in the data folder (claude/). It never goes into a job's sandbox: jobs reach Claude only through the studio.</p>
          <p>Calls count against the plan's limits, shared with Claude Code and claude.ai on the same account.</p>
          <p>Several accounts: each call goes to the one the studio used least in the last 5 hours, and moves on when one is at its limit.</p>
          <p>An API key (ANTHROPIC_API_KEY on the server) is used only when no Claude account can take a call.</p></div></details>
      </div></section>`;
  const msg = document.getElementById("msg");
  const act = async (fn, busy = "") => {
    msg.className = "muted"; msg.textContent = busy;
    try { await fn(); await route(); } catch (e) { msg.className = "error"; msg.textContent = e.message; }
  };
  (/** @type {NodeListOf<HTMLButtonElement>} */ ($app.querySelectorAll("li[data-slot] button[data-act]"))).forEach((b) => b.addEventListener("click", () => {
    const slot = /** @type {HTMLElement} */ (b.closest("li")).dataset.slot, label = claudeLabel(Number(slot));
    b.closest("details")?.removeAttribute("open");
    if (b.dataset.act === "login") act(async () => {
      const r = await post(`/admin/claude/accounts/${slot}/login`);
      window.open(r.url, "_blank", "noopener");
    }, "Starting the sign-in…");
    if (b.dataset.act === "logout" && confirm(`Sign out of ${label}? The studio stops using it. Your Claude account itself is not touched.`))
      act(() => post(`/admin/claude/accounts/${slot}/logout`));
    if (b.dataset.act === "remove" && confirm(`Remove ${label}? It is signed out and taken off the list. Your Claude account itself is not touched.`))
      act(() => send("DELETE", `/admin/claude/accounts/${slot}`));
  }));
  document.getElementById("add")?.addEventListener("click", () => act(async () => {
    const a = await post("/admin/claude/accounts");
    const r = await post(`/admin/claude/accounts/${a.slot}/login`);
    window.open(r.url, "_blank", "noopener");
  }, "Starting the sign-in…"));
  document.getElementById("refresh").addEventListener("click", () => act(() => post("/admin/claude/refresh"), "Checking…"));
  const form = /** @type {HTMLFormElement} */ (document.getElementById("code-form"));
  if (form && login) {
    form.onsubmit = (e) => {
      e.preventDefault();
      const btn = /** @type {HTMLButtonElement} */ (form.querySelector("button"));
      btn.disabled = true; btn.textContent = "Sending…";
      act(() => post(`/admin/claude/accounts/${login.slot}/code`, { code: field("code").value.trim() }), "Signing in…")
        .finally(() => { btn.disabled = false; btn.textContent = "Send"; });
    };
    field("code").focus();
  }
}
document.addEventListener("click", (e) => {      // close an open ⋯ menu when clicking elsewhere
  document.querySelectorAll("details.menu[open]").forEach((d) => { if (!d.contains(/** @type {Node} */ (e.target))) d.removeAttribute("open"); });
});

// ---------- account (US4) ----------
async function pageAccount() {
  ME = await get("/me");
  drawAccount();
  const f = ME.quota.films, l = ME.quota.learns;
  $app.innerHTML = `${head("You", "Account", esc(ME.email))}
    <div class="panel"><p class="section-title">This month</p>
      <p>Films: <strong>${Math.max(0, f.limit - f.used)}</strong> of ${f.limit} left · Learns: <strong>${Math.max(0, l.limit - l.used)}</strong> of ${l.limit} left</p>
      <p class="muted">They come back on ${when(ME.quota.resets_at)}.</p></div>
    <h2>Email</h2>
    <div class="panel"><label class="check"><input id="notify" type="checkbox" ${ME.email_notify ? "checked" : ""}>
      <span>Email me when a job is done, fails, or needs my answer</span></label><p id="notify-msg" class="muted" role="status"></p></div>
    <h2>Password</h2>
    <form class="form panel" id="pw-form">
      <label>Current password <input id="old" type="password" autocomplete="current-password" required></label>
      <label>New password <span class="hint">At least 10 characters.</span>
        <input id="new" type="password" autocomplete="new-password" minlength="10" required></label>
      <div><button class="primary" type="submit">Change password</button></div>
      <p id="pw-msg" class="muted" role="status"></p></form>
    <h2>Delete account</h2>
    <form class="form panel" id="del-form">
      <p class="muted" style="margin:0">You are logged out at once. Your films, styles, uploads and records are deleted for good within 30 days.</p>
      <label>Type your password to confirm <input id="del-pw" type="password" autocomplete="current-password" required></label>
      <div><button class="danger" type="submit">Delete my account</button></div>
      <p id="del-msg" class="muted" role="status"></p></form>`;
  const notify = field("notify"), nmsg = document.getElementById("notify-msg");
  notify.onchange = async () => {
    try { ME = await send("PUT", "/me", { email_notify: notify.checked }); nmsg.className = "muted"; nmsg.textContent = "Saved."; }
    catch (e) { nmsg.className = "fail"; nmsg.textContent = e.message; notify.checked = !notify.checked; }
  };
  /** Wire one form of this page to `fn`; its message goes under the form. */
  const wire = (id, msgId, fn) => {
    const form = /** @type {HTMLFormElement} */ (document.getElementById(id)), msg = document.getElementById(msgId);
    form.onsubmit = async (e) => {
      e.preventDefault();
      const btn = /** @type {HTMLButtonElement} */ (form.querySelector("button[type=submit]"));
      btn.disabled = true; msg.className = "muted"; msg.textContent = "";
      try { msg.textContent = await fn(); form.reset(); } catch (err) { msg.className = "fail"; msg.textContent = err.message; }
      btn.disabled = false;
    };
  };
  wire("pw-form", "pw-msg", async () => {
    await send("PUT", "/me", { old_password: field("old").value, password: field("new").value });
    return "Your password is changed.";
  });
  wire("del-form", "del-msg", async () => {
    if (!confirm("Delete your account and everything in it? This cannot be undone.")) return "";
    await send("DELETE", "/me", { password: field("del-pw").value });
    ME = null; drawAccount();
    authPage("Account deleted", "", `<p>Your account is closed and everything in it is deleted within 30 days. We sent you an email about it.</p>`);
    return "";
  });
}

async function loadMe() {
  try { ME = await get("/me"); } catch { ME = null; }
  drawAccount();
  return ME;
}
const ICON_UPDOWN = '<svg viewBox="0 0 24 24"><path d="M8 9l4-4 4 4M8 15l4 4 4-4"/></svg>';
/** The signed-in person (layout from neb-creative-tool's sidebar): a card that opens a small menu —
 *  their account, and Log out. In the sidebar on a computer, in the top bar on a phone. */
function userMenu(where) {
  const f = ME.quota.films, owner = ME.role === "admin";
  const films = `${Math.max(0, f.limit - f.used)}/${f.limit} films left this month`;
  const live = document.getElementById("live");
  return `<details class="menu user-menu ${where === "side" ? "up" : ""}"><summary class="user-btn" aria-label="Account menu">
      <span class="avatar">${esc(ME.email[0].toUpperCase())}</span>
      <span class="who"><strong>${esc(ME.email)}</strong><small class="credits">${films}</small></span>${ICON_UPDOWN}</summary>
    <div class="menu-list">
      <div class="menu-head"><strong>${esc(ME.email)}</strong><small>${owner ? "Owner" : "Member"}${where === "side"
        ? ` · <span id="live" class="${live?.className || "live"}">${esc(live?.textContent || "Connecting…")}</span>` : ""}</small></div>
      <a href="#/account">Your account</a>
      ${owner && where === "top" ? '<a href="#/admin/claude">AI accounts</a><a href="#/settings">Settings</a>' : ""}
      <button class="danger" data-logout>Log out</button></div></details>`;
}
function drawAccount() {
  const bar = document.getElementById("acct"), side = document.getElementById("owner");
  document.body.classList.toggle("guest", MODE === "online" && !ME);
  bar.hidden = !(MODE === "online" && ME);
  (/** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll(".admin-only"))).forEach((el) => (el.hidden = !(ME && ME.role === "admin")));
  if (bar.hidden) return;
  side.classList.add("signed");
  side.innerHTML = userMenu("side");
  bar.innerHTML = userMenu("top");
  document.querySelectorAll("[data-logout]").forEach((b) => b.addEventListener("click", async () => {
    try { await post("/auth/logout"); } catch { /* already logged out */ }
    location.reload();                 // the sidebar, the menus and live updates start over
  }));
  document.querySelectorAll(".user-menu a").forEach((a) => a.addEventListener("click", () => a.closest("details").removeAttribute("open")));
}

// ---------- router, live updates, waiting badge, notifications ----------
/** @type {Array<[RegExp, (id?: string) => Promise<void>, string]>} */
const routes = [
  [/^#\/?(\?.*)?$/, pageJobs, "jobs"], [/^#\/jobs\/([^/?]+)$/, pageJob, "jobs"], [/^#\/reviews\/([^/?]+)$/, pageReview, "jobs"],
  [/^#\/films$/, pageFilms, "films"], [/^#\/films\/([^/?]+)$/, pageFilm, "films"],
  [/^#\/sets$/, pageSets, "sets"], [/^#\/sets\/([^/?]+)$/, pageSet, "sets"],
  [/^#\/library(\?.*)?$/, pageLibrary, "library"], [/^#\/library\/([^/?]+)$/, pageLibStyle, "library"],
  [/^#\/styles$/, pageStyles, "styles"], [/^#\/styles\/([^/?]+)$/, pageStyle, "styles"],
  [/^#\/new(\?.*)?$/, pageNew, "new"], [/^#\/learn$/, pageLearn, "learn"], [/^#\/(?:admin|settings)(?:\/(general|users|usage))?(\?.*)?$/, pageSettings, "settings"], [/^#\/admin\/claude$/, pageClaude, "ai"],
  [/^#\/account$/, pageAccount, "account"],
];
/** pages open without logging in (online mode) */
const PUBLIC = [
  [/^#\/login$/, pageLogin], [/^#\/setup$/, pageSetup], [/^#\/forgot$/, pageForgot],
  [/^#\/verify\/([^/?]+)$/, pageVerify], [/^#\/reset\/([^/?]+)$/, pageReset],
];
let rendering = null;
async function route() {
  const h = location.hash || "#/";
  if (MODE === "online") {
    for (const [re, fn] of PUBLIC) {
      const m = h.match(/** @type {RegExp} */ (re));
      if (m) { await /** @type {(id?: string) => Promise<void>} */ (fn)(m[1] && decodeURIComponent(m[1])); return; }
    }
    if (!ME) { location.hash = "#/login"; return; }
    document.body.classList.remove("guest");
  }
  for (const [re, fn, nav] of routes) {
    const m = h.match(re);
    if (!m) continue;
    (/** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll("nav a, .side-foot a[data-nav]"))).forEach((a) => a.classList.toggle("on", a.dataset.nav === nav));
    const p = fn(m[1] && !m[1].startsWith("?") ? decodeURIComponent(m[1]) : undefined);
    rendering = p;
    try { await p; } catch (e) { if (rendering === p) $app.innerHTML = `<p class="error">${esc(e.message)}</p>${back("#/", "Jobs")}`; }
    return;
  }
  $app.innerHTML = `<p class="error">This page does not exist.</p>${back("#/", "Jobs")}`;
}

let pending = new Set(), seeded = false;
async function refreshPending(announce) {
  try {
    const { reviews } = await get("/reviews?status=pending");
    const ids = new Set(reviews.map((r) => r.id));
    if (announce && seeded) reviews.filter((r) => !pending.has(r.id)).forEach(notify);
    pending = ids; seeded = true;
    document.title = (ids.size ? `(${ids.size}) to review · ` : "") + "Film Studio";
    const c = document.getElementById("nav-count"); c.textContent = String(ids.size); c.hidden = !ids.size; c.title = `${ids.size} to review`;
  } catch { /* server restarting */ }
}
function notify(r) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  const n = new Notification("Film Studio: a job needs your review", { body: REVIEW[r.kind] + (r.set ? " · " + r.set : ""), tag: r.id });
  n.onclick = () => { window.focus(); location.hash = `#/reviews/${r.id}`; n.close(); };
}
function askNotify() {
  if (!("Notification" in window) || Notification.permission !== "default" || document.getElementById("ask-notify")) return;
  const p = document.createElement("p");
  p.id = "ask-notify"; p.className = "notice";
  p.innerHTML = `Turn on notifications to know as soon as a job needs your review, even when you are in another window. <button>Turn on notifications</button>`;
  p.querySelector("button").onclick = () => Notification.requestPermission().finally(() => p.remove());
  $app.prepend(p);
}

let timer = null;
function onChange() {           // coalesce bursts of events into one refresh
  clearTimeout(timer);
  timer = setTimeout(() => {
    refreshPending(true);
    const h = location.hash || "#/";
    const editing = document.activeElement && ["note", "answer", "change-note"].includes(document.activeElement.id)
      || /** @type {HTMLDetailsElement | null} */ (document.getElementById("changes"))?.open;
    if (!editing && !/^#\/(films|sets|styles|library)/.test(h)) route();
  }, 300);
}
function connect() {
  const es = new EventSource(API + "/events");
  const live = () => document.getElementById("live") || document.createElement("small");      // redrawn with the account menu
  es.onopen = () => { live().classList.add("on"); live().textContent = "● Live updates on"; };
  es.onerror = () => { live().classList.remove("on"); live().textContent = "Disconnected, reconnecting…"; };      // EventSource reconnects by itself
  ["job.updated", "review.created", "review.decided"].forEach((t) => es.addEventListener(t, onChange));
}

window.addEventListener("hashchange", route);
(async () => {
  try { MODE = (await get("/health")).mode || "local"; } catch { /* old server */ }
  (/** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll(".online-only"))).forEach((el) => (el.hidden = MODE !== "online"));
  (/** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll(".local-only"))).forEach((el) => (el.hidden = MODE === "online"));
  if (MODE === "online") {
    await loadMe();
  }
  await route();
  if (MODE === "online" && !ME) {     // live updates and the review badge start after logging in
    const wait = () => { if (ME) { window.removeEventListener("hashchange", wait); refreshPending(false); connect(); } };
    window.addEventListener("hashchange", wait);
    return;
  }
  refreshPending(false); askNotify();
  connect();
})();
