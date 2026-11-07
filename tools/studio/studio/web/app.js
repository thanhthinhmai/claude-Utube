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
  not_found: "Not found.", bad_name: "Invalid file name.", invalid: "Invalid request.", finished: "This job has already finished.",
  already_decided: "This review was already decided elsewhere.", note_required: "Add a note (at least 3 characters) before requesting changes.",
  value_not_allowed: "That choice is not allowed for this review.", csrf: "Request blocked (missing studio header).",
  bad_host: "Request blocked (wrong host).", not_local: "Request blocked (not from this machine).",
  auth_required: "Please log in.", locked: "This account is locked. Contact the studio.",
  bad_login: "Wrong email or password.", email_taken: "This email already has an account. Log in instead.",
  weak_password: "The password needs at least 10 characters.", terms_required: "Please accept the terms of use.",
  signup_closed: "Sign-up is closed for now. Please try again later.", token_expired: "This link was already used or has expired.",
  rate_limited: "Too many tries. Please wait a little and try again.", unverified: "Confirm your email first: open the link we sent you.",
  quota_exceeded: "You have used all your films for this month.", daily_cap: "The studio is fully booked today. Please try again tomorrow.",
  too_many_queued: "You already have 3 jobs in progress. Wait for one to finish.", too_long: "The film is too long.",
  content_rejected: "The studio cannot make this idea.", style_not_found: "This style does not exist any more.",
  in_use: "A job is still using this.", rights_required: "Please confirm your right to use the channel's videos.",
  too_many_videos: "Too many videos for one style.", too_large: "The file is too large.", bad_video: "This file is not a video the studio can read.",
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
  $app.innerHTML = `${back("#/", "Jobs")}
    ${head(esc(KIND[j.kind] || j.kind), `${esc(j.name)} ${badge(j.status)}`, "")}
    <div class="split"><div>
    ${j.status === "waiting_review" && j.reviews.some((r) => !r.decision) ? `<p class="notice">This job is waiting for your review: <a href="#/reviews/${esc(j.reviews.find((r) => !r.decision).id)}">open the review</a>.</p>` : ""}
    ${j.status === "queued" ? `<p class="notice">In the queue${j.queue_position ? `: number ${j.queue_position}` : ""}. It starts by itself when the studio is free.</p>` : ""}
    ${MODE === "online" && j.status === "done" && j.links.film ? `<p><a class="button primary" href="${API}/films/${encodeURIComponent(j.links.film)}/download">Download the film</a>
      <a class="button" href="#/films/${esc(j.links.film)}">Watch it</a></p>` : ""}
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
    <div class="panel decide" id="decide">${d ? decidedHtml(d) : `
      <p><strong>Your decision</strong> <span class="muted">· the job continues on its own, no need to type in the chat</span></p>
      <textarea id="note" placeholder="Note (required when requesting changes)"></textarea>
      <div class="row" style="margin-top:8px"><button class="primary" data-v="approve">Approve</button><button data-v="revise">Request changes</button>${extra}</div>
      <p id="msg" class="muted"></p>`}</div>`;
  zoomable($app);
  (/** @type {NodeListOf<HTMLElement>} */ ($app.querySelectorAll("#decide button[data-v]"))).forEach((b) => b.addEventListener("click", async () => {
    const v = b.dataset.v, note = (/** @type {HTMLInputElement} */ (document.getElementById("note"))).value.trim(), msg = document.getElementById("msg");
    if (v === "revise" && note.length < 3) { msg.textContent = ERR.note_required; msg.className = "fail"; return; }
    (/** @type {NodeListOf<HTMLButtonElement>} */ ($app.querySelectorAll("#decide button"))).forEach((x) => (x.disabled = true));
    try {
      const res = await post(`/reviews/${encodeURIComponent(id)}/decision`, { value: v, note });
      document.getElementById("decide").innerHTML = decidedHtml(res);
      askNotify();
    } catch (e) {
      msg.textContent = e.message; msg.className = "fail";
      if (e.code === "already_decided") setTimeout(route, 800); else (/** @type {NodeListOf<HTMLButtonElement>} */ ($app.querySelectorAll("#decide button"))).forEach((x) => (x.disabled = false));
    }
  }));
}
const decidedHtml = (d) => `<p class="done-box">Decided: <strong>${esc(DECISION[d.value])}</strong> (via ${esc(SOURCE[d.source])}, ${when(d.at)})
  ${d.note ? `<br>Note: ${esc(d.note)}` : ""}</p>`;

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
  $app.innerHTML = `<div class="auth panel"><h1>${title}</h1>${lead ? `<p class="muted">${lead}</p>` : ""}${body}
    <p id="msg" class="muted" role="status"></p>${foot}</div>`;
}
/** Wire a form: `fn` sends it; its result is shown, an error is shown in red. */
function onSubmit(fn) {
  const form = /** @type {HTMLFormElement} */ ($app.querySelector("form"));
  const msg = document.getElementById("msg");
  form.onsubmit = async (e) => {
    e.preventDefault();
    const btn = /** @type {HTMLButtonElement} */ (form.querySelector("button[type=submit]"));
    btn.disabled = true; msg.className = "muted"; msg.textContent = "";
    try { const t = await fn(); if (t) msg.textContent = t; } catch (err) { msg.className = "fail"; msg.textContent = err.message; }
    btn.disabled = false;
  };
}
async function pageLogin() {
  authPage("Log in", "Film Studio makes short films for you in the style you choose.", `<form class="form">
    <label>Email <input id="email" type="email" autocomplete="email" required></label>
    <label>Password <input id="password" type="password" autocomplete="current-password" required></label>
    <button class="primary" type="submit">Log in</button></form>`,
  `<p><a href="#/forgot">Forgot your password?</a> · <a href="#/signup">Create an account</a></p>`);
  onSubmit(async () => {
    await post("/auth/login", { email: field("email").value, password: field("password").value });
    await loadMe(); location.hash = "#/";
    return "";
  });
}
async function pageSignup() {
  authPage("Create an account", "Each month you get a few free films. No card needed.", `<form class="form">
    <label>Email <input id="email" type="email" autocomplete="email" required></label>
    <label>Password <span class="hint">At least 10 characters.</span>
      <input id="password" type="password" autocomplete="new-password" minlength="10" required></label>
    <label class="check"><input id="terms" type="checkbox" required> <span>I agree to the terms of use: I only ask for films I may publish,
      and I do not ask for violence, sexual content, hate, or copies of real people, brands or channels.</span></label>
    <button class="primary" type="submit">Create account</button></form>`, `<p>Already have an account? <a href="#/login">Log in</a></p>`);
  onSubmit(async () => {
    await post("/auth/signup", { email: field("email").value, password: field("password").value, accept_terms: field("terms").checked });
    $app.querySelector("form").remove();
    return "Check your email: we sent a link to confirm your address. Then log in.";
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

// ---------- admin (US3) ----------
const SETTING = [
  ["signup_open", "Sign-up open", "bool"], ["quota_films_default", "Films per month (default)", "int"],
  ["quota_learns_default", "Learns per month (default)", "int"], ["film_max_seconds", "Longest film (seconds)", "int"],
  ["learn_max_videos", "Videos per learn", "int"], ["upload_max_mb", "Upload size (MB)", "int"],
  ["upload_max_minutes", "Upload length (minutes)", "int"], ["daily_cost_cap_usd", "Studio cost cap per day (USD)", "num"],
  ["job_cost_cap_usd", "Cost cap per job (USD)", "num"], ["concurrency", "Jobs at the same time", "int"],
  ["review_timeout_days", "Stop a job after waiting (days)", "int"], ["model", "Claude model", "text"],
];
const usd = (v) => `$${Number(v || 0).toFixed(2)}`;
async function pageAdmin() {
  if (ME.role !== "admin") { $app.innerHTML = `<p class="error">This page is for the studio admin.</p>`; return; }
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  const q = params.get("q") || "";
  const [st, acc, use] = await Promise.all([get("/admin/settings"), get("/admin/accounts?q=" + encodeURIComponent(q)), get("/admin/usage")]);
  const input = ([k, label, t]) => t === "bool"
    ? `<label class="check"><input id="s-${k}" type="checkbox" ${st[k] ? "checked" : ""}> <span>${label}</span></label>`
    : `<label>${label}<input id="s-${k}" type="${t === "text" ? "text" : "number"}" ${t === "num" ? 'step="0.01"' : ""} value="${esc(st[k])}"></label>`;
  const rows = acc.accounts.map((a) => `<tr data-id="${esc(a.id)}"><td>${esc(a.email)}${a.role === "admin" ? " (admin)" : ""}${a.verified ? "" : ' <span class="muted">unverified</span>'}</td>
      <td>${a.quota.films.used} / <input type="number" min="0" data-f="quota_films" value="${a.quota_films ?? ""}" placeholder="${a.quota.films.limit}" aria-label="Films limit"></td>
      <td>${a.quota.learns.used} / <input type="number" min="0" data-f="quota_learns" value="${a.quota_learns ?? ""}" placeholder="${a.quota.learns.limit}" aria-label="Learns limit"></td>
      <td class="num">${usd(a.cost_month_usd)}</td><td class="num">${num(a.storage_mb, 1)} MB</td>
      <td>${a.role === "admin" ? "" : `<button data-lock="${a.locked ? "0" : "1"}" class="${a.locked ? "" : "danger"}">${a.locked ? "Unlock" : "Lock"}</button>`}</td></tr>`).join("");
  $app.innerHTML = `${head("Studio", "Admin", `Cost in the last 30 days: ${usd(use.cost_usd_total)} · storage ${num(use.storage_mb_total, 1)} MB`)}
    <h2>Settings</h2><form class="form panel" id="settings"><div class="admin-grid">${SETTING.map(input).join("")}</div>
      <div><button class="primary" type="submit">Save settings</button></div></form><p id="msg" class="muted" role="status"></p>
    <h2>Customers</h2>
    <div class="row filters"><label class="search"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
      <input id="acc-q" type="search" placeholder="Search by email" value="${esc(q)}" aria-label="Search by email"></label></div>
    <p class="muted">Films and learns: used / own limit (empty = the default). Locking stops the account's running jobs.</p>
    <div class="table-wrap"><table><tr><th>Email</th><th>Films</th><th>Learns</th><th>Cost this month</th><th>Storage</th><th></th></tr>${rows}</table></div>
    <p id="acc-msg" class="muted" role="status"></p>
    <h2>Cost per day</h2><div class="table-wrap"><table><tr><th>Day</th><th>Jobs</th><th>Cost</th></tr>
      ${use.days.slice().reverse().map((d) => `<tr><td>${esc(d.day)}</td><td class="num">${d.jobs}</td><td class="num">${usd(d.cost_usd)}</td></tr>`).join("") || '<tr><td colspan="3" class="muted">No jobs yet.</td></tr>'}</table></div>`;
  onSubmit(async () => {
    const data = {};
    for (const [k, , t] of SETTING) {
      const el = field(`s-${k}`);
      data[k] = t === "bool" ? el.checked : t === "text" ? el.value.trim() : Number(el.value);
    }
    await send("PUT", "/admin/settings", data);
    return "Saved.";
  });
  const msg = document.getElementById("acc-msg");
  const save = async (id, body) => {
    try { await send("PUT", `/admin/accounts/${encodeURIComponent(id)}`, body); msg.className = "muted"; msg.textContent = "Saved."; }
    catch (e) { msg.className = "fail"; msg.textContent = e.message; }
  };
  (/** @type {NodeListOf<HTMLInputElement>} */ ($app.querySelectorAll("tr[data-id] input[data-f]"))).forEach((el) => el.addEventListener("change", () => {
    const id = /** @type {HTMLElement} */ (el.closest("tr")).dataset.id, f = el.dataset.f;
    save(id, el.value === "" ? { [f === "quota_films" ? "use_default_films" : "use_default_learns"]: true } : { [f]: Number(el.value) });
  }));
  (/** @type {NodeListOf<HTMLButtonElement>} */ ($app.querySelectorAll("tr[data-id] button[data-lock]"))).forEach((b) => b.addEventListener("click", async () => {
    const lock = b.dataset.lock === "1";
    if (lock && !confirm("Lock this account? Its running jobs stop now.")) return;
    await save(/** @type {HTMLElement} */ (b.closest("tr")).dataset.id, { locked: lock });
    route();
  }));
  const qi = field("acc-q");
  let t = 0;
  qi.addEventListener("input", () => {
    clearTimeout(t);
    t = setTimeout(() => {
      history.replaceState(null, "", "#/admin?q=" + encodeURIComponent(qi.value));
      route().then(() => { const n = field("acc-q"); n.focus(); n.setSelectionRange(n.value.length, n.value.length); });
    }, 400);
  });
}

async function loadMe() {
  try { ME = await get("/me"); } catch { ME = null; }
  drawAccount();
  return ME;
}
function drawAccount() {
  const bar = document.getElementById("acct");
  document.body.classList.toggle("guest", MODE === "online" && !ME);
  bar.hidden = !(MODE === "online" && ME);
  (/** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll(".admin-only"))).forEach((el) => (el.hidden = !(ME && ME.role === "admin")));
  if (bar.hidden) return;
  const f = ME.quota.films;
  bar.innerHTML = `<span class="credits">${Math.max(0, f.limit - f.used)}/${f.limit} films left this month</span>
    <strong>${esc(ME.email)}</strong><button id="logout">Log out</button>`;
  document.getElementById("logout").onclick = async () => {
    try { await post("/auth/logout"); } catch { /* already logged out */ }
    ME = null; drawAccount(); location.hash = "#/login";
  };
}

// ---------- router, live updates, waiting badge, notifications ----------
/** @type {Array<[RegExp, (id?: string) => Promise<void>, string]>} */
const routes = [
  [/^#\/?(\?.*)?$/, pageJobs, "jobs"], [/^#\/jobs\/([^/?]+)$/, pageJob, "jobs"], [/^#\/reviews\/([^/?]+)$/, pageReview, "jobs"],
  [/^#\/films$/, pageFilms, "films"], [/^#\/films\/([^/?]+)$/, pageFilm, "films"],
  [/^#\/sets$/, pageSets, "sets"], [/^#\/sets\/([^/?]+)$/, pageSet, "sets"],
  [/^#\/library(\?.*)?$/, pageLibrary, "library"], [/^#\/library\/([^/?]+)$/, pageLibStyle, "library"],
  [/^#\/styles$/, pageStyles, "styles"], [/^#\/styles\/([^/?]+)$/, pageStyle, "styles"],
  [/^#\/new(\?.*)?$/, pageNew, "new"], [/^#\/learn$/, pageLearn, "learn"], [/^#\/admin(\?.*)?$/, pageAdmin, "admin"],
];
/** pages open without logging in (online mode) */
const PUBLIC = [
  [/^#\/login$/, pageLogin], [/^#\/signup$/, pageSignup], [/^#\/forgot$/, pageForgot],
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
    (/** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll("nav a"))).forEach((a) => a.classList.toggle("on", a.dataset.nav === nav));
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
    const editing = document.activeElement && document.activeElement.id === "note";
    if (!editing && !/^#\/(films|sets|styles|library)/.test(h)) route();
  }, 300);
}
function connect() {
  const es = new EventSource(API + "/events");
  const live = document.getElementById("live");
  es.onopen = () => { live.classList.add("on"); live.textContent = "● Live updates on"; };
  es.onerror = () => { live.classList.remove("on"); live.textContent = "Disconnected, reconnecting…"; };      // EventSource reconnects by itself
  ["job.updated", "review.created", "review.decided"].forEach((t) => es.addEventListener(t, onChange));
}

window.addEventListener("hashchange", route);
(async () => {
  try { MODE = (await get("/health")).mode || "local"; } catch { /* old server */ }
  (/** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll(".online-only"))).forEach((el) => (el.hidden = MODE !== "online"));
  (/** @type {NodeListOf<HTMLElement>} */ (document.querySelectorAll(".local-only"))).forEach((el) => (el.hidden = MODE === "online"));
  if (MODE === "online") {
    document.querySelector(".owner strong").textContent = "Your account";
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
