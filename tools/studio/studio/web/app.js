// Film Studio: track jobs and review them (specs/003-studio-ui). Plain JavaScript, no build step.
"use strict";
const API = "/api/v1";
const $app = document.getElementById("app");
const STATUS = {
  running: "Running", waiting_review: "Needs review", waiting_resume: "Waiting to resume", done: "Done",
  failed: "Failed", stopped: "Stopped", inactive: "Inactive",
};
const KIND = { learn: "Learn a style", film: "Make a film" };
const REVIEW = { "style-1": "Review 1: style draft", "style-2": "Review 2: proof frame" };
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
};
const errText = (body, status) => ERR[body?.error?.code] || `Error ${status}`;
const badge = (s) => `<span class="badge s-${esc(s)}">${esc(STATUS[s] || s)}</span>`;
async function get(path) {
  const r = await fetch(API + path);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(errText(body, r.status));
  return body;
}
async function post(path, data) {
  const r = await fetch(API + path, { method: "POST", headers: { "Content-Type": "application/json", "X-Studio": "1" }, body: JSON.stringify(data) });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(errText(body, r.status)); e.code = body?.error?.code; throw e; }
  return body;
}
function zoomable(root) {
  root.querySelectorAll("img[data-zoom]").forEach((img) => img.addEventListener("click", () => {
    const lb = document.getElementById("lightbox"); lb.querySelector("img").src = img.src; lb.hidden = false;
  }));
}
document.getElementById("lightbox").addEventListener("click", (e) => { e.currentTarget.hidden = true; });

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
    <div class="row filters">
      <label>Status <select id="f-status"><option value="">All</option>${opt(STATUS, st)}</select></label>
      <label>Type <select id="f-kind"><option value="">All</option>${opt(KIND, kd)}</select></label>
    </div>
    ${jobs.length ? `<ul class="jobs">${items}</ul>` : `<p class="panel muted">No jobs match these filters.</p>`}`;
  const go = () => {
    const nq = new URLSearchParams();
    const s = document.getElementById("f-status").value, k = document.getElementById("f-kind").value;
    if (s) nq.set("status", s); if (k) nq.set("kind", k);
    location.hash = "#/" + (nq.toString() ? "?" + nq : "");
  };
  document.getElementById("f-status").onchange = go;
  document.getElementById("f-kind").onchange = go;
}

function emptyJobs() {
  $app.innerHTML = `<div class="empty"><span class="spark">${SPARK}</span>
      <h1>What should we make today?</h1>
      <p class="muted">Open Claude Code in the project folder and say what you want. Jobs show up here, with the steps that need your review.</p></div>
    <div class="prompts">${PROMPTS.map(([t, x]) => `<div class="panel prompt" tabindex="0" data-text="${esc(x)}">
      <strong>${esc(t)}</strong><p>${esc(x)}</p></div>`).join("")}</div>
    <p class="muted" style="text-align:center;margin-top:16px">Click a card to copy the example prompt.</p>`;
  $app.querySelectorAll(".prompt").forEach((el) => {
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
      ${links ? `<p class="section-title" style="margin-top:18px">Results</p><p style="display:grid;gap:4px;margin:0">${links.replaceAll(" · ", "")}</p>` : ""}
    </aside></div>`;
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
    ${head("Review", esc(REVIEW[r.kind]), `Reference set <a href="#/sets/${esc(r.set)}">${esc(r.set)}</a> · sent ${when(r.created_at)}`)}
    ${proof}
    <h2>${c ? "Notes from Claude" : "Summary"}</h2><div class="panel md">${r.summary_html}</div>
    <div class="panel decide" id="decide">${d ? decidedHtml(d) : `
      <p><strong>Your decision</strong> <span class="muted">· the job continues on its own, no need to type in the chat</span></p>
      <textarea id="note" placeholder="Note (required when requesting changes)"></textarea>
      <div class="row" style="margin-top:8px"><button class="primary" data-v="approve">Approve</button><button data-v="revise">Request changes</button>${extra}</div>
      <p id="msg" class="muted"></p>`}</div>`;
  zoomable($app);
  $app.querySelectorAll("#decide button[data-v]").forEach((b) => b.addEventListener("click", async () => {
    const v = b.dataset.v, note = document.getElementById("note").value.trim(), msg = document.getElementById("msg");
    if (v === "revise" && note.length < 3) { msg.textContent = ERR.note_required; msg.className = "fail"; return; }
    $app.querySelectorAll("#decide button").forEach((x) => (x.disabled = true));
    try {
      const res = await post(`/reviews/${encodeURIComponent(id)}/decision`, { value: v, note });
      document.getElementById("decide").innerHTML = decidedHtml(res);
      askNotify();
    } catch (e) {
      msg.textContent = e.message; msg.className = "fail";
      if (e.code === "already_decided") setTimeout(route, 800); else $app.querySelectorAll("#decide button").forEach((x) => (x.disabled = false));
    }
  }));
}
const decidedHtml = (d) => `<p class="done-box">Decided: <strong>${esc(DECISION[d.value])}</strong> (via ${esc(SOURCE[d.source])}, ${when(d.at)})
  ${d.note ? `<br>Note: ${esc(d.note)}` : ""}</p>`;

async function pageFilms() {
  const { films } = await get("/films");
  $app.innerHTML = `${head("Results", "Films", "Rendered films in the films/ folder.")}${films.length ? `<div class="grid">${films.map((f) => `<a class="panel card" href="#/films/${esc(f.name)}">
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
      </video><p class="muted">Turn subtitles on or off with the player’s CC button.</p>`
    : `<p class="notice">${f.rendering ? "The film is still rendering: see progress on the Jobs page." : "No film file yet."}</p>`}
    ${f.treatment_html ? `<h2>Script (TREATMENT)</h2><div class="panel md">${f.treatment_html}</div>` : ""}
    ${f.credits ? `<h2>Third-party assets (CREDITS)</h2><pre class="log">${esc(f.credits)}</pre>` : ""}`;
}

async function pageSets() {
  const { sets } = await get("/sets");
  $app.innerHTML = `${head("Library", "Measurements", "Frame-by-frame measurements of the reference video sets you learned from.")}${sets.length ? `<ul class="jobs">${sets.map((s) => `<li><a class="panel job" href="#/sets/${esc(s.set)}">
      <strong>${esc(s.set)}</strong><span class="muted">${s.measured}/${s.videos} videos measured</span>
      <span class="muted">${s.media_removed ? "Reference videos deleted" : "Reference videos still on this machine"}</span></a></li>`).join("")}</ul>`
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
      const files = sh.sheets[document.getElementById("sv").value]; i = Math.max(0, Math.min(i, files.length - 1));
      document.getElementById("sheet").src = `${API}/sets/${encodeURIComponent(name)}/sheets/${files[i]}`;
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
  $app.innerHTML = `${head("Library", "My styles", "Styles you learned and saved in my-styles/, ready for making films.")}${styles.length ? `<div class="grid">${styles.map((s) => `<a class="panel card" href="#/styles/${esc(s.slug)}">
      ${s.has_styleframe ? `<img src="${API}/styles/${esc(s.slug)}/styleframe" alt="">` : ""}
      <p><strong>${esc(s.en || s.slug)}</strong><br><span class="muted">based on ${esc(s.based_on || "–")}${s.source === "learned" ? " · learned from videos" : ""}</span></p></a>`).join("")}</div>`
    : `<p class="panel muted">No styles yet. Learn one by telling Claude: “Learn the style of the channel …”.</p>`}`;
}

async function pageStyle(slug) {
  const s = await get(`/styles/${encodeURIComponent(slug)}`);
  const ref = s.reference || {};
  $app.innerHTML = `${back("#/styles", "Styles")}${head(esc(slug), esc(s.en || slug), `Base technique ${esc(s.based_on || "–")} · ${s.source === "learned" ? `learned from ${ref.videos ?? "?"} videos, ${num(ref.measured_seconds, 0)} seconds measured` : "custom style"}${s.created ? ` · saved ${esc(s.created)}` : ""}`)}
    ${s.has_styleframe ? `<p><img class="shot" data-zoom src="${API}/styles/${esc(slug)}/styleframe" alt="Proof frame"></p>` : ""}
    <h2>STYLE.md</h2><div class="panel md">${s.style_html}</div>
    ${s.evidence_html ? `<h2>Evidence</h2><div class="panel md">${s.evidence_html}</div>` : ""}`;
  zoomable($app);
}

// ---------- router, live updates, waiting badge, notifications ----------
const routes = [
  [/^#\/?(\?.*)?$/, pageJobs, "jobs"], [/^#\/jobs\/([^/?]+)$/, pageJob, "jobs"], [/^#\/reviews\/([^/?]+)$/, pageReview, "jobs"],
  [/^#\/films$/, pageFilms, "films"], [/^#\/films\/([^/?]+)$/, pageFilm, "films"],
  [/^#\/sets$/, pageSets, "sets"], [/^#\/sets\/([^/?]+)$/, pageSet, "sets"],
  [/^#\/styles$/, pageStyles, "styles"], [/^#\/styles\/([^/?]+)$/, pageStyle, "styles"],
];
let rendering = null;
async function route() {
  const h = location.hash || "#/";
  for (const [re, fn, nav] of routes) {
    const m = h.match(re);
    if (!m) continue;
    document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("on", a.dataset.nav === nav));
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
    const c = document.getElementById("nav-count"); c.textContent = ids.size; c.hidden = !ids.size; c.title = `${ids.size} to review`;
  } catch { /* server restarting */ }
}
function notify(r) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  const n = new Notification("Film Studio: a job needs your review", { body: REVIEW[r.kind] + " · " + r.set, tag: r.id });
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
    if (!editing && !/^#\/(films|sets|styles)/.test(h)) route();
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
route().then(() => { refreshPending(false); askNotify(); });
connect();
