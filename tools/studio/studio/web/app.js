// @ts-check
// Film Studio: track jobs and review them (specs/003-studio-ui). Plain JavaScript, no build step.
"use strict";
const API = "/api/v1";
const $app = document.getElementById("app");
const STATUS = {
  queued: "In queue", running: "Running", waiting_review: "Needs review", waiting_resume: "Waiting to resume", done: "Done",
  failed: "Failed", stopped: "Stopped", inactive: "Inactive",
};
const KIND = { learn: "Learn a style", film: "Make a film", topics: "Score topics" };
const REVIEW = { "style-1": "Review 1: style draft", "style-2": "Review 2: proof frame", question: "Question from the studio",
  treatment: "Treatment review", script: "Script review", voice: "Voice review", shots: "Shots review", mix: "Mix review",
  publish: "Publish review" };
// Online mode (specs/007): the same page serves many customers; MODE comes from GET /health
let MODE = "local";
/** @type {any} */
let ME = null;
const DECISION = { approve: "Approve", revise: "Request changes", accept_anyway: "Accept anyway", stop: "Stop" };
const SOURCE = { ui: "the studio", chat: "the chat", api: "the API" };

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
  studio_not_ready: "The studio has no Claude account ready right now. Please try again later.",
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
  quota_exceeded: "You have used all your films for this month.",
  too_many_queued: "You already have 3 jobs in progress. Wait for one to finish.", too_long: "The film is too long.",
  content_rejected: "The studio cannot make this idea.", style_not_found: "This style does not exist any more.",
  in_use: "A job is still using this.", rights_required: "Please confirm your right to use the channel's videos.",
  bad_image: "Only PNG, JPEG or WebP pictures can be added.", forbidden: "You can only read this.",
  changed: "Someone else just changed these notes.",
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

// ---------- Quality: script scores and film measures (specs/010 US3) ----------
/** @type {Array<[string, string, (v: any) => string, (v: any) => boolean, string]>} */
const QC_ROWS = [
  ["silence_ratio", "Silence in the narration", (v) => `${Math.round(v * 100)}%`, (v) => v <= 0.2, "≤ 20%"],
  ["long_pauses_bad", "Long pauses inside a paragraph", (v) => String(v.length), (v) => !v.length, "none"],
  ["cuts_bad", "Cuts too close to a sentence", (v) => String(v.length), (v) => !v.length, "none"],
  ["key_shots_bad", "Short closing shots", (v) => String(v.length), (v) => !v.length, "none (≥ 2.5 s)"],
  ["tail_s", "Time after the last word", (v) => `${num(v, 1)} s`, (v) => v <= 1.5, "≤ 1.5 s"],
  ["stills_bad", "Still pictures", (v) => String(v.length), (v) => !v.length, "none over the style's limit"],
  ["missing_glyphs", "Characters with no font", (v) => String(v.length), (v) => !v.length, "none"],
];
/** @param {any} qa */
function qualityHtml(qa) {
  if (!qa || (!qa.script && !qa.film && qa.lufs === undefined)) return "";
  const ok = (/** @type {boolean} */ good) => `<span class="${good ? "pass" : "fail"}">${good ? "pass" : "fail"}</span>`;
  const s = qa.script;
  const script = !s ? "" : s.verdict === "skipped"
    ? `<p class="muted">Script: skipped (${esc(s.skip_reason || "no narration")})</p>`
    : `<p><strong>Script:</strong> ${esc(s.verdict)} · machine check ${s.machine_score ?? "–"}/10 · editor ${s.editor_score ?? "–"}/10
        · fix rounds ${s.fix_rounds}${s.model ? ` · editor model ${esc(s.model)}` : ""}</p>
      <table class="qa"><tr><th>Round</th><th>Editor</th><th>P1</th><th>P2</th><th>P3</th></tr>${(s.rounds || []).map((/** @type {any} */ r) =>
        `<tr><td>${r.round}${r.customer_round ? " (your changes)" : ""}</td><td>${r.score ?? "no answer"}</td><td>${r.p1}</td><td>${r.p2}</td><td>${r.p3}</td></tr>`).join("")}</table>`;
  const m = qa.film && typeof qa.film === "object" ? qa.film.measures || {} : null;
  const rows = [
    qa.lufs !== undefined && qa.lufs !== null ? `<tr><td>Loudness</td><td>${num(qa.lufs, 1)} LUFS</td><td>−14 ± 1</td><td>${ok(Math.abs(qa.lufs + 14) <= 1)}</td></tr>` : "",
    qa.peak_db !== undefined && qa.peak_db !== null ? `<tr><td>True peak</td><td>${num(qa.peak_db, 1)} dB</td><td>≤ −1 dB</td><td>${ok(qa.peak_db <= -1)}</td></tr>` : "",
    qa.readcheck && qa.readcheck !== "not_checked" ? `<tr><td>Reading time of on-screen text</td><td>${esc(qa.readcheck)}</td><td>enough time</td><td>${ok(qa.readcheck === "pass")}</td></tr>` : "",
    ...(m ? QC_ROWS.filter(([k]) => m[k] !== undefined).map(([k, label, show, good, rule]) =>
      `<tr><td>${label}</td><td>${show(m[k])}</td><td>${rule}</td><td>${ok(good(m[k]))}</td></tr>`) : []),
  ].join("");
  return `<div class="panel" id="quality"><p class="section-title">Quality</p>${script}
    ${rows ? `<table class="qa"><tr><th>Measure</th><th>Value</th><th>Rule</th><th></th></tr>${rows}</table>` : ""}
    ${m && m.texts_checked === false ? `<p class="muted">On-screen text was not checked for missing characters (only subtitles).</p>` : ""}
    ${qa.film === "not_checked" ? `<p class="muted">The film could not be measured.</p>` : ""}</div>`;
}

// ---------- channels and lessons (specs/012) ----------
const lines = (/** @type {string} */ v) => v.split("\n").map((x) => x.trim()).filter(Boolean);
/** @param {any[]} ls @param {string} base @param {boolean} canEdit */
function lessonsTable(ls, base, canEdit) {
  if (!ls.length) return `<p class="muted">No lessons yet.</p>`;
  return `<div class="table-wrap"><table class="qa lessons"><tr><th>#</th><th>State</th><th>What went wrong</th><th>How to stop it</th><th>Checked by</th><th></th></tr>
    ${ls.map((x) => `<tr class="l-${esc(x.status)}"><td>${x.n}</td><td>${esc(x.status)}</td><td>${esc(x.what)}<br><small class="muted">${esc(x.why)}</small></td>
      <td>${esc(x.stop)}</td><td>${x.rule ? `<code>${esc(x.rule)}</code>${x.rule_valid === false ? " (cannot be read)" : ""}` : "—"}</td>
      <td class="row">${x.status === "draft" && canEdit ? `<button data-act="approve" data-n="${x.n}">Approve</button><button data-act="edit" data-n="${x.n}">Edit</button>` : ""}
        ${x.status !== "retired" ? `<button data-act="retire" data-n="${x.n}">Retire</button>` : ""}</td></tr>`).join("")}</table></div>`;
}
const LESSON_FORM = `<details class="panel"><summary><strong>Add a lesson</strong></summary><div class="form" id="lesson-form">
  <label>What went wrong<input id="l-what" maxlength="400"></label><label>Why it was not caught<input id="l-why" maxlength="400"></label>
  <label>How to stop it next time<input id="l-stop" maxlength="400"></label>
  <label>Machine rule <span class="hint">Optional: phrase:&lt;words never to use&gt;, max_sentence_words:N or max_title_chars:N</span><input id="l-rule" maxlength="120"></label>
  <div><button class="primary" id="l-add">Add the lesson</button></div><p id="l-msg" class="muted" role="status"></p></div></details>`;
/** @param {string} base API path of the lesson list @param {() => void} again */
function wireLessons(base, again) {
  $app.querySelectorAll("table.lessons button").forEach((el) => {
    const b = /** @type {HTMLButtonElement} */ (el);
    b.onclick = async () => {
      try {
        if (b.dataset.act === "edit") {
          const what = prompt("What went wrong", ""), stop = prompt("How to stop it next time", "");
          if (what === null || stop === null) return;
          await send("PUT", `${base}/${b.dataset.n}`, { ...(what ? { what } : {}), ...(stop ? { stop } : {}) });
        } else await post(`${base}/${b.dataset.n}/${b.dataset.act}`);
        again();
      } catch (e) { alert(e.message); }
    };
  });
  const add = document.getElementById("l-add");
  if (add) add.onclick = async () => {
    const msg = document.getElementById("l-msg");
    try {
      const rule = field("l-rule").value.trim();
      await post(base, { what: field("l-what").value.trim(), why: field("l-why").value.trim(), stop: field("l-stop").value.trim(), ...(rule ? { rule } : {}) });
      again();
    } catch (e) { msg.className = "fail"; msg.textContent = e.message; }
  };
}

async function pageChannels() {
  const [{ channels }, lib, mine] = await Promise.all([get("/channels"), get("/library"), get("/styles")]);
  const styles = [...mine.styles.map((/** @type {any} */ s) => [s.slug, `${s.en || s.slug} (yours)`]), ...(lib.styles || []).map((/** @type {any} */ s) => [s.slug, s.en])];
  $app.innerHTML = `${head("Make", "Channels", "Your own YouTube channels: what you decided for each one, and the lessons the studio must not forget.")}
    ${channels.length ? `<div class="table-wrap"><table class="qa"><tr><th>Channel</th><th>Language</th><th>Length</th><th>Style</th><th>Lessons</th></tr>
      ${channels.map((/** @type {any} */ c) => `<tr><td><a href="#/channels/${esc(c.slug)}">${esc(c.name)}</a></td><td>${esc(c.language)}</td><td>${c.seconds} s</td>
        <td>${esc(c.style)}</td><td>${c.lessons_active}${c.lessons_draft ? ` · ${c.lessons_draft} to approve` : ""}</td></tr>`).join("")}</table></div>` : `<p class="muted">No channels yet.</p>`}
    <form class="form panel"><p class="section-title">New channel</p>
      <label>Name<input id="c-name" maxlength="80" required></label>
      <label>Short id <span class="hint">Lowercase letters, digits and dashes, e.g. science-for-kids</span><input id="c-slug" maxlength="40" pattern="[a-z0-9-]+" required></label>
      <label>Language <span class="hint">A code such as en or vi</span><input id="c-language" maxlength="3" value="en" required></label>
      <label>Length in seconds<input id="c-seconds" type="number" min="5" max="900" value="45" required></label>
      <label>Style<select id="c-style">${styles.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join("")}</select></label>
      <div><button class="primary" type="submit">Create the channel</button></div></form><p id="msg" class="muted" role="status"></p>`;
  onSubmit(async () => {
    const c = await post("/channels", { name: field("c-name").value.trim(), slug: field("c-slug").value.trim(), language: field("c-language").value.trim(),
      seconds: Number(field("c-seconds").value), style: /** @type {HTMLSelectElement} */ (document.getElementById("c-style")).value });
    location.hash = `#/channels/${c.slug}`;
    return "";
  });
}

const POINTS = [["script", "Script"], ["voice", "Voice"], ["shots", "Shots (before render)"], ["mix", "Mix"], ["publish", "Publish"]];
/** Five boxes: where a film stops for this person's review (specs/026). @param {string} id @param {string[]} on */
const pointBoxes = (id, on) => `<fieldset class="points" id="${id}"><legend>Stop for my review at <span class="hint">You can change and approve each one on the job page</span></legend>
  ${POINTS.map(([k, l]) => `<label class="check"><input type="checkbox" value="${k}" ${on.includes(k) ? "checked" : ""}> <span>${l}</span></label>`).join("")}</fieldset>`;
const pointsOf = (/** @type {string} */ id) => Array.from(document.querySelectorAll(`#${id} input:checked`)).map((x) => /** @type {HTMLInputElement} */ (x).value);

async function pageChannel(slug) {
  const c = await get(`/channels/${encodeURIComponent(slug)}`);
  const base = `/channels/${encodeURIComponent(slug)}/lessons`;
  const t = (/** @type {string} */ k, /** @type {string} */ label, /** @type {string} */ hint = "") =>
    `<label>${label}${hint ? ` <span class="hint">${hint}</span>` : ""}<input id="p-${k}" value="${esc(c[k] ?? "")}"></label>`;
  const a = (/** @type {string} */ k, /** @type {string} */ label, /** @type {string} */ hint) =>
    `<label>${label} <span class="hint">${hint}</span><textarea id="p-${k}">${esc(Array.isArray(c[k]) ? c[k].join("\n") : c[k] || "")}</textarea></label>`;
  $app.innerHTML = `${back("#/channels", "Channels")}${head("Channel", esc(c.name), `<a class="button primary" href="#/new?channel=${esc(c.slug)}">New film for this channel</a>`)}
    <form class="form panel" id="profile"><p class="section-title">Profile</p>
      ${t("name", "Name")}${t("niche", "Niche")}${t("audience", "Audience")}${t("language", "Language")}${t("seconds", "Length in seconds")}
      ${t("style", "Style")}${t("voice", "Voice", "A voice of the library, e.g. af_bella")}${t("speed", "Speed", "0.5 to 2")}
      ${a("title_rules", "Title rules", "In your own words")}${t("title_max", "Longest title", "20–100 characters, or empty")}
      ${a("thumbnail_rules", "Thumbnail rules", "In your own words")}
      ${a("hashtags", "Hashtags always used", "One per line, like #science; at most 5")}${a("banned", "Words never used", "One per line")}
      ${pointBoxes("p-reviews", c.reviews || ["script", "shots"])}
      <div><button class="primary" type="submit">Save the profile</button></div></form><p id="msg" class="muted" role="status"></p>
    <div class="panel"><p class="section-title">Decisions</p>
      ${(c.decisions || []).length ? `<ul>${c.decisions.map((/** @type {any} */ d) => `<li>${esc(d.date)}: ${esc(d.text)}</li>`).join("")}</ul>` : `<p class="muted">None yet.</p>`}
      <div class="row"><input id="d-text" maxlength="300" placeholder="Something you decided for this channel"><button id="d-add">Add</button></div></div>
    <div class="panel"><p class="section-title">Lessons</p>${lessonsTable(c.lessons || [], base, true)}</div>${LESSON_FORM}
    <div class="panel" id="topics"><p class="section-title">Topics</p><p class="muted">Loading…</p></div>`;
  const again = () => pageChannel(slug);
  fillTopics(slug);
  onSubmit(async () => {
    const num = (/** @type {string} */ k) => field(`p-${k}`).value.trim() === "" ? null : Number(field(`p-${k}`).value);
    await send("PUT", `/channels/${encodeURIComponent(slug)}`, {
      name: field("p-name").value.trim(), niche: field("p-niche").value.trim(), audience: field("p-audience").value.trim(),
      language: field("p-language").value.trim(), seconds: num("seconds"), style: field("p-style").value.trim(),
      voice: field("p-voice").value.trim() || null, speed: num("speed") ?? 1, title_rules: field("p-title_rules").value.trim(),
      title_max: num("title_max"), thumbnail_rules: field("p-thumbnail_rules").value.trim(),
      hashtags: lines(field("p-hashtags").value), banned: lines(field("p-banned").value), reviews: pointsOf("p-reviews") });
    return "Saved.";
  });
  /** @type {HTMLButtonElement} */ (document.getElementById("d-add")).onclick = async () => {
    try { await post(`/channels/${encodeURIComponent(slug)}/decisions`, { text: field("d-text").value.trim() }); again(); }
    catch (e) { alert(e.message); }
  };
  wireLessons(base, again);
}

// ---------- topics of a channel (specs/013) ----------
const VERDICT_CLASS = { PRIORITY: "pass", GO: "pass", HOLD: "muted", DROP: "fail" };
/** @param {string} slug */
async function fillTopics(slug) {
  const box = document.getElementById("topics");
  if (!box) return;
  const base = `/channels/${encodeURIComponent(slug)}`;
  const [d, refs] = await Promise.all([get(`${base}/topics`), get(`${base}/references`)]);
  const byN = Object.fromEntries(d.topics.map((/** @type {any} */ t) => [t.n, t]));
  const row = (/** @type {any} */ t) => {
    const s = t.scores || {}, v = (t.evidence || {}).top_video;
    const url = v && /^https:\/\/www\.youtube\.com\/watch\?v=[\w-]+$/.test(v.url) ? v.url : "";
    return `<tr><td>${t.n}</td><td class="${VERDICT_CLASS[t.verdict] || ""}">${esc(t.verdict)}${d.stale.includes(t.n) ? " (stale)" : ""}</td>
      <td>${esc(t.text)}${t.source === "suggested" ? ' <small class="muted">suggested</small>' : ""}${t.note ? `<br><small class="muted">${esc(t.note)}</small>` : ""}</td>
      <td>${t.total}</td><td>${s.demand}</td><td>${s.heat}</td><td>${s.competition}</td><td>${s.overlap}</td>
      <td><input class="t-fit" data-n="${t.n}" type="number" min="0" max="10" value="${s.fit ?? ""}" aria-label="Fit"></td>
      <td><select class="t-type" data-n="${t.n}" aria-label="Type">${["explainer", "comparison", "list", "true story", "q&a", "other"].map((k) =>
        `<option${k === t.type ? " selected" : ""}>${k}</option>`).join("")}</select></td>
      <td>${url ? `<a href="${url}" target="_blank" rel="noopener noreferrer">${esc(v.title.slice(0, 50))}</a><br><small class="muted">${num(v.views, 0)} views · ${v.age_days} d</small>` : "—"}</td></tr>`;
  };
  const queued = d.queue.map((/** @type {number} */ n) => byN[n]);
  const others = d.topics.filter((/** @type {any} */ t) => !d.queue.includes(t.n));
  box.innerHTML = `<p class="section-title">Topics</p>
    <p class="muted">Score ideas with YouTube numbers: demand, heat, competition, overlap with your films, and fit. ${d.usage.today} of ${d.usage.limit} topics scored today.</p>
    <div class="form"><label>Topics <span class="hint">One per line, up to 20</span><textarea id="t-new" placeholder="why honey never spoils"></textarea></label>
      <label class="check"><input id="t-suggest" type="checkbox"> <span>Suggest up to 10 more for this channel</span></label>
      <div class="row"><button class="primary" id="t-score">Score</button></div><p id="t-msg" class="muted" role="status"></p></div>
    ${queued.length ? `<p class="section-title" style="margin-top:12px">Queue</p>
      <p class="row"><a class="button primary" id="t-make" href="#/new?channel=${esc(slug)}&topic=${queued[0].n}">Make a film from #${queued[0].n}</a>
        <button id="t-recheck">Check the queue again</button></p>` : ""}
    ${d.topics.length ? `<div class="table-wrap"><table class="qa topics"><tr><th>#</th><th>Verdict</th><th>Topic</th><th>Total</th><th>Demand</th><th>Heat</th>
      <th>Competition</th><th>Overlap</th><th>Fit</th><th>Type</th><th>Strongest video</th></tr>${[...queued, ...others].map(row).join("")}</table></div>` : ""}
    <details><summary class="muted">Reference channels (${refs.channels.length})</summary>
      <div class="form"><label>Channel ids <span class="hint">One per line, like UC…; topics they posted in the last 30 days are not taken</span>
        <textarea id="t-refs">${esc(refs.channels.map((/** @type {any} */ r) => r.id).join("\n"))}</textarea></label>
        <div><button id="t-refs-save">Save</button></div></div></details>`;
  /** @type {HTMLButtonElement} */ (document.getElementById("t-score")).onclick = async () => {
    const msg = document.getElementById("t-msg");
    try {
      const j = await post(`${base}/topics/score`, { topics: lines(field("t-new").value), suggest: field("t-suggest").checked });
      msg.className = "muted"; msg.innerHTML = `Scoring… <a href="#/jobs/${esc(j.id)}">follow the job</a>; this page updates when it is done.`;
    } catch (e) { msg.className = "fail"; msg.textContent = e.message; }
  };
  const recheck = document.getElementById("t-recheck");
  if (recheck) recheck.onclick = async () => {        // FR-010: numbers change fast; YouTube's cache keeps a same-day recheck free
    const msg = document.getElementById("t-msg");
    try {
      const j = await post(`${base}/topics/score`, { topics: queued.slice(0, 20).map((/** @type {any} */ t) => t.text) });
      msg.className = "muted"; msg.innerHTML = `Checking again… <a href="#/jobs/${esc(j.id)}">follow the job</a>.`;
    } catch (e) { msg.className = "fail"; msg.textContent = e.message; }
  };
  box.querySelectorAll(".t-type").forEach((el) => { /** @type {HTMLSelectElement} */ (el).onchange = async () => {
    const s = /** @type {HTMLSelectElement} */ (el);
    try { await post(`${base}/topics/${s.dataset.n}/type`, { type: s.value }); } catch (e) { alert(e.message); }
  }; });
  box.querySelectorAll(".t-fit").forEach((el) => { /** @type {HTMLInputElement} */ (el).onchange = async () => {
    const i = /** @type {HTMLInputElement} */ (el);
    try { await post(`${base}/topics/${i.dataset.n}/fit`, { score: Number(i.value) }); fillTopics(slug); } catch (e) { alert(e.message); }
  }; });
  /** @type {HTMLButtonElement} */ (document.getElementById("t-refs-save")).onclick = async () => {
    try { await send("PUT", `${base}/references`, { channels: lines(field("t-refs").value) }); fillTopics(slug); } catch (e) { alert(e.message); }
  };
}

/** @param {string} top */
async function settingsLessons(top) {
  const { lessons } = await get("/lessons/shared");
  $app.innerHTML = `${top}<div class="panel"><p class="section-title">Shared lessons</p>
    <p class="muted">Lessons for every channel of every member. Members do not see them unless one stops their film.</p>
    ${lessonsTable(lessons, "/lessons/shared", false)}</div>${LESSON_FORM}`;
  wireLessons("/lessons/shared", () => settingsLessons(top));
}

const ANGLE = { curiosity: "Curiosity", number: "Number", question: "Question" };
/** The Publish block of a finished film job (specs/011 contracts/api.md). @param {string} film @param {any} sum */
async function fillPublish(film, sum) {
  const box = document.getElementById("publish");
  if (!box) return;
  const base = `${API}/films/${encodeURIComponent(film)}/publish`;
  let p;
  try { p = await get(`/films/${encodeURIComponent(film)}/publish`); }
  catch { box.innerHTML = `<p class="section-title">Publish</p><p class="muted">${sum.cut ? `The publish step was stopped: ${esc(sum.cut)}` : "No publish pack for this film."}</p>`; return; }
  const check = p.check.cut ? `The publish step was stopped: ${esc(p.check.cut)}`
    : p.check.pass ? "Publish check: pass" : `Publish check: ${p.check.problems.length} problem${p.check.problems.length === 1 ? "" : "s"}`;
  const blocked = (sum.blocked_by_lesson || []).map((/** @type {number} */ n) => `#${n}`).join(", ");
  box.innerHTML = `<p class="section-title">Publish</p>
    ${blocked ? `<p class="error">⚠ Do not publish yet: repeats lesson ${blocked}.</p>` : ""}
    <div class="pub-grid">${p.titles.map((/** @type {any} */ t, /** @type {number} */ i) => `<div class="pub-card">
      ${t.thumbnail ? `<img loading="lazy" src="${base}/${encodeURIComponent(t.thumbnail)}" alt="Thumbnail ${i + 1}">` : `<div class="pub-none muted">No picture</div>`}
      <p class="muted">${esc(ANGLE[t.angle] || t.angle)}${t.thumb_text ? ` · on the picture: “${esc(t.thumb_text)}”` : ""}</p>
      <p class="pub-title">${esc(t.text)}</p>
      <button class="copy" data-copy="t${i}">Copy title</button></div>`).join("")}</div>
    <p class="section-title" style="margin-top:14px">Description</p>
    <pre class="pub-desc" id="pub-desc">${esc(p.description)}</pre>
    <div class="row"><button class="copy" data-copy="desc">Copy description</button>
      ${p.subtitles ? `<a class="button" href="${base}/subtitles.srt">Download subtitles</a>` : ""}
      <a class="button" href="${base}.zip">Download pack</a></div>
    <p class="${p.check.pass && !p.check.cut ? "pass" : "muted"}" style="margin-top:10px">${check}</p>
    ${p.check.problems.length ? `<ul class="muted">${p.check.problems.map((/** @type {string} */ x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}`;
  const texts = /** @type {Record<string, string>} */ ({ desc: p.description });
  p.titles.forEach((/** @type {any} */ t, /** @type {number} */ i) => { texts[`t${i}`] = t.text; });
  box.querySelectorAll("button.copy").forEach((el) => {
    const b = /** @type {HTMLButtonElement} */ (el);
    b.onclick = async () => {
      const text = texts[b.dataset.copy || ""] || "";
      try { await navigator.clipboard.writeText(text); }
      catch {                                    // no clipboard: select the description so it can be copied by hand
        const r = document.createRange(); r.selectNodeContents(/** @type {Node} */ (document.getElementById("pub-desc")));
        const sel = window.getSelection(); if (sel) { sel.removeAllRanges(); sel.addRange(r); }
        return;
      }
      const old = b.textContent; b.textContent = "Copied";
      setTimeout(() => { b.textContent = old; }, 2000);
    };
  });
}

// ---------- the parts of a film already done (specs/025) ----------
/** @param {any} j */
function stepHtml(j) {
  const pct = j.progress && j.progress.total ? Math.round((100 * j.progress.done) / j.progress.total) : null;
  return `<p class="section-title">Current step</p>
    <div class="step-row"><p class="step-name">${esc(j.step)}</p>${pct !== null ? `<span class="muted num">${j.progress.done}/${j.progress.total}</span>` : ""}</div>
    ${pct !== null ? `<div class="bar"><i style="width:${pct}%"></i></div>` : ""}`;
}
/** @type {any} */
const DONE = { job: null, data: null, tab: null, group: 0, respelled: false, sheet: 1, shotMode: "sheet", shotCount: 24,
  lines: null, dur: null, labels: null, audio: null, playing: null, drawn: {} };
const fileUrl = (/** @type {string} */ path) => `${API}/jobs/${encodeURIComponent(DONE.job.id)}/files/${path.split("/").map(encodeURIComponent).join("/")}`;
const mmss = (/** @type {number} */ s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;
const shotFile = (/** @type {string} */ id) => `.check/shots/${id}.jpg`;

/** @param {any} j */
async function doneOpen(j) {
  if (!DONE.job || DONE.job.id !== j.id) Object.assign(DONE, { tab: null, group: 0, respelled: false, sheet: 1, shotMode: "sheet",
    shotCount: 24, lines: null, dur: null, labels: null, drawn: {} });
  DONE.job = j;
  DONE.drawn = {};
  RAIL.editing = {}; RAIL.last = {};
  await railRefresh();
  const rv = RAIL.data && RAIL.data.review;
  if (rv && !rv.decision) DONE.tab = rv.kind;            // open on the step that waits for this person
  await doneRefresh();
}
/** @param {boolean} [clicked] a click on a step: always draw it (live updates leave a playing section alone) */
async function doneRefresh(clicked = false) {
  const slot = document.getElementById("done-slot");
  if (!slot || !DONE.job) return;
  let d;
  try { d = await get(`/jobs/${encodeURIComponent(DONE.job.id)}/done`); } catch { return; }
  DONE.data = d;
  if (!d.film) { slot.hidden = true; return; }
  slot.hidden = false;
  const usable = d.steps.filter((/** @type {any} */ s) => d.sections[s.key]);
  if (!DONE.tab || !d.sections[DONE.tab]) DONE.tab = usable.length ? usable[0].key : null;
  if (!slot.querySelector("#done-steps")) {
    slot.innerHTML = `<p class="section-title">Done so far</p><ul class="stages" id="done-steps" role="tablist"></ul><div id="done-body"></div>`;
  }
  slot.querySelector("#done-steps").innerHTML = d.steps.map((/** @type {any} */ s) => {
    const can = !!d.sections[s.key];
    const pct = s.progress ? ` ${Math.round((100 * s.progress.done) / s.progress.total)}%` : "";
    return `<li><button role="tab" data-t="${s.key}" class="st-${s.state}" ${can ? "" : "disabled"} aria-selected="${DONE.tab === s.key}">
      <span class="dot"></span>${esc(s.label)}${pct}</button></li>`;
  }).join("");
  slot.querySelectorAll("#done-steps button:not([disabled])").forEach((b) => {
    /** @type {HTMLElement} */ (b).onclick = () => { DONE.tab = /** @type {HTMLElement} */ (b).dataset.t; doneRefresh(true); };
  });
  const sec = DONE.tab && d.sections[DONE.tab];
  const body = /** @type {HTMLElement} */ (slot.querySelector("#done-body"));
  if (!sec) { body.innerHTML = `<p class="muted">Nothing done yet.</p>`; return; }
  const key = `${DONE.tab}:${sec.version}`;
  if (DONE.drawn.key === key) return;                 // same content: keep what is open (and what is playing)
  if (!clicked && DONE.playing && body.contains(DONE.playing)) return;
  DONE.drawn.key = key;
  stopAudio();
  await ({ script: doneScript, voice: doneVoice, shots: doneShots, mix: doneMix, render: doneRender }[DONE.tab] || (() => {}))(body, sec);
  await editPanel(body);
}
/** specs/026: the edit part of the open section. @param {HTMLElement} body */
async function editPanel(body) {
  if (!RAIL.data) return;
  const pt = TAB_POINT[DONE.tab];
  if (!pt) return;
  if (MODE === "online" && ["running", "queued"].includes(DONE.job.status)) {
    const n = document.createElement("p"); n.className = "muted small"; n.textContent = "Edits open when the film stops for your review.";
    body.prepend(n);
  }
  const edit = { script: async () => { const sc = body.querySelector(".script"); if (sc) sc.remove(); await editScript(body); },
    voice: async () => { body.querySelectorAll(".tbl, .done-actions").forEach((x) => x.remove()); await editVoice(body); },
    mix: async () => editMix(body),
    publish: async () => editPublish(body),
    shots: async () => {
      body.querySelectorAll(".thumbs, .sheet-img, .done-actions.spread, .sheet-img + p, #done-more-shots").forEach((x) => x.remove());
      await editShots(body);
    } }[pt];
  if (edit && (pendingFor(pt) || RAIL.open === pt)) { await edit(); return; }
  if (edit && canEdit(pt)) {                          // not waiting: the read-only view stays, with a way in
    const btn = document.createElement("button");
    btn.className = "btn"; btn.id = "open-edit";
    btn.textContent = { script: "Edit paragraphs", shots: "Change shots", voice: "Change the voice", mix: "Change the mix",
      publish: "Change the publish pack" }[pt];
    btn.onclick = () => { RAIL.open = pt; DONE.drawn = {}; doneRefresh(true); };
    body.prepend(btn);
  }
  approveBar(body, pt);
}
function stopAudio() {
  if (DONE.audio) { DONE.audio.pause(); DONE.audio = null; }
  if (DONE.playing) { DONE.playing.classList.remove("on"); DONE.playing.textContent = "▶"; DONE.playing = null; }
}
const facts = (/** @type {string[]} */ xs) => `<div class="facts">${xs.filter(Boolean).map((x) => `<span>${x}</span>`).join("")}</div>`;
const b = (/** @type {any} */ v) => `<b>${v ?? "—"}</b>`;

/** @param {HTMLElement} body @param {any} s */
function doneScript(body, s) {
  const ed = s.editor;
  body.innerHTML = facts([s.machine != null ? `Machine ${b(s.machine)}/10` : "",
    ed ? `Editor ${b(ed.score)}/10 after ${b(ed.fix_rounds)} fix round${ed.fix_rounds === 1 ? "" : "s"}` : "",
    `${b(num(s.words, 0))} words`, `${b(s.paragraphs)} paragraphs`, s.target_seconds ? `Target ${b(mmss(s.target_seconds))}` : "",
    `${b(s.sources)} sources`])
    + `<div class="script">${s.title ? `<p class="script-title">${esc(s.title)}</p>` : ""}
      ${s.excerpt.map((/** @type {any} */ x) => x.kind === "dir" ? `<p class="dir">${esc(x.text)}</p>`
        : `<p><span class="pid">${esc(x.id)}</span>${esc(x.text)}</p>`).join("")}
      ${s.paragraphs > 9 ? `<p class="muted">… ${s.paragraphs - 9} more paragraphs</p>` : ""}</div>
    <div class="row done-actions"><button class="btn" data-open="SCRIPT.md">Open the full script</button>
      <button class="btn" data-open="SOURCES.md">Sources (${s.sources})</button>
      ${s.rounds.map((/** @type {number} */ n) => `<button class="btn" data-review="${n}">Editor notes, round ${n}</button>`).join("")}</div>
    <div id="done-more"></div>`;
  body.querySelectorAll("[data-open]").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = async () => {
    const r = await fetch(fileUrl(/** @type {HTMLElement} */ (el).dataset.open), { credentials: "same-origin" });
    document.getElementById("done-more").innerHTML = `<pre class="doc">${esc(await r.text())}</pre>`;
  }; });
  body.querySelectorAll("[data-review]").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = async () => {
    const n = /** @type {HTMLElement} */ (el).dataset.review;
    const r = await (await fetch(fileUrl(`.check/review-r${n}.json`), { credentials: "same-origin" })).json();
    document.getElementById("done-more").innerHTML = `<div class="doc"><p><b>Round ${esc(n)}</b> · score ${esc(r.score)}/10${r.model ? ` · ${esc(r.model)}` : ""}</p>
      <ul>${(r.issues || []).map((/** @type {any} */ i) => `<li><b>${esc(i.level)}</b> ${esc(i.para)}: ${esc(i.reason)}</li>`).join("") || "<li>No issues.</li>"}</ul></div>`;
  }; });
}

/** @param {HTMLElement} body @param {any} s */
async function doneVoice(body, s) {
  if (!DONE.lines || DONE.drawn.linesVersion !== s.version) {
    try {
      DONE.lines = await (await fetch(fileUrl("lines.json"), { credentials: "same-origin" })).json();
      DONE.dur = await (await fetch(fileUrl("voices/dur.json"), { credentials: "same-origin" })).json().catch(() => ({}));
    } catch { DONE.lines = []; DONE.dur = {}; }
    DONE.drawn.linesVersion = s.version;
  }
  const paras = s.paras || [];
  const groups = [];
  for (let i = 0; i < paras.length; i += 10) groups.push(paras.slice(i, i + 10));
  if (DONE.group >= groups.length) DONE.group = 0;
  const inGroup = new Set(groups[DONE.group] || []);
  const rows = (DONE.lines || []).filter((/** @type {any} */ l) => DONE.respelled ? l.say : inGroup.has(l.para));
  const has = new Set(Object.keys(DONE.dur || {}));
  body.innerHTML = facts([`${b(s.lines)} lines`, s.voice ? `Voice ${b(esc(s.voice))} · speed ${b(s.speed)}` : "",
    `Voice check: ${b(s.pass ? "pass" : s.pass === false ? "not yet" : "—")}`, `${b(s.respelled)} lines read with a respelling`])
    + `<div class="row done-actions"><span class="seg"><button data-f="all" aria-pressed="${!DONE.respelled}">All lines</button>
        <button data-f="say" aria-pressed="${DONE.respelled}">Respelled only</button></span>
      ${DONE.respelled ? "" : `<label class="muted">Paragraphs <select id="done-group">${groups.map((g, i) =>
        `<option value="${i}"${i === DONE.group ? " selected" : ""}>${esc(g[0])}–${esc(g[g.length - 1])}</option>`).join("")}</select></label>`}</div>
    <div class="tbl"><table class="lines"><thead><tr><th></th><th>Line</th><th>Text</th><th>Length</th></tr></thead><tbody>
    ${rows.map((/** @type {any} */ l) => `<tr><td><button class="play" data-a="${esc(l.id)}" aria-label="Play ${esc(l.id)}" ${has.size && !has.has(l.id) ? "disabled" : ""}>▶</button></td>
      <td class="num">${esc(l.id)} · ${esc(l.para || "")}</td><td>${esc(l.text)}${l.say ? `<span class="say">Read as: “${esc(l.say)}”</span>` : ""}</td>
      <td class="num">${DONE.dur && DONE.dur[l.id] != null ? `${Number(DONE.dur[l.id]).toFixed(1)} s` : "—"}</td></tr>`).join("") || `<tr><td colspan="4" class="muted">No lines.</td></tr>`}
    </tbody></table></div>`;
  body.querySelectorAll(".seg button").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = () => {
    DONE.respelled = /** @type {HTMLElement} */ (el).dataset.f === "say"; doneVoice(body, s);
  }; });
  const g = /** @type {HTMLSelectElement | null} */ (body.querySelector("#done-group"));
  if (g) g.onchange = () => { DONE.group = Number(g.value); doneVoice(body, s); };
  body.querySelectorAll(".play[data-a]").forEach((el) => { /** @type {HTMLButtonElement} */ (el).onclick = () => {
    const was = DONE.playing === el;
    stopAudio();
    if (was) return;
    const a = new Audio(fileUrl(`voices/${/** @type {HTMLElement} */ (el).dataset.a}.wav`));
    DONE.audio = a; DONE.playing = el; el.classList.add("on"); el.textContent = "❚❚";
    a.onended = () => stopAudio();
    a.play().catch(() => stopAudio());
  }; });
}

/** @param {HTMLElement} body @param {any} s */
async function doneShots(body, s) {
  if (s.labels && !DONE.labels) {
    try { DONE.labels = (await (await fetch(fileUrl(".check/labels.json"), { credentials: "same-origin" })).json()).labels || {}; }
    catch { DONE.labels = {}; }
  }
  const ids = Array.from({ length: s.shots }, (_, i) => `S${String(i + 1).padStart(3, "0")}`);
  if (DONE.sheet > s.sheets) DONE.sheet = 1;
  const grid = DONE.shotMode === "grid";
  body.innerHTML = facts([`${b(s.shots)} shots`, `Plan check ${b(s.plan_pass ? "pass" : s.plan_pass === false ? "not yet" : "—")}`,
    `Shot check ${b(s.shots_pass ? "pass" : s.shots_pass === false ? "not yet" : "—")}${s.warnings ? ` · ${s.warnings} style warning${s.warnings === 1 ? "" : "s"}${s.accepted ? " accepted" : ""}` : ""}`,
    s.extras ? `${b(s.extras)} extra frames (speech bubbles, cards)` : ""])
    + `<div class="row done-actions spread"><span class="seg" id="done-mode"><button data-m="sheet" aria-pressed="${!grid}">Contact sheets</button>
        <button data-m="grid" aria-pressed="${grid}">Shot by shot</button></span>
      ${grid ? "" : `<span class="seg">${Array.from({ length: s.sheets }, (_, i) => `<button data-s="${i + 1}" aria-pressed="${DONE.sheet === i + 1}">${i + 1}</button>`).join("")}</span>`}</div>
    ${grid ? `<div class="thumbs">${ids.slice(0, DONE.shotCount).map((id) => {
        const l = (DONE.labels || {})[id] || {};
        return `<figure class="thumb"><img src="${fileUrl(shotFile(id))}" alt="${id}" loading="lazy"><figcaption><code>${id}</code><span class="muted">${esc([l.scale, l.place].filter(Boolean).join(" · "))}</span></figcaption></figure>`;
      }).join("")}</div>${DONE.shotCount < ids.length ? `<p><button class="btn" id="done-more-shots">Show more (${ids.length - DONE.shotCount} left)</button></p>` : ""}`
      : `<img class="sheet-img" src="${fileUrl(`.check/shots/sheet-${DONE.sheet}.jpg`)}" alt="Contact sheet ${DONE.sheet}">
         <p class="muted small">Sheet ${DONE.sheet} of ${s.sheets} · click to enlarge</p>`}
    ${s.accepted ? `<p class="muted small">Accepted: ${esc(s.accepted)}</p>` : ""}`;
  body.querySelectorAll("#done-mode button").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = () => {
    DONE.shotMode = /** @type {HTMLElement} */ (el).dataset.m; doneShots(body, s);
  }; });
  body.querySelectorAll("[data-s]").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = () => {
    DONE.sheet = Number(/** @type {HTMLElement} */ (el).dataset.s); doneShots(body, s);
  }; });
  const more = document.getElementById("done-more-shots");
  if (more) more.onclick = () => { DONE.shotCount += 24; doneShots(body, s); };
  body.querySelectorAll(".sheet-img, .thumb img").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = () => {
    const lb = document.createElement("div"); lb.className = "done-zoom"; lb.setAttribute("role", "dialog");
    lb.innerHTML = `<img src="${/** @type {HTMLImageElement} */ (el).src}" alt="">`;
    lb.onclick = () => lb.remove(); document.body.append(lb);
  }; });
}

/** @param {HTMLElement} body @param {any} s */
function doneMix(body, s) {
  body.innerHTML = facts([s.seconds ? `Length ${b(mmss(s.seconds))}` : "", "Voice + music + sound"])
    + `<audio controls preload="metadata" src="${fileUrl("out/mix.wav")}"></audio>`;
  const a = body.querySelector("audio");
  a.onplay = () => { DONE.playing = a; };
  a.onpause = () => { if (DONE.playing === a) DONE.playing = null; };
}

/** @param {HTMLElement} body @param {any} s */
function doneRender(body, s) {
  const total = s.chunks_total || 0, done = s.chunks_done || 0, w = s.workers || 1;
  body.innerHTML = facts([`${b(done)} of ${b(total)} chunks`, s.mode ? `${b(s.mode === "gpu" ? "GPU" : "Software")}${s.workers ? ` · ${s.workers} workers` : ""}` : ""])
    + `<div class="chunks" aria-label="${done} of ${total} chunks done">${Array.from({ length: total }, (_, i) =>
      `<i class="${i < done ? "d" : i < done + w && done < total ? "r" : ""}"></i>`).join("")}</div>`;
}

// ---------- review points and edits (specs/026) ----------
/** @type {any} */
const RAIL = { data: null, editing: {}, last: {}, msg: {} };
const STATE_LABEL = { done: "Done", running: "Running", waiting: "Waiting for you", todo: "Not yet", stale: "Must run again", skipped: "Skipped" };
const STEP_TAB = { Script: "script", Voice: "voice", Shots: "shots", Mix: "mix", Render: "render", "Self-check": "selfcheck", Publish: "publish" };
const TAB_POINT = { script: "script", voice: "voice", shots: "shots", mix: "mix", publish: "publish" };
const POINT_STEP = { script: "Script", voice: "Voice", shots: "Shots", mix: "Mix", publish: "Publish" };

async function railRefresh() {
  const slot = document.getElementById("rail-slot");
  if (!slot || !DONE.job) return;
  let v;
  try { v = await get(`/jobs/${encodeURIComponent(DONE.job.id)}/steps`); } catch { slot.hidden = true; return; }
  RAIL.data = v;
  slot.hidden = false;
  const wait = v.review && !v.review.decision ? POINT_STEP[v.review.kind] : null;
  slot.innerHTML = `<div class="rail-head"><p class="section-title">Steps</p>
      ${wait ? `<span class="badge s-waiting_review">Waiting for you: ${esc(wait)}</span>` : v.busy ? `<span class="badge">Busy: ${esc(v.busy.step)}</span>` : ""}</div>
    <ol class="rail" role="tablist">${v.steps.map((/** @type {any} */ s, i) => `<li><button class="rs st-${s.state}" data-step="${esc(s.name)}"
        ${STEP_TAB[s.name] ? "" : "disabled"} aria-selected="${STEP_TAB[s.name] === DONE.tab}">
        <span class="n"><span>${i + 1}</span>${s.review_on ? `<span class="gate">REVIEW</span>` : ""}</span>
        <span class="t">${esc(s.name)}</span><span class="s">${esc(s.state === "stale" ? STATE_LABEL.stale : s.approved_at
          ? `Approved ${new Date(s.approved_at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`
          : s.note || STATE_LABEL[s.state] || s.state)}</span></button></li>`).join("")}</ol>
    <div id="impact"></div>
    <div class="point-toggles" id="point-toggles"><span class="muted small">Stop for my review at:</span>
      ${POINTS.map(([k, l]) => {
        const pt = v.points[k], locked = ["approved", "waiting", "skipped"].includes(pt.state) || ["done", "failed", "stopped"].includes(DONE.job.status);
        return `<label class="check small" title="${locked ? esc(`${l}: ${pt.state}`) : ""}"><input type="checkbox" value="${k}" ${pt.on ? "checked" : ""} ${locked ? "disabled" : ""}> <span>${esc(l.replace(" (before render)", ""))}</span></label>`;
      }).join("")}<span class="msg small" id="points-msg"></span></div>`;
  slot.querySelectorAll("#point-toggles input").forEach((el) => { /** @type {HTMLInputElement} */ (el).onchange = async () => {
    const on = Array.from(slot.querySelectorAll("#point-toggles input:checked")).map((x) => /** @type {HTMLInputElement} */ (x).value);
    try { await send("PUT", `/jobs/${encodeURIComponent(DONE.job.id)}/points`, { on }); await railRefresh(); }
    catch (err) { const m = document.getElementById("points-msg"); if (m) m.textContent = /** @type {Error} */ (err).message; }
  }; });
  slot.querySelectorAll("button[data-step]:not([disabled])").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = () => {
    const tab = STEP_TAB[/** @type {HTMLElement} */ (el).dataset.step];
    if (DONE.data && DONE.data.sections[tab]) { DONE.tab = tab; DONE.drawn = {}; doneRefresh(true); railMarks(); }
  }; });
  railMarks();
}
function railMarks() {
  const v = RAIL.data, box = document.getElementById("impact");
  if (!v || !box) return;
  document.querySelectorAll("#rail-slot button[data-step]").forEach((el) =>
    el.setAttribute("aria-selected", String(STEP_TAB[/** @type {HTMLElement} */ (el).dataset.step] === DONE.tab)));
  const pt = TAB_POINT[DONE.tab];
  const hit = pt ? v.impact[pt] : null;
  box.innerHTML = pt ? `<p class="impact"><b>If you change ${esc(POINT_STEP[pt])}:</b> ${hit.length
    ? hit.map((/** @type {string} */ x) => `<span class="chip">↻ ${esc(x)}</span>`).join(" ") + ` <span class="muted">run again, and their approvals stop counting.</span>`
    : `<span class="muted">nothing else runs again.</span>`}</p>` : "";
}
/** The point is waiting for this person's review. @param {string} pt */
const pendingFor = (pt) => RAIL.data && RAIL.data.review && !RAIL.data.review.decision && RAIL.data.review.kind === pt ? RAIL.data.review : null;
/** Edits are open while the job is not finished and the step is not busy. @param {string} pt */
function canEdit(pt) {
  const v = RAIL.data;
  if (!v || !DONE.job || ["done", "failed", "stopped"].includes(DONE.job.status)) return false;
  if (MODE === "online" && !["waiting_review", "waiting_resume"].includes(DONE.job.status)) return false;   // edits run while it waits
  if (v.busy && (v.busy.step === POINT_STEP[pt] || (v.impact[pt] || []).includes(v.busy.step))) return false;
  return v.points[pt] && v.points[pt].state !== "skipped";
}
/** Send one edit and wait for its result (the page never writes a file itself). @param {string} point @param {string} op @param {any} args */
async function sendEdit(point, op, args) {
  const base = RAIL.data.points[point].fingerprint;
  const a = await post(`/jobs/${encodeURIComponent(DONE.job.id)}/actions`, { point, op, args, base });
  for (let i = 0; i < 1200; i++) {
    await new Promise((r) => setTimeout(r, i < 20 ? 300 : 1000));
    const x = await get(`/jobs/${encodeURIComponent(DONE.job.id)}/actions/${a.id}`);
    if (!["queued", "running"].includes(x.status)) { await railRefresh(); return x; }
  }
  throw new Error("The edit is taking long; its result will show in the log.");
}
const editMsg = (/** @type {any} */ x) => x.status === "conflict" ? "Changed since you opened it: reload the page."
  : x.status === "busy" ? (x.result && x.result.error) || "Busy: try again when the running step ends."
  : x.status === "invalid" || x.status === "failed" ? (x.result && x.result.error) || "The edit was not saved."
  : x.result && x.result.code === 1 ? "Saved, but the check does not pass yet." : "Saved.";
/** Approve / request changes for the point shown. @param {HTMLElement} body @param {string} pt @param {string} [blocked] why approve is off */
function approveBar(body, pt, blocked) {
  const r = pendingFor(pt);
  const old = body.querySelector(".approve-bar"); if (old) old.remove();
  if (!r) return;
  const bar = document.createElement("div");
  bar.className = "approve-bar";
  bar.innerHTML = `<div class="row spread"><span class="muted" id="approve-why">${esc(blocked || `Approving lets the film go on after ${POINT_STEP[pt]}.`)}</span>
      <span class="row"><button class="btn" id="ask-changes">Request changes…</button>
      <button class="primary" id="approve" ${blocked ? "disabled" : ""}>Approve ${esc(POINT_STEP[pt].toLowerCase())}</button></span></div>
    <div id="changes-box" hidden><textarea id="changes-note" maxlength="4000" placeholder="What should change?"></textarea>
      <div class="row"><button class="btn" id="send-note">Send back with this note</button></div></div>
    <p class="muted small" id="approve-msg" role="status"></p>`;
  body.prepend(bar);
  const msg = /** @type {HTMLElement} */ (bar.querySelector("#approve-msg"));
  /** @type {HTMLElement} */ (bar.querySelector("#ask-changes")).onclick = () => { /** @type {HTMLElement} */ (bar.querySelector("#changes-box")).hidden = false; };
  /** @type {HTMLElement} */ (bar.querySelector("#approve")).onclick = async (e) => {
    const btn = /** @type {HTMLButtonElement} */ (e.currentTarget); btn.disabled = true;
    try { await post(`/reviews/${encodeURIComponent(r.id)}/decision`, { value: "approve", base: RAIL.data.points[pt].fingerprint }); route(); }
    catch (err) { msg.className = "fail small"; msg.textContent = err.message; btn.disabled = false; }
  };
  /** @type {HTMLElement} */ (bar.querySelector("#send-note")).onclick = async () => {
    const note = /** @type {HTMLTextAreaElement} */ (bar.querySelector("#changes-note")).value.trim();
    if (note.length < 3) { msg.className = "fail small"; msg.textContent = "Say what should change (at least 3 characters)."; return; }
    try { await post(`/reviews/${encodeURIComponent(r.id)}/decision`, { value: "revise", note }); route(); }
    catch (err) { msg.className = "fail small"; msg.textContent = err.message; }
  };
}

/** Script panel: every paragraph, edit one, run the check, approve (US1). @param {HTMLElement} body */
async function editScript(body) {
  let text = "";
  try { text = await (await fetch(fileUrl("SCRIPT.md"), { credentials: "same-origin", cache: "no-store" })).text(); } catch { return; }
  const paras = [];
  for (const ln of text.split("\n")) {
    const m = ln.match(/^\s*\[(P\d+)\]\s*(.*)$/);
    if (m) paras.push({ id: m[1], text: m[2] });
    else if (paras.length && ln.trim() && !ln.trim().startsWith(">")) paras[paras.length - 1].text += " " + ln.trim();
  }
  const box = document.createElement("div");
  box.className = "edit-script";
  const open = () => Object.keys(RAIL.editing).some((k) => k.startsWith("script:"));
  const draw = () => {
    box.innerHTML = paras.map((p) => {
      const ed = RAIL.editing[`script:${p.id}`] !== undefined, last = RAIL.last[`script:${p.id}`];
      return `<div class="para" data-p="${esc(p.id)}"><div class="row spread"><span class="pid">${esc(p.id)}</span>
          ${last ? `<span class="${last.ok ? "pass" : "fail"} small">${esc(last.text)}</span>` : ""}</div>
        ${ed ? `<textarea maxlength="4000" aria-label="Paragraph ${esc(p.id)}">${esc(RAIL.editing[`script:${p.id}`])}</textarea>
          <div class="row"><button class="primary" data-check>Run script check</button><button class="btn" data-cancel>Cancel</button></div>`
        : `<p>${esc(p.text)}</p>${canEdit("script") ? `<button class="btn small" data-edit>Edit</button>` : ""}`}</div>`;
    }).join("");
    box.querySelectorAll("[data-edit]").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = () => {
      const id = /** @type {HTMLElement} */ (el.closest(".para")).dataset.p;
      RAIL.editing[`script:${id}`] = paras.find((p) => p.id === id).text; draw(); bar();
    }; });
    box.querySelectorAll("[data-cancel]").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = () => {
      delete RAIL.editing[`script:${/** @type {HTMLElement} */ (el.closest(".para")).dataset.p}`]; draw(); bar();
    }; });
    box.querySelectorAll("[data-check]").forEach((el) => { /** @type {HTMLButtonElement} */ (el).onclick = async () => {
      const div = /** @type {HTMLElement} */ (el.closest(".para")), id = div.dataset.p;
      const val = /** @type {HTMLTextAreaElement} */ (div.querySelector("textarea")).value;
      /** @type {HTMLButtonElement} */ (el).disabled = true; /** @type {HTMLElement} */ (el).textContent = "Checking…";
      try {
        const x = await sendEdit("script", "script-para", { para: id, text: val });
        const c = (x.result && x.result.check) || {};
        RAIL.last[`script:${id}`] = { ok: x.status === "done" && x.result.code === 0,
          text: editMsg(x) + (c.score != null ? ` Score ${c.score}/10${c.failed && c.failed.length ? ` · failed: ${c.failed.join(", ")}` : ""}` : "") };
        if (x.status === "done") { delete RAIL.editing[`script:${id}`]; paras.find((p) => p.id === id).text = val.replace(/\s+/g, " ").trim(); }
      } catch (err) { RAIL.last[`script:${id}`] = { ok: false, text: /** @type {Error} */ (err).message }; }
      draw(); bar();
    }; });
  };
  const bar = () => {
    const failed = Object.entries(RAIL.last).some(([k, v]) => k.startsWith("script:") && !(/** @type {any} */ (v)).ok);
    approveBar(body, "script", open() ? "Run the script check on your edits before you approve." : failed ? "The script check does not pass yet." : "");
  };
  body.append(box);
  draw(); bar();
}

/** Shots panel: one frame per shot, change set / camera / acting from the kit's catalogue, keep a shot with a reason,
 * run the shot check, approve and render (US2). @param {HTMLElement} body */
async function editShots(body) {
  const v = RAIL.data;
  /** @type {any} */ let doc = null, checks = null;
  try { checks = await (await fetch(fileUrl("checks.json"), { credentials: "same-origin", cache: "no-store" })).json(); } catch { checks = {}; }
  if (v.editable.shots) {
    try { doc = await (await fetch(fileUrl("scenes.json"), { credentials: "same-origin", cache: "no-store" })).json(); } catch { doc = null; }
  }
  const tier = ((checks || {}).tiers || {}).shots || { issues: [] };
  const issues = tier.issues || [];
  const accepted = (tier.style_accept || {}).reason;
  const stale = (v.steps.find((/** @type {any} */ s) => s.name === "Shots") || {}).base !== "done";   // the files, not the review
  RAIL.changed = RAIL.changed || new Set();
  const box = document.createElement("div");
  box.className = "edit-shots";
  RAIL.shotPage = RAIL.shotPage || 24;
  const draw = () => {
    const scenes = doc ? doc.scenes : [];
    const sel = (/** @type {string} */ id, /** @type {string} */ k, /** @type {string[]} */ list, /** @type {string} */ cur) =>
      `<select data-k="${k}" aria-label="${k} of ${esc(id)}" ${canEdit("shots") ? "" : "disabled"}>${(list.includes(cur) ? list : [cur, ...list]).map((x) =>
        `<option${x === cur ? " selected" : ""}>${esc(x)}</option>`).join("")}</select>`;
    const acts = v.catalog ? [...v.catalog.acts, ...Object.entries(v.catalog.act_prefixes).flatMap(([p, xs]) => (/** @type {string[]} */ (xs)).map((x) => `${p}:${x}`))] : [];
    box.innerHTML = (v.editable.shots ? "" : `<p class="muted small">Shots cannot be changed here: ${esc(v.editable.reason)}. You can still keep a shot with a reason and approve.</p>`)
      + `<div class="row done-actions"><button class="btn" id="run-shots" ${canEdit("shots") ? "" : "disabled"}>Run shot check</button>
        <span class="muted small">${stale ? "The shot check has not run on the current film." : `Shot check: ${tier.pass ? "pass" : "not yet"}`}${accepted ? ` · style accepted: ${esc(accepted)}` : ""}</span></div>
      ${(() => {                                     // warnings about the whole film, not one shot
        const ids = new Set(scenes.map((/** @type {any} */ x) => x.id));
        const fw = issues.filter((/** @type {any} */ i) => !ids.has(i.ref) && (i.severity === "warn" || !i.excepted));
        return fw.length ? `<div class="film-warn" data-id="film"><p class="small"><b>The whole film</b></p>
          ${fw.map((/** @type {any} */ i) => `<p class="small"><span class="tag ${i.severity === "warn" ? "warn" : "bad"}">${esc(i.rule)}</span>
            ${esc(String(i.measure ?? ""))}${i.limit ? ` outside ${esc(String(i.limit))}` : ""}</p>`).join("")}
          ${!accepted && fw.some((/** @type {any} */ i) => i.severity === "warn") ? `<button class="btn small" data-style>Keep the style as it is…</button>` : accepted ? `<p class="small pass">Accepted: ${esc(accepted)}</p>` : ""}
          <span class="msg small">${esc(RAIL.msg.film || "")}</span></div>` : "";
      })()}
      <div class="shot-grid">${scenes.slice(0, RAIL.shotPage).map((/** @type {any} */ s) => {
        const mine = issues.filter((/** @type {any} */ i) => i.ref === s.id);
        const blk = mine.filter((/** @type {any} */ i) => i.severity === "block" && !i.excepted), wrn = mine.filter((/** @type {any} */ i) => i.severity === "warn");
        const cam = typeof s.cam === "string" ? s.cam : (s.cam || {}).name || "";
        const act = ((((s.cast || [])[0] || {}).act || [])[0] || [])[1] || "";
        const changed = RAIL.changed.has(s.id);
        return `<figure class="shot ${changed ? "changed" : blk.length ? "issue" : wrn.length && !accepted ? "warn" : ""}" data-id="${esc(s.id)}">
          <img src="${fileUrl(`.check/shots/${s.id}.jpg`)}?v=${Date.now()}" alt="Frame of ${esc(s.id)}" loading="lazy" onerror="this.style.visibility='hidden'">
          <figcaption><span class="row spread"><code>${esc(s.id)}</code><span class="muted small">${Number(s.dur).toFixed(1)} s</span></span>
          ${v.catalog ? `<span class="sel3">${sel(s.id, "set", v.catalog.sets, s.set)}${sel(s.id, "cam", v.catalog.cams, cam)}${act ? sel(s.id, "act", acts, act) : ""}</span>` : ""}
          ${changed ? `<span class="tag acc">changed · run the shot check</span>` : ""}
          ${blk.map((/** @type {any} */ i) => `<span class="tag bad">${esc(i.rule)}</span> <button class="btn small" data-keep="${esc(i.rule)}">Keep it this way…</button>`).join("")}
          ${!accepted ? wrn.map((/** @type {any} */ i) => `<span class="tag warn">style: ${esc(i.rule)}</span> <button class="btn small" data-style>Keep the style as it is…</button>`).join("") : ""}
          <span class="msg small">${esc(RAIL.msg[s.id] || "")}</span></figcaption></figure>`;
      }).join("")}</div>
      ${scenes.length > RAIL.shotPage ? `<p><button class="btn" id="more-shots">Show more (${scenes.length - RAIL.shotPage} left)</button></p>` : ""}`;
    box.querySelectorAll("select[data-k]").forEach((el) => { /** @type {HTMLSelectElement} */ (el).onchange = async () => {
      const fig = /** @type {HTMLElement} */ (el.closest(".shot")), id = fig.dataset.id, msg = /** @type {HTMLElement} */ (fig.querySelector(".msg"));
      msg.textContent = RAIL.msg[id] = "Saving and drawing the shot again…";
      try {
        const x = await sendEdit("shots", "shot", { shot: id, [/** @type {HTMLElement} */ (el).dataset.k]: /** @type {HTMLSelectElement} */ (el).value });
        if (x.status === "done") RAIL.changed.add(id);
        RAIL.msg[id] = editMsg(x);
      } catch (err) { RAIL.msg[id] = /** @type {Error} */ (err).message; }
      DONE.drawn = {}; doneRefresh(true);                 // the page may have been drawn again meanwhile
    }; });
    box.querySelectorAll("[data-keep], [data-style]").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = () => {
      const fig = /** @type {HTMLElement} */ (el.closest("[data-id]")), id = fig.dataset.id, rule = /** @type {HTMLElement} */ (el).dataset.keep;
      const msg = /** @type {HTMLElement} */ (fig.querySelector(".msg"));
      msg.innerHTML = `<input class="reason" maxlength="400" placeholder="Why keep it? (needed)"> <button class="btn small">Keep</button>`;
      /** @type {HTMLElement} */ (msg.querySelector("button")).onclick = async () => {
        const reason = /** @type {HTMLInputElement} */ (msg.querySelector("input")).value.trim();
        if (!reason) { msg.append(" A reason is needed."); return; }
        try {
          const x = rule ? await sendEdit("shots", "except", { shot: id, rule, reason }) : await sendEdit("shots", "accept-style", { reason });
          RAIL.msg[id] = x.status === "done" ? "Kept." : editMsg(x);
        } catch (err) { RAIL.msg[id] = /** @type {Error} */ (err).message; }
        DONE.drawn = {}; doneRefresh(true);
      };
    }; });
    const more = /** @type {HTMLElement | null} */ (box.querySelector("#more-shots"));
    if (more) more.onclick = () => { RAIL.shotPage += 24; draw(); };
    const run = /** @type {HTMLButtonElement} */ (box.querySelector("#run-shots"));
    run.onclick = async () => {
      run.disabled = true; run.textContent = "Checking every shot…";
      try {
        const x = await sendEdit("shots", "shots-check", {});
        if (x.status === "done") { RAIL.changed.clear(); RAIL.msg = {}; }
      } catch (err) { RAIL.msg.film = /** @type {Error} */ (err).message; }
      DONE.drawn = {}; await doneRefresh(true);
    };
  };
  const bar = () => {
    const open = issues.filter((/** @type {any} */ i) => i.severity === "block" && !i.excepted).length;
    const warns = issues.filter((/** @type {any} */ i) => i.severity === "warn").length && !accepted;
    approveBar(body, "shots", RAIL.changed.size || stale ? "Run the shot check on the current film before you approve."
      : open ? `${open} frame problem(s) open: fix the shot or keep it with a reason.`
      : warns ? "Style warnings are open: fix the shot or keep the style with a reason." : "");
    const b = body.querySelector("#approve"); if (b) b.textContent = "Approve and render";
  };
  body.append(box);
  draw(); bar();
}

/** Voice panel: play each line, fix how a word is said ("say"), make one line again, or change the voice or speed
 * of the whole film after a confirmation on the page (US3). The written words come from the script only. @param {HTMLElement} body */
async function editVoice(body) {
  const v = RAIL.data;
  /** @type {any[]} */ let rows = [];
  /** @type {any} */ let checks = {};
  try { rows = await (await fetch(fileUrl("lines.json"), { cache: "no-store" })).json(); } catch { rows = []; }
  try { checks = await (await fetch(fileUrl("checks.json"), { cache: "no-store" })).json(); } catch { checks = {}; }
  const issues = (((checks.tiers || {}).voice || {}).issues) || [];
  const first = rows.find((r) => r && r.id) || {};
  RAIL.voiceAll = RAIL.voiceAll ?? rows.length <= 40;
  const box = document.createElement("div");
  box.className = "edit-voice";
  const ed = canEdit("voice");
  const draw = () => {
    const shown = rows.filter((r) => r && r.id && (RAIL.voiceAll || r.say || issues.some((/** @type {any} */ i) => i.ref === r.id)));
    const speeds = ["0.85", "0.9", "0.95", "1", "1.05", "1.1", "1.15"];
    const sp = String(first.speed ?? 1);
    box.innerHTML = `<div class="row done-actions"><label>Voice <select id="v-voice" ${ed ? "" : "disabled"}>${(v.voices.includes(first.voice) ? v.voices : [first.voice, ...v.voices]).map((x) =>
        `<option${x === first.voice ? " selected" : ""}>${esc(x)}</option>`).join("")}</select></label>
      <label>Speed <select id="v-speed" ${ed ? "" : "disabled"}>${(speeds.includes(sp) ? speeds : [sp, ...speeds]).map((x) => `<option${x === sp ? " selected" : ""}>${x}</option>`).join("")}</select></label>
      <span class="muted small" id="v-confirm"></span>
      <span class="seg"><button data-f="all" aria-pressed="${RAIL.voiceAll}">All lines</button><button data-f="some" aria-pressed="${!RAIL.voiceAll}">With say or warnings</button></span></div>
      ${issues.filter((/** @type {any} */ i) => i.ref === "lines").map((/** @type {any} */ i) => `<p class="notice warn small">${esc(i.measure)}: ${esc(i.fix)}</p>`).join("")}
      <div class="vlines">${shown.map((r) => {
        const mine = issues.filter((/** @type {any} */ i) => i.ref === r.id);
        return `<div class="vline ${mine.length ? "warnl" : ""}" data-id="${esc(r.id)}"><button class="play" data-a="${esc(r.id)}" aria-label="Play ${esc(r.id)}">▶</button>
          <div class="vtxt"><div><code>${esc(r.id)}</code> ${esc(r.text)}</div>
            <label class="small muted">say <input class="say-in" maxlength="400" value="${esc(r.say || "")}" placeholder="as written" ${ed ? "" : "disabled"}></label>
            ${mine.map((/** @type {any} */ i) => `<span class="tag warn small">${esc(i.rule)}${i.text ? `: ${esc(i.text)}` : ""}</span>`).join(" ")}
            <span class="msg small">${esc(RAIL.msg[r.id] || "")}</span></div>
          <div class="vact">${ed ? `<button class="btn small" data-save>Save say</button><button class="btn small" data-remake>Remake line</button>` : ""}</div></div>`;
      }).join("") || `<p class="muted">No line has a "say" or a warning.</p>`}</div>`;
    box.querySelectorAll(".seg button").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = () => { RAIL.voiceAll = /** @type {HTMLElement} */ (el).dataset.f === "all"; draw(); }; });
    box.querySelectorAll(".play[data-a]").forEach((el) => { /** @type {HTMLButtonElement} */ (el).onclick = () => {
      const was = DONE.playing === el; stopAudio(); if (was) return;
      const a = new Audio(fileUrl(`voices/${/** @type {HTMLElement} */ (el).dataset.a}.wav`) + `?v=${Date.now()}`);
      DONE.audio = a; DONE.playing = el; el.classList.add("on"); el.textContent = "❚❚";
      a.onended = () => stopAudio(); a.play().catch(() => stopAudio());
    }; });
    const act = async (/** @type {Element} */ el, /** @type {string} */ op) => {
      const line = /** @type {HTMLElement} */ (el.closest(".vline")), id = line.dataset.id;
      RAIL.msg[id] = op === "voice-remake" ? "Making the line again…" : "Saving…";
      /** @type {HTMLElement} */ (line.querySelector(".msg")).textContent = RAIL.msg[id];
      try {
        if (op === "voice-say") {
          const x = await sendEdit("voice", "voice-say", { line: id, say: /** @type {HTMLInputElement} */ (line.querySelector(".say-in")).value });
          RAIL.msg[id] = editMsg(x) + (x.status === "done" ? " Remake the line to hear it." : "");
        } else {
          const x = await sendEdit("voice", "voice-remake", { line: id });
          RAIL.msg[id] = editMsg(x);
        }
      } catch (err) { RAIL.msg[id] = /** @type {Error} */ (err).message; }
      DONE.drawn = {}; doneRefresh(true);
    };
    box.querySelectorAll("[data-save]").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = () => act(el, "voice-say"); });
    box.querySelectorAll("[data-remake]").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = () => act(el, "voice-remake"); });
    const ask = () => {                                // the whole film is made again: confirm on the page
      const c = /** @type {HTMLElement} */ (box.querySelector("#v-confirm"));
      const voice = /** @type {HTMLSelectElement} */ (box.querySelector("#v-voice")).value, speed = /** @type {HTMLSelectElement} */ (box.querySelector("#v-speed")).value;
      c.innerHTML = `This makes all ${rows.length} lines again. <button class="btn small" id="v-go">Make all again</button> <button class="btn small" id="v-no">Cancel</button>`;
      /** @type {HTMLElement} */ (c.querySelector("#v-no")).onclick = () => draw();
      /** @type {HTMLElement} */ (c.querySelector("#v-go")).onclick = async () => {
        c.textContent = "Making every line again…";
        try { const x = await sendEdit("voice", "voice-set", { voice, speed, confirm: "all" }); RAIL.msg = { film: editMsg(x) }; }
        catch (err) { RAIL.msg = { film: /** @type {Error} */ (err).message }; }
        DONE.drawn = {}; doneRefresh(true);
      };
    };
    /** @type {HTMLElement} */ (box.querySelector("#v-voice")).onchange = ask;
    /** @type {HTMLElement} */ (box.querySelector("#v-speed")).onchange = ask;
  };
  body.append(box);
  draw();
  approveBar(body, "voice", issues.some((/** @type {any} */ i) => i.severity === "block") ? "The voice check has problems: make those lines again." : "");
}

/** Mix panel: pick the music, set the levels inside the allowed ranges, mix again; the picture is not drawn again (US4).
 * @param {HTMLElement} body */
function editMix(body) {
  const r = RAIL.data.mix_ranges, cur = { ...r.defaults, ...(r.current || {}) };
  const ed = canEdit("mix");
  const names = { "seed:7": "Score A (the style's own)", "seed:3": "Score B", "seed:11": "Score C", none: "No music" };
  const box = document.createElement("div");
  box.className = "edit-mix";
  const slider = (/** @type {string} */ k, /** @type {string} */ label, /** @type {number[]} */ rg, /** @type {number} */ val) =>
    `<div class="mixrow"><label for="mx-${k}">${label}</label><input type="range" id="mx-${k}" data-k="${k}" min="${rg[0]}" max="${rg[1]}" step="0.5" value="${val}" ${ed ? "" : "disabled"}>
      <span class="num small" id="mx-${k}-v">${Number(val).toFixed(1)} dB</span></div>`;
  box.innerHTML = `<p class="muted small">A new mix does not draw the picture again: only the sound goes back on the video.</p>
    <div class="choices">${r.music.map((/** @type {string} */ m) => `<button class="choice${m === cur.music ? " on" : ""}" data-m="${m}" ${ed ? "" : "disabled"}>${esc(names[m] || m)}</button>`).join("")}</div>
    ${slider("under", "Music in the pauses (below the voice)", r.under, cur.music_under_voice_db)}
    ${slider("duck", "Music while the voice speaks", r.duck, cur.duck_db)}
    ${slider("sfx", "Sound effects", r.sfx, cur.sfx_db)}
    <div class="row done-actions"><button class="primary" id="mix-go" ${ed ? "" : "disabled"}>Mix again</button><span class="msg small">${esc(RAIL.msg.mix || "")}</span></div>`;
  let music = cur.music;
  box.querySelectorAll(".choice").forEach((el) => { /** @type {HTMLElement} */ (el).onclick = () => {
    music = /** @type {HTMLElement} */ (el).dataset.m;
    box.querySelectorAll(".choice").forEach((x) => x.classList.toggle("on", x === el));
  }; });
  box.querySelectorAll("input[type=range]").forEach((el) => { /** @type {HTMLInputElement} */ (el).oninput = () => {
    /** @type {HTMLElement} */ (box.querySelector(`#mx-${/** @type {HTMLElement} */ (el).dataset.k}-v`)).textContent = `${Number(/** @type {HTMLInputElement} */ (el).value).toFixed(1)} dB`;
  }; });
  /** @type {HTMLElement} */ (box.querySelector("#mix-go")).onclick = async (e) => {
    const btn = /** @type {HTMLButtonElement} */ (e.currentTarget); btn.disabled = true; btn.textContent = "Mixing…";
    const val = (/** @type {string} */ k) => /** @type {HTMLInputElement} */ (box.querySelector(`#mx-${k}`)).value;
    try { const x = await sendEdit("mix", "mix", { music, under: val("under"), duck: val("duck"), sfx: val("sfx") }); RAIL.msg.mix = editMsg(x); }
    catch (err) { RAIL.msg.mix = /** @type {Error} */ (err).message; }
    DONE.drawn = {}; doneRefresh(true);
  };
  body.append(box);
  approveBar(body, "mix");
}

/** Publish panel: pick one of the three titles (with its thumbnail), change the description and hashtags (US5).
 * @param {HTMLElement} body */
async function editPublish(body) {
  /** @type {any} */ let pk = null;
  try { pk = await (await fetch(fileUrl("publish/pack.json"), { cache: "no-store" })).json(); } catch { pk = null; }
  if (!pk || !Array.isArray(pk.titles)) { approveBar(body, "publish"); return; }
  const ed = canEdit("publish");
  let chosen = pk.chosen || 1;
  const box = document.createElement("div");
  box.className = "edit-publish";
  box.innerHTML = `<div class="titles">${pk.titles.map((/** @type {any} */ t, /** @type {number} */ i) => `<label class="title-pick${i + 1 === chosen ? " on" : ""}">
      <input type="radio" name="pub-title" value="${i + 1}" ${i + 1 === chosen ? "checked" : ""} ${ed ? "" : "disabled"}>
      <img src="${fileUrl(`publish/thumbnail-${i + 1}.png`)}" alt="Thumbnail ${i + 1}" onerror="this.onerror=null;this.src=this.src.replace('.png','.jpg')">
      <span><b>${esc(t.text)}</b><span class="muted small">${esc(t.angle)} · on the picture: “${esc((t.thumb || {}).text || "")}”</span></span></label>`).join("")}</div>
    <label class="small muted" for="pub-desc">Description</label><textarea id="pub-desc" maxlength="4000" ${ed ? "" : "disabled"}>${esc(pk.summary || "")}</textarea>
    <label class="small muted" for="pub-tags">Hashtags (3–5, comma between)</label><input id="pub-tags" value="${esc((pk.hashtags || []).join(", "))}" ${ed ? "" : "disabled"}>
    <div class="row done-actions"><button class="primary" id="pub-save" ${ed ? "" : "disabled"}>Save and check</button><span class="msg small">${esc(RAIL.msg.publish || "")}</span></div>`;
  box.querySelectorAll("input[name=pub-title]").forEach((el) => { /** @type {HTMLInputElement} */ (el).onchange = () => {
    chosen = Number(/** @type {HTMLInputElement} */ (el).value);
    box.querySelectorAll(".title-pick").forEach((x) => x.classList.toggle("on", x.contains(el)));
  }; });
  /** @type {HTMLElement} */ (box.querySelector("#pub-save")).onclick = async (e) => {
    const btn = /** @type {HTMLButtonElement} */ (e.currentTarget); btn.disabled = true;
    const args = { chosen: String(chosen), description: /** @type {HTMLTextAreaElement} */ (box.querySelector("#pub-desc")).value,
      hashtags: /** @type {HTMLInputElement} */ (box.querySelector("#pub-tags")).value };
    try { const x = await sendEdit("publish", "publish", args); RAIL.msg.publish = editMsg(x) + ((x.result && x.result.check && x.result.check.problems || []).length ? ` ${x.result.check.problems[0]}` : ""); }
    catch (err) { RAIL.msg.publish = /** @type {Error} */ (err).message; }
    DONE.drawn = {}; doneRefresh(true);
  };
  body.append(box);
  approveBar(body, "publish");
}

/** Live updates on a job page: only what changed, so a playing line or the open section stays (specs/025 R5).
 * @param {string} id */
async function refreshJob(id) {
  let j;
  try { j = await get(`/jobs/${encodeURIComponent(id)}`); } catch { return route(); }
  const old = DONE.job;
  if (!old || old.id !== id || old.status !== j.status || (old.review_ids || []).length !== (j.review_ids || []).length) return route();
  DONE.job = j;
  const sp = document.getElementById("step-panel"); if (sp) sp.innerHTML = stepHtml(j);
  const pr = document.getElementById("job-progress"); if (pr) pr.textContent = j.progress ? `${j.progress.done}/${j.progress.total}` : "—";
  const lg = document.getElementById("job-log");
  if (lg) lg.textContent = j.log.map((/** @type {any} */ l) => `${new Date(l.t).toLocaleTimeString("en-GB")}  ${l.line}`).join("\n") || "No lines yet.";
  await railRefresh();
  if (Object.keys(RAIL.editing).length) return;          // an open edit box stays as it is
  await doneRefresh();
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
    : open && TAB_POINT[open.kind] ? `<p class="notice">This film is waiting for your ${esc(REVIEW[open.kind].toLowerCase())}: change what you want below, then approve.</p>`
    : open ? `<p class="notice">This job is waiting for your review: <a href="#/reviews/${esc(open.id)}">${open.kind === "treatment" ? "review the treatment" : "open the review"}</a>.</p>` : ""}
    ${j.status === "queued" ? `<p class="notice">${j.step === "Waiting for a Claude account" ? "Waiting for a Claude account: the studio owner needs to sign one in on AI accounts." : `In the queue${j.queue_position ? `: number ${j.queue_position}` : ""}. It starts by itself when the studio is free.`}</p>` : ""}
    ${MODE === "online" && j.status === "done" && j.links.film ? `<p><a class="button primary" href="${API}/films/${encodeURIComponent(j.links.film)}/download">Download the film</a>
      <a class="button" href="#/films/${esc(j.links.film)}">Watch it</a></p>
      <details class="panel" id="changes"><summary><strong>Request changes</strong> <span class="muted">· makes a new version and keeps this one</span></summary>
        <textarea id="change-note" maxlength="2000" placeholder="What should be different? For example: a slower ending, warmer colours."></textarea>
        ${j.input && j.input.channel ? `<label class="check"><input id="change-lesson" type="checkbox"> <span>Save this as a lesson for ${esc(j.input.channel)} (you approve it on the channel page)</span></label>` : ""}
        <div class="row" style="margin-top:8px"><button class="primary" id="send-changes">Request changes (uses 1 film credit)</button></div>
        <p id="changes-msg" class="muted" role="status"></p></details>` : ""}
    ${j.status === "waiting_resume" ? `<p class="notice">You decided, but the Claude session is no longer waiting. Open Claude Code again and say “continue job ${esc(j.name)}”.</p>` : ""}
    ${j.status === "inactive" ? `<p class="notice">No updates for over 10 minutes: the Claude session may have closed or stopped.</p>` : ""}
    ${j.error ? `<p class="error">${esc(j.error)}</p>` : ""}
    ${j.kind === "film" ? `<div class="panel rail-panel" id="rail-slot" hidden></div>` : ""}
    <div class="panel" id="step-panel">${stepHtml(j)}</div>
    ${j.kind === "film" ? `<div class="panel done" id="done-slot" hidden></div>` : ""}
    ${qualityHtml(j.qa)}
    ${j.links.film ? `<div id="tiers-slot"></div>` : ""}
    ${j.lesson_draft ? `<p class="notice">A draft lesson (#${j.lesson_draft.n}) is waiting on the <a href="#/channels/${esc(j.lesson_draft.scope)}">channel page</a>: approve it there.</p>` : ""}
    ${j.status === "done" && j.links.film && j.qa && j.qa.publish ? `<div class="panel" id="publish"><p class="section-title">Publish</p><p class="muted">Loading…</p></div>` : ""}
    ${revs ? `<h2>Reviews</h2><ul class="reviews">${revs}</ul>` : ""}
    <h2>Log</h2><pre class="log" id="job-log">${j.log.map((l) => `${new Date(l.t).toLocaleTimeString("en-GB")}  ${esc(l.line)}`).join("\n") || "No lines yet."}</pre>
    </div><aside class="aside panel"><p class="section-title">Summary</p><dl class="kv">
      <dt>Type</dt><dd>${esc(KIND[j.kind] || j.kind)}</dd>
      <dt>Status</dt><dd>${esc(STATUS[j.status] || j.status)}</dd>
      <dt>Progress</dt><dd id="job-progress">${pct !== null ? `${j.progress.done}/${j.progress.total}` : "—"}</dd>
      <dt>Started</dt><dd>${when(j.started_at)}</dd>
      <dt>Updated</dt><dd>${when(j.updated_at)}</dd></dl>
      ${MODE === "online" && !["done", "failed", "stopped"].includes(j.status) ? `<p style="margin-top:14px"><button class="danger" id="stop">Stop this job</button></p>
        <p class="muted" style="font-size:13px">Stopping keeps the film credit used.</p>` : ""}
      ${links ? `<p class="section-title" style="margin-top:18px">Results</p><p style="display:grid;gap:4px;margin:0">${links.replaceAll(" · ", "")}</p>` : ""}
    </aside></div>`;
  if (j.status === "done" && j.links.film && j.qa && j.qa.publish) fillPublish(j.links.film, j.qa.publish);
  if (j.kind === "film") doneOpen(j);
  if (j.links.film) get(`/films/${encodeURIComponent(j.links.film)}`).then((/** @type {any} */ f) => {
    const slot = document.getElementById("tiers-slot");
    if (!slot) return;
    slot.innerHTML = (f.has_video ? `<p class="shot-notes-link"><a class="button" href="#/films/${esc(j.links.film)}">Shot notes</a>
      <span class="muted small">Watch the film shot by shot and write what to fix (specs/029).</span></p>` : "") + tiersHtml(f.tiers);
  }).catch(() => {});
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
      const les = /** @type {HTMLInputElement | null} */ (document.getElementById("change-lesson"));
      const nj = await post("/jobs", { kind: "film", revise_of: j.links.film, note, ...(les && les.checked ? { lesson: true } : {}) });
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
  if (TAB_POINT[r.kind]) {                          // specs/026: a review point is edited and approved on the job page
    location.replace(`#/jobs/${encodeURIComponent(r.job_id)}`);
    return;
  }
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

// The stages a film job reports (CLAUDE.md: job step); Storyboard only when the job asked for one
const STAGES = ["Treatment", "Script", "Look", "Storyboard", "Voice", "Music", "Picture", "Mix", "Render", "Self-check", "Publish"];
const OPEN_STATUS = ["queued", "running", "waiting_review", "waiting_resume"];
const ago = (iso) => {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  return m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${m % 60} min`;
};
/** A film being made: its stages so far, the current one, progress and time (Films page). */
function filmInProgress(j) {
  const seen = new Set(j.log.map((x) => x.line));
  const now = STAGES.indexOf(j.step);
  const skipped = ((j.qa || {}).script || {}).verdict === "skipped";     // no narration: no Script step (specs/010)
  const stages = STAGES.filter((st) => (st === "Storyboard" ? seen.has(st) : st !== "Script" || !skipped || seen.has(st)));
  const track = stages.map((st) => {
    const i = STAGES.indexOf(st);
    const cls = i === now ? "now" : seen.has(st) || (now >= 0 && i < now) ? "done" : "next";   // agents may change the order
    return `<li class="${cls}">${esc(st)}</li>`;
  }).join("");
  const started = j.log.find((x) => x.line === "Started");
  const pct = j.progress && j.progress.total ? Math.round((100 * j.progress.done) / j.progress.total) : null;
  const note = j.status === "queued"
    ? (j.step === "Waiting for a Claude account" ? "Waiting for a Claude account" : `In the queue${j.queue_position ? `: number ${j.queue_position}` : ""}`)
    : j.status === "waiting_review" ? "Waiting for your answer" : `${esc(j.step)}${started ? ` · ${ago(started.t)} so far` : ""}`;
  const idea = (j.input && j.input.idea) || j.name;
  return `<a class="panel making" href="#/jobs/${esc(j.id)}">
    <div class="making-head"><strong>${esc(idea.length > 90 ? idea.slice(0, 88) + "…" : idea)}</strong>${badge(j.status)}</div>
    <p class="muted small">${j.links && j.links.style ? `Style ${esc(j.links.style)} · ` : ""}${note}</p>
    <ol class="stages">${track}</ol>
    ${pct !== null ? `<div class="bar" title="${pct}%"><span style="width:${pct}%"></span></div><p class="muted small">${esc(j.step)}: ${j.progress.done} / ${j.progress.total}</p>` : ""}
  </a>`;
}
async function pageFilms() {
  const [{ films }, { jobs }] = await Promise.all([get("/films"), get("/jobs").catch(() => ({ jobs: [] }))]);
  const making = jobs.filter((j) => j.kind === "film" && OPEN_STATUS.includes(j.status));
  $app.innerHTML = `${head("Results", "Films", MODE === "online" ? "Your films: the ones being made, then the finished ones." : "Rendered films in the films/ folder.")}
    ${making.length ? `<h2>In progress</h2><div class="making-list">${making.map(filmInProgress).join("")}</div><h2>Finished</h2>` : ""}
    ${films.length ? `<div class="grid">${films.map((f) => `<a class="panel card" href="#/films/${esc(f.name)}">
      ${f.has_poster ? `<img src="${API}/films/${esc(f.name)}/poster" alt="">` : ""}<p><strong>${esc(f.name)}</strong>
      ${f.rendering ? '<span class="badge s-running">Rendering</span>' : ""}</p></a>`).join("")}</div>`
    : `<p class="panel muted">${MODE === "online" ? "No finished films yet." : "No films in the films/ folder yet."}</p>`}`;
}

const TIER = { voice: "Voice", plan: "Plan", shots: "Shots", render: "Render", final: "Final" };
/** The film's QC tiers (specs/020): one row per stage, then the open problems. @param {any} t */
function tiersHtml(t) {
  if (!t) return "";
  const rows = t.rows.map((/** @type {any} */ r) => `<tr><td>${esc(TIER[r.tier] || r.tier)}</td>${r.ran
    ? `<td class="${r.pass ? "pass" : "fail"}">${r.pass ? "✓ pass" : "✗ not yet"}${r.skipped_checks ? ` · checks skipped: ${esc(r.skipped_checks)}` : ""}</td>
       <td class="num">${r.problems}</td><td class="num">${r.warnings}${r.style_accepted ? ` <span class="muted">(accepted: ${esc(r.style_accepted)})</span>` : ""}</td>
       <td class="num">${r.exceptions}</td>`
    : `<td class="muted">not run</td><td></td><td></td><td></td>`}</tr>`).join("");
  const open = t.open.map((/** @type {any} */ i) => `<li>${i.warn ? "!" : "✗"} ${esc(TIER[i.tier] || i.tier)} · ${esc(String(i.ref))} · ${esc(i.rule)} ${esc(String(i.measure))}
    <span class="muted">(limit ${esc(String(i.limit))})</span>${i.fix ? ` → ${esc(i.fix)}` : ""}</li>`).join("");
  return `<div class="panel" id="tiers" style="min-width:0"><p class="section-title">Checks by stage</p>
    <div class="table-wrap" style="width:0;min-width:100%"><table><tr><th>Stage</th><th>Result</th><th>Problems</th><th>Warnings</th><th>Exceptions</th></tr>${rows}</table></div>
    ${open ? `<ul class="plain" style="overflow-wrap:anywhere">${open}</ul>${t.open_total > t.open.length ? `<p class="muted">… ${t.open_total - t.open.length} more in CHECKS.md</p>` : ""}` : ""}</div>`;
}

async function pageFilm(name) {
  const f = await get(`/films/${encodeURIComponent(name)}`);
  const base = `${API}/films/${encodeURIComponent(name)}`;
  $app.classList.toggle("wide-film", !!f.has_video);      // room for the Inspector column on the right
  $app.innerHTML = `<div class="film-layout"><div class="film-main"><div class="film-head">${back("#/films", "Films")}${head("Film", esc(f.name), "")}</div>
    ${f.has_video ? `<div id="film-player"><video id="film-video" controls preload="metadata" ${f.has_poster ? `poster="${base}/poster"` : ""}>
        <source src="${base}/video" type="video/mp4">
        ${f.has_subtitles ? `<track kind="subtitles" srclang="vi" label="Subtitles" src="${base}/subtitles.vtt" default>` : ""}
      </video></div><p class="muted">Turn subtitles on or off with the player’s CC button.</p>
      ${MODE === "online" ? `<p class="film-actions" id="film-actions"><a class="button primary" href="${base}/download">Download</a> <button class="danger" id="del-film">Delete this film</button></p>` : ""}`
    : `<p class="notice">${f.rendering ? "The film is still rendering: see progress on the Jobs page." : "No film file yet."}</p>`}
    ${f.has_video ? `<div id="shots-slot"><div class="panel"><p class="section-title">Shots</p><p class="muted">Loading…</p></div></div>` : ""}
    ${tiersHtml(f.tiers)}
    ${f.treatment_html ? `<h2>Script (TREATMENT)</h2><div class="panel md">${f.treatment_html}</div>` : ""}
    ${f.credits ? `<h2>Third-party assets (CREDITS)</h2><pre class="log">${esc(f.credits)}</pre>` : ""}</div>
    ${f.has_video ? `<div class="film-side" id="film-side"><aside class="shot-pane sh-inspector film-inspector" id="sh-pane" aria-label="Inspector"><div class="insp-head"><p class="section-title">Inspector</p><p class="muted small">Loading…</p></div></aside></div>` : ""}</div>`;
  const acts = document.getElementById("film-actions"), side = document.getElementById("film-side");
  if (acts && side) side.appendChild(acts);
  if (f.has_video) filmShots(name, f);
  const del = document.getElementById("del-film");
  if (del) del.onclick = async () => {
    if (!confirm("Delete this film for good?")) return;
    try { await send("DELETE", `/films/${encodeURIComponent(name)}`); location.hash = "#/films"; } catch (e) { alert(e.message); }
  };
}

// ---------- shots and shot notes on the film page (specs/029) ----------
const SHOT_STATUS = { none: "No notes", ok: "No issue", fix: "Needs fix", fixed: "Fixed" };
const SHOT_FILTERS = [["all", "All"], ["fix", "Needs fix"], ["fixed", "Fixed"], ["none", "No notes"]];
/** m:ss.s @param {number} t */
const mss1 = (t) => { const m = Math.floor(t / 60), s = t - 60 * m; return `${m}:${s.toFixed(1).padStart(4, "0")}`; };
/** The Shots section's state (one film page at a time). @type {any} */
let SH = null;

/** @param {string} name @param {any} f */
async function filmShots(name, f) {
  const slot = document.getElementById("shots-slot");
  if (!slot) return;
  const path = `/films/${encodeURIComponent(name)}`;
  let r;
  try { r = await get(`${path}/shots`); }
  catch (e) { slot.innerHTML = `<div class="panel"><p class="section-title">Shots</p><p class="error">${esc(e.message)}</p></div>`; return; }
  const noInspector = () => { // no shot marks: back to one column, Download / Delete under the film again
    const a = document.getElementById("sh-pane"), acts = document.getElementById("film-actions"), fp = document.getElementById("film-player");
    if (a) a.remove();
    if (acts && fp && fp.parentNode) fp.parentNode.insertBefore(acts, fp.nextSibling);
    $app.classList.remove("wide-film");
  };
  if (r.missing || !r.valid) noInspector();
  if (r.missing) {
    slot.innerHTML = `<div class="panel" id="shots"><p class="section-title">Shots</p><p>This film has no shot marks yet.</p>
      <p class="muted">Make them from the film's page (no new render): <code>sh bin/studio shots export ${esc(name)}</code></p></div>`;
    return;
  }
  if (!r.valid) {
    slot.innerHTML = `<div class="panel" id="shots"><p class="section-title">Shots</p><p class="fail">The shot marks file (shots.json) is not valid:</p>
      <ul class="plain">${r.problems.map((/** @type {any} */ p) => `<li>${p.row ? `Row ${p.row}` : "File"} · ${esc(p.rule)}: ${esc(p.detail)}</li>`).join("")}</ul></div>`;
    return;
  }
  SH = { name, path, api: API + path, f, shots: r.shots, stamp: r.video_stamp, duration: r.duration, sel: 0, filter: "all",
    doc: { version: 1, shots: {} }, base: "", orphans: [], stopper: 0, selfSeek: false, prev: null, pending: [], draft: "", drafts: /** @type {Record<string, {text: string, pending: string[]}>} */ ({}), live: /** @type {Record<string, {id: string, at: number | null}>} */ ({}), liveTimer: 0, pv: /** @type {HTMLVideoElement | null} */ (null),
    pin: true, notesError: "", pps: 34 };
  slot.innerHTML = `<div class="panel shots" id="shots">
    <div class="shots-head"><p class="section-title">Shots</p><span class="muted small">${r.shots.length} shots · ${mss1(r.duration || 0)}</span></div>
    <div class="timeline" id="sh-timeline" role="group" aria-label="Shots on the timeline"></div>
    <div class="sh-legend small muted" id="sh-legend"></div>
    <div class="chips sh-filters" id="sh-filters" role="group" aria-label="Filter shots"></div>

    <div class="sh-strip-wrap">
      <div class="row sh-strip-tools"><label class="small muted sh-zoom">Zoom <input type="range" id="sh-zoom" min="10" max="160" step="1" value="34" aria-label="Timeline zoom"></label>
        <span class="small muted" id="sh-zoom-val">34px/s</span><span class="small muted sh-strip-count">${r.shots.length} shots · ${mss1(r.duration || 0)}</span></div>
      <div class="sh-strip-scroll" id="sh-strip-scroll"><div class="sh-ruler" id="sh-ruler"></div><ol class="sh-strip" id="sh-list"></ol></div>
    </div>
    <div id="sh-orphans"></div>
    <div class="sh-claude"><p class="section-title">Fix with Claude</p>
      <div id="sh-fix"></div>
      <p class="muted small">${f.engine === "ae" && MODE === "online" ? "Or paste" : "Paste"} this into your Claude Code chat. Claude lists the open notes, fixes those shots, renders again, replaces the video and ticks each note with a short reply.</p>
      <div class="row"><code id="sh-claude-text">${esc(`Sửa theo ghi chú phim ${name}`)}</code><button type="button" id="sh-claude-copy">Copy</button></div></div>
  </div>`;
  // the shot player takes the film player's place at the top of the page
  const fp = document.getElementById("film-player");
  if (fp) {
    fp.innerHTML = `<div class="sh-canvas" id="sh-canvas"></div>`;
    // the shot strip (and its filters) sits right under the player: click a shot and watch it without scrolling
    const strip = document.querySelector("#shots .sh-strip-wrap"), filters = document.getElementById("sh-filters");
    if (strip) { fp.appendChild(strip); const tools = strip.querySelector(".sh-strip-tools"); if (filters && tools) tools.prepend(filters); }
    if (window.ResizeObserver) new ResizeObserver(() => alignInspector()).observe(fp);
    window.addEventListener("resize", alignInspector);
  }
  const zm = /** @type {HTMLInputElement} */ (document.getElementById("sh-zoom"));
  zm.oninput = () => { SH.pps = +zm.value; /** @type {HTMLElement} */ (document.getElementById("sh-zoom-val")).textContent = `${SH.pps}px/s`; drawList(); };
  const cp = /** @type {HTMLButtonElement} */ (document.getElementById("sh-claude-copy"));
  cp.onclick = () => copyCommand(cp, `Sửa theo ghi chú phim ${name}`);
  // the selected shot plays in the shot pane itself: one video element kept across redraws (moved, not rebuilt)
  const pv = document.createElement("video");
  pv.id = "sh-pane-video"; pv.className = "sh-pane-video"; pv.controls = true; pv.preload = "metadata"; pv.playsInline = true;
  pv.src = `${SH.api}/video?v=${encodeURIComponent(SH.stamp || "")}`;
  if (f.has_subtitles) { const tr = document.createElement("track"); tr.kind = "subtitles"; tr.srclang = "vi"; tr.label = "Subtitles"; tr.src = `${SH.api}/subtitles.vtt`; tr.default = true; pv.appendChild(tr); }
  pv.addEventListener("loadedmetadata", () => { if (SH && SH.pv === pv && pv.currentTime < 0.01) { SH.selfSeek = true; pv.currentTime = SH.shots[SH.sel].t0 + 0.04; } }, { once: true });   // show the real first frame
  pv.addEventListener("seeking", () => { if (!SH || SH.selfSeek) return; stopShot(); });
  pv.addEventListener("seeked", () => { if (SH) SH.selfSeek = false; });
  ["play", "pause", "ended"].forEach((ev) => pv.addEventListener(ev, playButtonState));
  SH.pv = pv;
  drawShots();
  loadNotes();
}
/** The "Fix with Claude" button of an After Effects film in the app (specs/031 FR-010): a fix job on the open notes,
 * or why it cannot start (not AE, no open notes, the desktop app has no AE), or the run in progress. */
function drawFix() {
  const box = document.getElementById("sh-fix");
  if (!box || !SH) return;
  const f = SH.f;
  if (f.engine !== "ae" || MODE !== "online") { box.innerHTML = ""; return; }
  const open = Object.values(SH.doc.shots || {}).reduce((k, /** @type {any} */ sh) => k + (sh.notes || []).filter((/** @type {any} */ n) => !n.done).length, 0);
  if (f.lot) {
    box.innerHTML = `<p><button type="button" class="primary" disabled>Fixing…</button> <span class="small">Claude is fixing ${f.lot.notes.length} note${f.lot.notes.length === 1 ? "" : "s"}
      (marked <span class="sh-lot-badge">in this fix</span>). New notes wait for the next run. <a href="#/jobs/${esc(f.lot.job)}">Follow the job</a></span></p>`;
    return;
  }
  const why = !f.ae_ready ? (f.ae_message || "After Effects is not ready on this computer.") : open ? "" : "No open notes: write what is wrong in a shot first.";
  box.innerHTML = `<p><button type="button" class="primary" id="sh-fix-go"${why ? " disabled" : ""}>Fix with Claude</button>
    <span class="small ${why ? "muted" : ""}">${why ? esc(why) : `Claude fixes ${Math.min(open, 10)} open note${open === 1 ? "" : "s"}${open > 10 ? ` (the first 10 in film order; ${open - 10} wait for the next run)` : ""}, rebuilds only those shots in After Effects and replaces the video (the previous one is kept).`}</span></p>
    <p class="error small" id="sh-fix-err" hidden></p>`;
  const go = /** @type {HTMLButtonElement | null} */ (document.getElementById("sh-fix-go"));
  if (go) go.onclick = async () => {
    go.disabled = true;
    try {
      const r = await send("POST", `${SH.path}/fix`, {});
      SH.f.lot = { job: r.job, notes: r.notes };
      drawFix(); drawNotes();
    } catch (e) {
      const err = /** @type {HTMLElement} */ (document.getElementById("sh-fix-err"));
      err.textContent = /** @type {Error} */ (e).message; err.hidden = false; go.disabled = false;
    }
  };
}
/** A film changed on the server (video replaced, notes answered). Only the open page of that film reacts.
 * @param {Event} e */
function onFilmUpdated(e) {
  let id = "";
  try { id = JSON.parse(/** @type {MessageEvent} */ (e).data).id; } catch { return; }
  if (!SH || SH.name !== id || !location.hash.startsWith("#/films/")) return;
  if (SH.liveRefresh) clearTimeout(SH.liveRefresh);
  SH.liveRefresh = setTimeout(() => { SH.liveRefresh = 0; refreshFilmLive(); }, 300);
}
/** The right column (Inspector, then Download / Delete) spans exactly the shot player: from the top of the video to the
 * Prev / Play / Next row. Long notes scroll inside the Inspector. Off on narrow screens (one column). */
function alignInspector() {
  const side = document.getElementById("film-side"), pl = document.getElementById("film-player"), lay = document.querySelector(".film-layout");
  const insp = document.getElementById("sh-pane"), acts = document.getElementById("film-actions");
  if (!side || !insp) return;
  if (!pl || !lay || !$app.classList.contains("wide-film") || window.innerWidth <= 1100) { side.style.marginTop = ""; insp.style.height = ""; return; }
  const pr = pl.getBoundingClientRect();
  side.style.marginTop = `${Math.max(0, Math.round(pr.top - lay.getBoundingClientRect().top))}px`;
  const gap = acts && acts.parentNode === side ? acts.getBoundingClientRect().height + 12 : 0;
  insp.style.height = `${Math.max(260, Math.round(pr.height - gap))}px`;
}
/** True while the person is typing a note or editing one: their box is never rebuilt under them. */
const typingNote = () => !!(document.activeElement && (document.activeElement.id === "sh-note" || document.activeElement.classList.contains("sh-edit-box"))) || !!document.querySelector(".sh-edit-box");
async function refreshFilmLive() {
  if (!SH) return;
  if (SH.f && SH.f.engine === "ae") {
    try { const f = await get(SH.path); SH.f.lot = f.lot; SH.f.ae_ready = f.ae_ready; SH.f.ae_message = f.ae_message; drawFix(); } catch { /* next event */ }
  }
  try {
    const n = await get(`${SH.path}/notes`);
    if (n.base !== SH.base && !SH.liveTimer) {
      SH.doc = n.doc; SH.base = n.base; SH.orphans = n.orphans || [];
      drawTimeline(); drawFilters(); drawList(); drawOrphans();
      if (typingNote()) refreshPaneStatus(); else drawNotes();
    }
  } catch { /* next event tries again */ }
  try {
    const r = await get(`${SH.path}/shots`);
    if (r.video_stamp && r.video_stamp !== SH.stamp) {
      SH.pendingVideo = r;
      const main = /** @type {HTMLVideoElement | null} */ (document.getElementById("film-video"));
      if ((SH.pv && !SH.pv.paused) || (main && !main.paused)) newVersionBar(true); else applyNewVideo();
    }
  } catch { /* next event tries again */ }
}
/** "A new version of the film is ready" while a video is playing; the person loads it when they want. @param {boolean} on */
function newVersionBar(on) {
  let bar = document.getElementById("sh-newver");
  if (!on) { if (bar) bar.remove(); return; }
  if (bar) return;
  const slot = document.getElementById("shots-slot");
  if (!slot) return;
  bar = document.createElement("div");
  bar.id = "sh-newver"; bar.className = "notice sh-newver"; bar.setAttribute("role", "status");
  bar.innerHTML = `<span>A new version of the film is ready.</span> <button type="button" class="primary" id="sh-newver-load">Load it</button>`;
  slot.prepend(bar);
  /** @type {HTMLElement} */ (bar.querySelector("#sh-newver-load")).onclick = () => applyNewVideo();
}
/** Swap in the replaced video (both players), its shot marks and small pictures; the selected shot stays. */
function applyNewVideo() {
  const r = SH.pendingVideo;
  if (!r) return;
  SH.pendingVideo = null;
  SH.stamp = r.video_stamp;
  if (r.valid) { SH.shots = r.shots; SH.duration = r.duration; SH.sel = Math.min(SH.sel, SH.shots.length - 1); }
  SH.prev = null; SH.f.has_prev = true;
  const src = `${SH.api}/video?v=${encodeURIComponent(SH.stamp)}`;
  const main = /** @type {HTMLVideoElement | null} */ (document.getElementById("film-video"));
  if (main) { main.pause(); main.src = src; main.load(); }
  if (SH.pv) {
    stopShot(); SH.pv.pause();
    const t0 = SH.shots[SH.sel] ? SH.shots[SH.sel].t0 : 0, pv = SH.pv;
    pv.addEventListener("loadedmetadata", () => { SH.selfSeek = true; pv.currentTime = t0 + 0.04; }, { once: true });
    pv.src = src; pv.load();
  }
  newVersionBar(false);
  if (typingNote()) { drawTimeline(); drawFilters(); drawList(); } else drawShots();
}
async function loadNotes() {
  try {
    const n = await get(`${SH.path}/notes`);
    SH.doc = n.doc; SH.base = n.base; SH.orphans = n.orphans || [];
  } catch (e) { SH.notesError = e.message; }
  drawShots();
}
/** Copy, falling back to a selected text box when the clipboard API is refused; "Copied" for 1.5 s.
 * @param {HTMLButtonElement} btn @param {string} text */
async function copyCommand(btn, text) {
  let ok = false;
  try { await navigator.clipboard.writeText(text); ok = true; } catch {
    const t = document.createElement("textarea");
    t.value = text; t.setAttribute("readonly", ""); t.style.position = "fixed"; t.style.opacity = "0";
    document.body.appendChild(t); t.select();
    try { ok = document.execCommand("copy"); } catch { ok = false; }
    t.remove();
  }
  if (!ok) { prompt("Copy this:", text); return; }
  btn.textContent = "Copied";
  setTimeout(() => { btn.textContent = "Copy"; }, 1500);
}
/** @returns {HTMLVideoElement | null} */
/** The video the Shots section drives: the shot pane's own player. @returns {HTMLVideoElement | null} */
const shotVideo = () => (SH && SH.pv) ? SH.pv : /** @type {HTMLVideoElement | null} */ (document.getElementById("film-video"));
/** Status of a shot by id (US2 fills the notes book). @param {string} id */
const shotStatus = (id) => ((SH && SH.doc.shots[id]) || {}).status || "none";
/** @param {any} s */
const shotThumb = (s, w) => `${SH.api}/shots/thumbs/${s.n}/${w}.jpg?v=${encodeURIComponent(SH.stamp || "")}`;
/** img tag that retries every second while the server is still cutting the small pictures (202) */
const thumbImg = (s, w, cls = "") => `<img class="sh-thumb ${cls}" data-src="${shotThumb(s, w)}" alt="" loading="lazy">`;
/** @param {ParentNode} root */
function wireThumbs(root) {
  root.querySelectorAll("img.sh-thumb[data-src]").forEach((el) => {
    const img = /** @type {HTMLImageElement} */ (el), src = img.dataset.src || "";
    let tries = 0;
    img.onerror = () => { if (++tries <= 60) setTimeout(() => { img.src = `${src}&r=${tries}`; }, 1000); };
    img.onload = () => { img.classList.add("ok"); };
    img.src = src;
    img.removeAttribute("data-src");
  });
}
function drawShots() { drawTimeline(); drawFilters(); drawList(); drawPane(); drawOrphans(); }
function drawTimeline() {
  const el = document.getElementById("sh-timeline");
  if (!el) return;
  el.innerHTML = SH.shots.map((/** @type {any} */ s, /** @type {number} */ i) => `<button type="button" class="sh-cell st-${shotStatus(s.id)}${i === SH.sel ? " on" : ""}"
    style="flex-grow:${Math.max(0.001, s.t1 - s.t0).toFixed(3)}" data-i="${i}" title="Shot ${s.n} · ${mss1(s.t0)}–${mss1(s.t1)} · ${esc(SHOT_STATUS[shotStatus(s.id)])}"
    aria-label="Shot ${s.n}, ${esc(SHOT_STATUS[shotStatus(s.id)])}"></button>`).join("");
  el.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => selectShot(+(/** @type {HTMLElement} */ (b).dataset.i || 0), true)));
  const lg = document.getElementById("sh-legend");
  if (lg) lg.innerHTML = ["fix", "fixed", "ok", "none"].map((k) => `<span><i class="sw st-${k}"></i>${SHOT_STATUS[k]}</span>`).join("")
    + `<span><i class="sw sw-on"></i>Selected</span>`;
}
function shotCounts() {
  /** @type {Record<string, number>} */
  const c = { all: SH.shots.length, fix: 0, fixed: 0, none: 0, ok: 0 };
  for (const s of SH.shots) c[shotStatus(s.id)]++;
  return c;
}
function drawFilters() {
  drawFix();                       // the open-note count of "Fix with Claude" follows every change of the notes
  const el = document.getElementById("sh-filters");
  if (!el) return;
  const c = shotCounts();
  el.innerHTML = SHOT_FILTERS.map(([k, label]) => `<button type="button" class="chip${SH.filter === k ? " on" : ""}" data-f="${k}" aria-pressed="${SH.filter === k}">${label}<span>${c[k]}</span></button>`).join("");
  el.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { SH.filter = /** @type {HTMLElement} */ (b).dataset.f; drawFilters(); drawList(); }));
}
/** Open notes of a shot. @param {string} id */
const openNotes = (id) => ((SH.doc.shots[id] || {}).notes || []).filter((/** @type {any} */ n) => !n.done);
function drawList() {
  const el = document.getElementById("sh-list"), ruler = document.getElementById("sh-ruler");
  if (!el) return;
  const pps = SH.pps || 34, all = SH.filter === "all";
  const rows = SH.shots.map((/** @type {any} */ s, /** @type {number} */ i) => ({ s, i }))
    .filter((/** @type {any} */ x) => all || shotStatus(x.s.id) === SH.filter);
  el.innerHTML = rows.length ? rows.map(({ s, i }) => {
    const st = shotStatus(s.id), open = openNotes(s.id), w = Math.max(44, Math.round((s.t1 - s.t0) * pps)) - (all ? 2 : 0);
    const tip = `Shot ${s.n} · ${mss1(s.t0)}–${mss1(s.t1)} · ${(s.t1 - s.t0).toFixed(1)} s · ${SHOT_STATUS[st]}${open.length ? ` · ${open.length} open: ${String(open[0].text || "(picture)").slice(0, 80)}` : ""}`;
    return `<li class="sh-row sh-clip${i === SH.sel ? " on" : ""}" data-i="${i}" tabindex="0" role="button" aria-label="${esc(tip)}" title="${esc(tip)}" style="width:${w}px">
      <span class="sh-thumbs">${thumbImg(s, "a")}${w >= 90 ? thumbImg(s, "b") : ""}${w >= 140 ? thumbImg(s, "c") : ""}</span>
      <span class="sh-n">${s.n}</span>${open.length ? `<span class="sh-dot" aria-hidden="true">${open.length}</span>` : ""}
      <span class="sh-stripe st-${st}"></span>
    </li>`;
  }).join("") : `<li class="muted">No shots with this status.</li>`;
  if (ruler) { // a time ruler under the clips while the whole film shows (filters break the time line)
    ruler.hidden = !all;
    const step = pps >= 20 ? 5 : 10, total = SH.duration || (SH.shots.length ? SH.shots[SH.shots.length - 1].t1 : 0);
    let t = 0, h = "";
    for (; t <= total; t += step) h += `<span style="left:${Math.round(t * pps)}px">${Math.floor(t / 60)}:${String(Math.round(t % 60)).padStart(2, "0")}</span>`;
    ruler.innerHTML = h; ruler.style.width = `${Math.ceil(total * pps)}px`;
  }
  el.querySelectorAll("li.sh-row").forEach((li) => {
    const go = () => selectShot(+(/** @type {HTMLElement} */ (li).dataset.i || 0), true);
    li.addEventListener("click", go);
    li.addEventListener("keydown", (e) => { if (/** @type {KeyboardEvent} */ (e).key === "Enter" || /** @type {KeyboardEvent} */ (e).key === " ") { e.preventDefault(); go(); } });
  });
  wireThumbs(el);
  if (document.getElementById("sh-msg")) unsavedHint();
}
/** @param {number} i @param {boolean} seek */
function selectShot(i, seek) {
  // each shot keeps its own unsaved note (text and pictures): it never follows you to another shot
  const was = SH.shots[SH.sel];
  if (was) flushLive();
  if (was) { if ((SH.draft || "").trim() || SH.pending.length) SH.drafts[was.id] = { text: SH.draft || "", pending: SH.pending }; else delete SH.drafts[was.id]; }
  SH.sel = Math.max(0, Math.min(SH.shots.length - 1, i));
  const d = SH.drafts[SH.shots[SH.sel].id];
  SH.draft = d ? d.text : ""; SH.pending = d ? d.pending : [];
  stopShot();
  document.querySelectorAll("#sh-timeline .sh-cell").forEach((b) => b.classList.toggle("on", /** @type {HTMLElement} */ (b).dataset.i === String(SH.sel)));
  document.querySelectorAll("#sh-list .sh-row").forEach((b) => b.classList.toggle("on", /** @type {HTMLElement} */ (b).dataset.i === String(SH.sel)));
  const onClip = document.querySelector("#sh-list .sh-row.on");
  if (onClip) onClip.scrollIntoView({ block: "nearest", inline: "nearest" });
  drawPane();
  const v = shotVideo();
  if (seek && v) { v.pause(); SH.selfSeek = true; v.currentTime = SH.shots[SH.sel].t0 + 0.04; }   // just inside the shot: the cut frame belongs to the shot before
}
function stopShot() { if (SH && SH.stopper) { cancelAnimationFrame(SH.stopper); SH.stopper = 0; } }
/** Play one shot from its start and stop at its end (research R4). @param {HTMLVideoElement} v @param {number} t0 @param {number} t1 */
function playRange(v, t0, t1) {
  if (v === shotVideo()) { stopShot(); SH.selfSeek = true; }
  v.currentTime = t0;
  v.play().catch(() => {});
  const tick = () => {
    if (v.currentTime >= t1 - 0.03 || v.ended) { v.pause(); if (v === shotVideo()) SH.stopper = 0; return; }
    const id = requestAnimationFrame(tick);
    if (v === shotVideo()) SH.stopper = id;
  };
  const id = requestAnimationFrame(tick);
  if (v === shotVideo()) SH.stopper = id;
}
function drawPane() {
  const el = document.getElementById("sh-pane"), cv = document.getElementById("sh-canvas");
  if (!el || !cv) return;
  const s = SH.shots[SH.sel], st = shotStatus(s.id);
  cv.innerHTML = `<div class="sh-media" id="sh-media"></div>
    <div class="row sh-nav"><button type="button" id="sh-prev"${SH.sel === 0 ? " disabled" : ""} aria-label="Previous shot">← Prev</button>
      <button type="button" class="primary sh-roundbtn" id="sh-play" aria-label="Play this shot" title="Play this shot"></button>
      <button type="button" id="sh-next"${SH.sel === SH.shots.length - 1 ? " disabled" : ""} aria-label="Next shot">Next →</button>
      <span class="small muted sh-range">${mss1(s.t0)}–${mss1(s.t1)} · ${(s.t1 - s.t0).toFixed(1)} s</span></div>`;
  const nn = ((SH.doc.shots[s.id] || {}).notes || []).length;
  el.innerHTML = `<div class="insp-head">
      <p class="section-title">Inspector</p>
      <div class="sh-pane-head insp-title"><strong>Shot ${s.n}</strong><span class="badge st-badge st-${st}">${SHOT_STATUS[st]}</span></div>
      <div class="insp-tags"><span class="tag">${esc(s.id)}</span><span class="tag">${mss1(s.t0)}–${mss1(s.t1)}</span><span class="tag">${(s.t1 - s.t0).toFixed(1)} s</span>${s.set ? `<span class="tag">${esc(s.set)}</span>` : ""}<span class="tag">${nn} note${nn === 1 ? "" : "s"}</span></div>
    </div>
    ${SH.f.has_prev ? `<div class="insp-sec sh-prev"><button type="button" class="insp-btn" id="sh-prev-version"><span aria-hidden="true">↺</span> Watch the previous version</button><div id="sh-prev-slot"></div></div>` : ""}
    <div id="sh-notes"></div>`;
  const media = cv.querySelector("#sh-media");
  if (media && SH.pv) media.appendChild(SH.pv);   // no poster: the small strip picture blown up looks blurred; the real frame shows
  drawNotes();
  wireThumbs(el);
  zoomable(el);
  /** @type {HTMLElement} */ (cv.querySelector("#sh-prev")).onclick = () => selectShot(SH.sel - 1, true);
  /** @type {HTMLElement} */ (cv.querySelector("#sh-next")).onclick = () => selectShot(SH.sel + 1, true);
  /** @type {HTMLElement} */ (cv.querySelector("#sh-play")).onclick = () => {
    const v = shotVideo();
    if (!v) return;
    if (!v.paused) { stopShot(); v.pause(); playButtonState(); return; }      // playing: the button is a pause button
    playRange(v, s.t0, s.t1);
  };
  playButtonState();
  const pv = /** @type {HTMLElement | null} */ (el.querySelector("#sh-prev-version"));
  if (pv) pv.onclick = () => playPrevious(s.id);
}
/** "▶ Play this shot" while stopped; a round pause button while the shot plays (click it to stop). */
function playButtonState() {
  const b = document.getElementById("sh-play"), v = shotVideo();
  if (!b || !v) return;
  const playing = !v.paused && !v.ended;
  b.setAttribute("aria-label", playing ? "Pause" : "Play this shot");
  b.title = playing ? "Pause" : "Play this shot";
  b.innerHTML = playing ? '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><rect x="6" y="5" width="4" height="14" rx="1" fill="currentColor"/><rect x="14" y="5" width="4" height="14" rx="1" fill="currentColor"/></svg>'
    : '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l10.5-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5z" fill="currentColor"/></svg>';
}
/** The same shot (by id) in the one previous video kept by `film replace` (FR-014a). @param {string} id */
async function playPrevious(id) {
  const slot = document.getElementById("sh-prev-slot");
  if (!slot) return;
  try {
    if (!SH.prev) SH.prev = await get(`${SH.path}/shots?prev=1`);
  } catch (e) { slot.innerHTML = `<p class="small fail">${esc(e.message)}</p>`; return; }
  const ps = (SH.prev.shots || []).find((/** @type {any} */ x) => x.id === id);
  if (!ps) { slot.innerHTML = `<p class="small muted">This shot is not in the previous version.</p>`; return; }
  slot.innerHTML = `<p class="small muted">Previous version · shot ${ps.n} · ${mss1(ps.t0)}–${mss1(ps.t1)}</p>
    <video id="sh-prev-video" class="sh-prev-video" controls muted preload="metadata" src="${SH.api}/video?prev=1"></video>`;
  const v = /** @type {HTMLVideoElement} */ (slot.querySelector("video"));
  const main = shotVideo();
  if (main) { stopShot(); main.pause(); }
  const go = () => playRange(v, ps.t0, ps.t1);
  if (v.readyState >= 1) go(); else v.addEventListener("loadedmetadata", go, { once: true });
}

/** One note as a list item. @param {any} n @param {string} sid @param {boolean} canEdit */
function noteHtml(n, sid, canEdit) {
  const s = SH.shots.find((/** @type {any} */ x) => x.id === sid);
  const at = n.at === null || n.at === undefined ? "" : s
    ? `<button type="button" class="link sh-at" data-at="${s.t0 + n.at}" title="Jump to ${mss1(s.t0 + n.at)} in the film">at ${mss1(n.at)}</button>`
    : `<span class="muted">at ${mss1(n.at)}</span>`;
  return `<li class="sh-note${n.done ? " done" : ""}" data-id="${esc(n.id)}">
    ${canEdit ? `<input type="checkbox" class="sh-done" ${n.done ? "checked" : ""} aria-label="Fixed" title="Fixed">` : `<span>${n.done ? "✓" : "•"}</span>`}
    <div class="sh-note-body">
      <div class="sh-note-text">${at} ${esc(n.text)}</div>
      ${n.images && n.images.length ? `<div class="sh-note-imgs">${n.images.map((/** @type {string} */ f) => `<img src="${SH.api}/notes/images/${esc(f)}" data-zoom alt="Picture of this note">`).join("")}</div>` : ""}
      ${n.reply ? `<div class="sh-reply small"><strong>Claude:</strong> ${esc(n.reply)}</div>` : ""}
      ${SH.f && SH.f.lot && (SH.f.lot.notes || []).includes(n.id) ? `<span class="sh-lot-badge small">in this fix</span>` : ""}
      <div class="muted small">${esc(n.by || "")} · ${when(n.updated || n.created)}</div>
    </div>
    ${canEdit ? `<div class="sh-note-tools"><button type="button" class="link sh-edit">Edit</button><button type="button" class="link danger sh-del">Delete</button></div>` : ""}
  </li>`;
}
function drawNotes() {
  const el = document.getElementById("sh-notes");
  if (!el) return;
  const s = SH.shots[SH.sel], sh = SH.doc.shots[s.id] || { status: "none", notes: [] }, st = sh.status || "none";
  el.innerHTML = `${SH.notesError ? `<p class="error">${esc(SH.notesError)}</p>` : ""}
    <div class="insp-sec"><p class="insp-label">Status</p><div class="seg sh-status" role="group" aria-label="Shot status">${["ok", "fix", "fixed"].map((k) => `<button type="button" data-st="${k}" class="${st === k ? "on" : ""}" aria-pressed="${st === k}">${SHOT_STATUS[k]}</button>`).join("")}</div></div>
    <div class="insp-sec"><p class="insp-label">Notes</p><ul class="sh-notes">${(sh.notes || []).filter((/** @type {any} */ n) => !SH.live[s.id] || n.id !== SH.live[s.id].id).map((/** @type {any} */ n) => noteHtml(n, s.id, true)).join("") || (SH.live[s.id] ? "" : `<li class="muted small">No notes on this shot yet.</li>`)}</ul></div>
    <div class="insp-sec sh-add"><p class="insp-label">Add a note</p>
      <textarea id="sh-note" maxlength="2000" rows="3" placeholder="What is wrong in this shot? Type it (saved as you type) or paste a screenshot with Ctrl+V.">${esc(SH.draft || "")}</textarea>
      <div class="sh-pending" id="sh-pending"></div>
      <div class="row sh-add-row">
        <label class="check"><input type="checkbox" id="sh-pin"${SH.pin ? " checked" : ""}> <span>Pin to current time</span></label>
        <label class="button sh-file">Add picture<input type="file" id="sh-file" accept="image/png,image/jpeg,image/webp" hidden></label>
        <span class="muted small" id="sh-count">${(SH.draft || "").length}/2000</span>
        <button type="button" id="sh-add" title="Keep this note and start another one for this shot">New note</button>
      </div>
      <p class="small" id="sh-msg" role="status"></p>
    </div>`;
  drawPending();
  unsavedHint();
  zoomable(el);
  const ta = /** @type {HTMLTextAreaElement} */ (el.querySelector("#sh-note"));
  ta.addEventListener("input", () => { SH.draft = ta.value; /** @type {HTMLElement} */ (el.querySelector("#sh-count")).textContent = `${ta.value.length}/2000`; unsavedHint(); scheduleLive(); });
  ta.addEventListener("blur", () => flushLive());
  ta.addEventListener("paste", (e) => {
    const items = Array.from(/** @type {ClipboardEvent} */ (e).clipboardData?.items || []).filter((it) => it.kind === "file" && it.type.startsWith("image/"));
    if (!items.length) return;                     // text goes into the box as usual
    e.preventDefault();
    items.forEach((it) => { const f = it.getAsFile(); if (f) addPicture(f); });
  });
  const pin = /** @type {HTMLInputElement} */ (el.querySelector("#sh-pin"));
  pin.onchange = () => { SH.pin = pin.checked; };
  const file = /** @type {HTMLInputElement} */ (el.querySelector("#sh-file"));
  file.onchange = () => { Array.from(file.files || []).forEach(addPicture); file.value = ""; };
  /** @type {HTMLElement} */ (el.querySelector("#sh-add")).onclick = () => addNote();
  el.querySelectorAll(".sh-status button").forEach((b) => b.addEventListener("click", () => {
    const k = /** @type {HTMLElement} */ (b).dataset.st;
    saveNotes((doc) => { const x = doc.shots[s.id] || (doc.shots[s.id] = { status: "none", status_by: "auto", notes: [] }); x.status = k; x.status_by = "user"; });
  }));
  wireNoteItems(el, s.id);
}
/** Ticks, edits, deletes and jumps of the notes under `root` (a shot's pane or the gone-shots list). @param {ParentNode} root @param {string} sid */
function wireNoteItems(root, sid) {
  /** @param {any} doc @param {string} id */
  const find = (doc, id) => { const ns = (doc.shots[sid] || {}).notes || []; return { ns, i: ns.findIndex((/** @type {any} */ n) => n.id === id) }; };
  root.querySelectorAll(".sh-note").forEach((li) => {
    const id = /** @type {HTMLElement} */ (li).dataset.id || "";
    const done = /** @type {HTMLInputElement | null} */ (li.querySelector(".sh-done"));
    if (done) done.onchange = () => saveNotes((doc) => { const { ns, i } = find(doc, id); if (i >= 0) ns[i].done = done.checked; });
    const del = /** @type {HTMLElement | null} */ (li.querySelector(".sh-del"));
    if (del) del.onclick = () => {
      if (!confirm("Delete this note?")) return;
      saveNotes((doc) => { const { ns, i } = find(doc, id); if (i >= 0) ns.splice(i, 1); });
    };
    const edit = /** @type {HTMLElement | null} */ (li.querySelector(".sh-edit"));
    if (edit) edit.onclick = () => {
      const body = /** @type {HTMLElement} */ (li.querySelector(".sh-note-text"));
      const cur = find(SH.doc, id);
      if (cur.i < 0) return;
      body.innerHTML = `<textarea maxlength="2000" rows="3" class="sh-edit-box">${esc(cur.ns[cur.i].text)}</textarea>
        <div class="row"><button type="button" class="primary sh-save">Save</button><button type="button" class="sh-cancel">Cancel</button></div>`;
      const box = /** @type {HTMLTextAreaElement} */ (body.querySelector("textarea"));
      box.focus();
      /** @type {HTMLElement} */ (body.querySelector(".sh-cancel")).onclick = () => drawShots();
      /** @type {HTMLElement} */ (body.querySelector(".sh-save")).onclick = () => {
        const text = box.value;
        saveNotes((doc) => { const { ns, i } = find(doc, id); if (i >= 0) ns[i].text = text; });
      };
    };
    const at = /** @type {HTMLElement | null} */ (li.querySelector(".sh-at"));
    if (at) at.onclick = () => { const v = shotVideo(); if (v) { stopShot(); v.currentTime = +(at.dataset.at || 0); } };
  });
}
/** After a save made while typing: the shot's badge and status buttons, without rebuilding the note box. */
function refreshPaneStatus() {
  const s = SH.shots[SH.sel];
  if (!s) return;
  const st = shotStatus(s.id), b = document.querySelector("#sh-pane .sh-pane-head .badge");
  if (b) { b.className = `badge st-badge st-${st}`; b.textContent = SHOT_STATUS[st]; }
  const cur = (SH.doc.shots[s.id] || {}).status || "none";
  document.querySelectorAll("#sh-notes .sh-status button").forEach((x) => { const on = /** @type {HTMLElement} */ (x).dataset.st === cur; x.classList.toggle("on", on); x.setAttribute("aria-pressed", String(on)); });
}
function drawPending() {
  const el = document.getElementById("sh-pending");
  if (!el) return;
  el.innerHTML = SH.pending.map((/** @type {string} */ f, /** @type {number} */ i) => `<span class="sh-pend"><img src="${SH.api}/notes/images/${esc(f)}" data-zoom alt="Picture to add">
    <button type="button" class="link" data-i="${i}" aria-label="Remove this picture">×</button></span>`).join("");
  zoomable(el);
  el.querySelectorAll("button[data-i]").forEach((b) => b.addEventListener("click", () => { SH.pending.splice(+(/** @type {HTMLElement} */ (b).dataset.i || 0), 1); drawPending(); flushLive(); }));
}
/** Save state of the note being typed: "Saving…" while a save waits, then "Saved". */
function unsavedHint() {
  const m = document.getElementById("sh-msg");
  if (!m || (m.textContent && !m.dataset.unsaved)) return;
  const dirty = !!((SH.draft || "").trim() || SH.pending.length), cur = SH.shots[SH.sel];
  m.dataset.unsaved = "1"; m.className = "small muted";
  m.textContent = SH.liveTimer ? "Saving…" : (dirty && cur && SH.live[cur.id] ? "Saved" : "");
}
function scheduleLive() {
  if (SH.liveTimer) clearTimeout(SH.liveTimer);
  SH.liveTimer = setTimeout(() => { SH.liveTimer = 0; flushLive(); }, 1000);
  unsavedHint();
}
/** Typing is the note (no Add button): create the shot's note on the first save, then keep updating that same note;
 * an emptied box removes it. Called after 1 s without typing, on a picture, on leaving the box and on switching shots. */
function flushLive() {
  if (SH.liveTimer) { clearTimeout(SH.liveTimer); SH.liveTimer = 0; }
  const s = SH.shots[SH.sel];
  if (!s) return;
  const text = (SH.draft || "").trim().slice(0, 2000), images = SH.pending.slice();
  let live = SH.live[s.id];
  if (!live) {
    if (!text && !images.length) { unsavedHint(); return; }
    const v = shotVideo();
    let at = null;
    if (SH.pin && v && v.currentTime >= s.t0 && v.currentTime <= s.t1) at = Math.round((v.currentTime - s.t0) * 10) / 10;
    live = SH.live[s.id] = { id: "n-" + Array.from(crypto.getRandomValues(new Uint8Array(4)), (b) => b.toString(16).padStart(2, "0")).join(""), at };
  }
  const id = live.id, at = live.at, sid = s.id;
  if (!text && !images.length) delete SH.live[sid];
  saveNotes((doc) => {
    const x = doc.shots[sid] || (doc.shots[sid] = { status: "none", status_by: "auto", notes: [] });
    const i = x.notes.findIndex((/** @type {any} */ n) => n.id === id);
    if (!text && !images.length) { if (i >= 0) x.notes.splice(i, 1); return; }
    if (i < 0) x.notes.push({ id, at, text, images, done: false });
    else { x.notes[i].text = text; x.notes[i].images = images; }
  }, () => unsavedHint(), true);
}
/** @param {string} text @param {boolean} [bad] */
function shotMsg(text, bad = false) {
  const m = document.getElementById("sh-msg");
  if (m) { m.dataset.unsaved = ""; m.className = `small ${bad ? "fail" : "muted"}`; m.textContent = text; }
}
/** Upload one picture (pasted or chosen) for the note being written. @param {File} file */
async function addPicture(file) {
  const pend = SH.pending;                          // the picture belongs to the shot it was added on
  if (pend.length >= 4) { shotMsg("A note can have up to 4 pictures.", true); return; }
  if (file.size > 10 * 1024 * 1024) { shotMsg("The picture is larger than 10 MB.", true); return; }
  shotMsg("Adding the picture…");
  const fd = new FormData();
  fd.append("file", file, file.name || "pasted.png");
  try {
    const r = await fetch(`${SH.api}/notes/images`, { method: "POST", headers: { "X-Studio": "1" }, body: fd });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw failed(r, body);
    pend.push(body.file);
    drawPending();
    shotMsg("");
    if (pend === SH.pending) flushLive();
  } catch (e) { shotMsg(e.message, true); }
}
function addNote() {
  const s = SH.shots[SH.sel];
  if (!(SH.draft || "").trim() && !SH.pending.length) { shotMsg("Type the note or paste a picture first.", true); return; }
  if ((SH.draft || "").length > 2000) { shotMsg("A note can have up to 2,000 characters.", true); return; }
  flushLive();
  delete SH.live[s.id]; delete SH.drafts[s.id];
  SH.draft = ""; SH.pending = [];
  drawPane();
}
/** Save the notes book with the fingerprint read (FR-009); on "changed" apply the same change to the new book once.
 * @param {(doc: any) => void} op @param {() => void} [ok] @param {boolean} [quiet] keep the pane (and the box being typed in) */
async function saveNotes(op, ok, quiet = false) {
  /** @param {string} base @param {any} doc */
  const put = async (base, doc) => {
    const r = await fetch(`${SH.api}/notes`, { method: "PUT", headers: { "Content-Type": "application/json", "X-Studio": "1" },
      body: JSON.stringify({ base, doc }) });
    return { r, body: await r.json().catch(() => ({})) };
  };
  let doc = structuredClone(SH.doc);
  op(doc);
  try {
    let { r, body } = await put(SH.base, doc);
    if (r.status === 409 && body.error && body.error.current) {
      doc = structuredClone(body.error.current.doc);
      op(doc);
      ({ r, body } = await put(body.error.current.base, doc));
      if (r.status === 409) {
        await loadNotes();
        shotMsg("Someone else just changed these notes; they were loaded again. Try once more.", true);
        return;
      }
    }
    if (!r.ok) throw failed(r, body);
    SH.doc = body.doc; SH.base = body.base;
    if (ok) ok();
    if (quiet) { drawTimeline(); drawFilters(); drawList(); refreshPaneStatus(); } else drawShots();
  } catch (e) { shotMsg(e.message, true); }
}
function drawOrphans() {
  const el = document.getElementById("sh-orphans");
  if (!el) return;
  if (!SH.orphans.length) { el.innerHTML = ""; return; }
  el.innerHTML = `<div class="sh-gone"><p class="section-title">Notes of shots that are gone</p>
    <p class="muted small">These shots are not in the film's shot marks any more. Their notes are kept.</p>
    ${SH.orphans.map((/** @type {string} */ id) => `<div class="sh-gone-shot" data-sid="${esc(id)}"><strong>${esc(id)}</strong>
      <ul class="sh-notes">${((SH.doc.shots[id] || {}).notes || []).map((/** @type {any} */ n) => noteHtml(n, id, true)).join("")}</ul></div>`).join("")}</div>`;
  el.querySelectorAll(".sh-gone-shot").forEach((g) => wireNoteItems(g, /** @type {HTMLElement} */ (g).dataset.sid || ""));
  zoomable(el);
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

/** A learned style takes only the rendering engine (camera, character rig, focus set-up) from a library style. */
const ENGINE_TIP = "The look and rules come from the measured videos; only the rendering engine (camera, character rig, focus set-up) is taken from this library style.";

async function pageStyles() {
  const { styles } = await get("/styles");
  $app.innerHTML = `${head("Browse", "My styles", "Styles you learned and saved in my-styles/, ready for making films.")}${styles.length ? `<div class="grid">${styles.map((s) => `<article class="panel card my-card" data-slug="${esc(s.slug)}" tabindex="0">
      ${s.has_styleframe ? `<img src="${API}/styles/${esc(s.slug)}/styleframe" alt="">` : ""}
      <p><strong>${esc(s.en || s.slug)}</strong><br><span class="muted"${s.source === "learned" ? ` title="${ENGINE_TIP}"` : ""}>${s.source === "learned" ? "engine from" : "based on"} ${s.based_on_in_library
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
  $app.innerHTML = `${back("#/styles", "My styles")}${head(esc(slug), esc(s.en || slug), `<span${s.source === "learned" ? ` title="${ENGINE_TIP}"` : ""}>${s.source === "learned" ? "Engine from" : "Based on"}</span> ${s.based_on_in_library ? `<a href="#/library/${esc(s.based_on)}">${esc(s.based_on)}</a>` : esc(s.based_on || "–")} · ${s.source === "learned" ? `learned from ${ref.videos ?? "?"} videos, ${num(ref.measured_seconds, 0)} seconds measured` : "custom style"}${s.created ? ` · saved ${esc(s.created)}` : ""}`)}
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
  const [lib, mine, chs] = await Promise.all([get("/library"), get("/styles"), get("/channels").catch(() => ({ channels: [] }))]);
  const topicN = Number(params.get("topic") || 0);
  const topic = topicN && params.get("channel")
    ? (await get(`/channels/${encodeURIComponent(params.get("channel") || "")}/topics`).catch(() => ({ topics: [] }))).topics.find((/** @type {any} */ t) => t.n === topicN)
    : null;
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
      ${chs.channels.length ? `<label>Channel <span class="hint">One of <a href="#/channels">your channels</a>: its style, length, language, rules and lessons are used.</span>
        <select id="f-channel"><option value="">No channel</option>${chs.channels.map((/** @type {any} */ c) =>
          `<option value="${esc(c.slug)}" ${params.get("channel") === c.slug ? "selected" : ""}>${esc(c.name)} (${esc(c.language)})</option>`).join("")}</select></label>` : ""}
      <label>Style <span class="hint">Pick the look of the film. <a href="#/library">See the whole library</a>.</span></label>
      <div class="pick" role="radiogroup" aria-label="Style">${cards}</div>
      <label>Your idea <span class="hint">What happens in the film, who is in it, the mood. Up to 2000 characters.</span>
        <textarea id="idea" minlength="3" maxlength="2000" required placeholder="A late-night bánh mì stall in Saigon, told by the old man who runs it.">${topic ? esc(topic.text) : ""}</textarea></label>
      ${topic ? `<p class="muted">From topic #${topic.n} (${esc(topic.verdict)} ${topic.total}/50).</p>` : ""}
      <label>Length in seconds <span class="hint">Up to ${max} seconds.</span>
        <input id="seconds" type="number" min="5" max="${max}" value="${Math.min(30, max)}" required></label>
      <label class="check"><input id="treat" type="checkbox"> <span>Let me review the treatment (the written plan) before the picture is made</span></label>
      ${pointBoxes("f-reviews", ["script", "shots"])}
      <div><button class="primary" type="submit" ${left === 0 || !ME.verified ? "disabled" : ""}>Make the film (uses 1 credit)</button></div>
    </form><p id="msg" class="muted" role="status"></p>`;
  $app.querySelector("input[name=style]:checked")?.closest("label")?.scrollIntoView({ block: "nearest" });
  const chSel = /** @type {HTMLSelectElement | null} */ (document.getElementById("f-channel"));
  const fillFromChannel = () => {             // the channel's profile fills the form; the customer may still change it
    const c = chs.channels.find((/** @type {any} */ x) => x.slug === chSel?.value);
    if (!c) return;
    const r = /** @type {HTMLInputElement | null} */ ($app.querySelector(`input[name=style][value="${CSS.escape(c.style)}"]`));
    if (r) { r.checked = true; r.closest("label")?.scrollIntoView({ block: "nearest" }); }
    field("seconds").value = String(Math.min(c.seconds, max));
    const on = c.reviews || ["script", "shots"];        // the channel's review points, changeable for this film
    document.querySelectorAll("#f-reviews input").forEach((x) => { /** @type {HTMLInputElement} */ (x).checked = on.includes(/** @type {HTMLInputElement} */ (x).value); });
  };
  if (chSel) { chSel.onchange = fillFromChannel; if (chSel.value) fillFromChannel(); }
  onSubmit(async () => {
    const style = /** @type {HTMLInputElement | null} */ ($app.querySelector("input[name=style]:checked"));
    if (!style) throw new Error("Pick a style first.");
    const j = await post("/jobs", { kind: "film", style: style.value, idea: field("idea").value.trim(),
      seconds: Number(field("seconds").value), review_treatment: field("treat").checked, reviews: pointsOf("f-reviews"),
      ...(chSel && chSel.value ? { channel: chSel.value } : {}),
      ...(topic && chSel && chSel.value === params.get("channel") ? { topic: topic.n } : {}) });
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
  ["youtube_daily_units", "YouTube units a day (YouTube gives 10000)", "int"], ["topics_per_day", "Topics per member a day", "int"],
  ["quota_films_default", "Films per month (default)", "int"],
  ["quota_learns_default", "Learns per month (default)", "int"], ["film_max_seconds", "Longest film (seconds)", "int"],
  ["learn_max_videos", "Videos per learn", "int"], ["upload_max_mb", "Upload size (MB)", "int"],
  ["upload_max_minutes", "Upload length (minutes)", "int"], ["job_token_cap", "Token limit per job", "int"],
  ["concurrency", "Jobs at the same time", "int"],
  ["review_timeout_days", "Stop a job after waiting (days)", "int"], ["model", "Claude model (every Claude call of the studio)", "model"],
];
const SETTINGS_TABS = [["general", "General"], ["users", "Users"], ["usage", "Usage"], ["worker", "Worker"], ["tokens", "API tokens"], ["lessons", "Shared lessons"]];
const ROLE = { admin: "Owner", customer: "Member" };
const usd = (v) => `$${Number(v || 0).toFixed(2)}`;
async function pageSettings(tab = "general") {
  if (ME.role !== "admin") { $app.innerHTML = `<p class="error">This page is for the studio owner.</p>`; return; }
  if (!SETTINGS_TABS.some(([k]) => k === tab)) tab = "general";
  const top = `${head("Owner", "Settings", 'How the studio is run. The AI plans themselves are on the <a href="#/admin/claude">AI accounts</a> page.')}
    <div class="tabs" role="tablist">${SETTINGS_TABS.map(([k, label]) =>
      `<a role="tab" href="#/settings/${k}" class="${k === tab ? "on" : ""}" aria-selected="${k === tab}">${label}</a>`).join("")}</div>`;
  if (tab === "users") return settingsUsers(top);
  if (tab === "worker") return settingsWorker(top);
  if (tab === "tokens") {
    $app.innerHTML = `${top}<div id="tokens"></div>`;
    return tokensSection(document.getElementById("tokens"), "admin");
  }
  if (tab === "usage") return settingsUsage(top);
  if (tab === "lessons") return settingsLessons(top);
  const st = await get("/admin/settings");
  // specs/024: the model list comes from the server (tools/models.json), never typed
  const pick = (/** @type {string} */ k, /** @type {string} */ label, /** @type {string[][]} */ choices) =>
    `<label>${label}<select id="s-${k}">${choices.map(([v, l]) => `<option value="${esc(v)}"${st[k] === v ? " selected" : ""}>${esc(l)}</option>`).join("")}</select></label>`;
  const input = ([k, label, t, choices]) => t === "model" ? pick(k, label, (st.models || []).map((m) => [m.id, m.name]))
    : t === "choice" ? pick(k, label, choices)
    : `<label>${label}<input id="s-${k}" type="${t === "text" ? "text" : "number"}" ${t === "num" ? 'step="0.01"' : ""} value="${esc(st[k])}"></label>`;
  const ytKey = `<section class="panel card-pad" id="yt-key"><h2>YouTube key</h2>
    <p class="muted">For scoring topics with YouTube numbers (specs/013). The key is kept on the server and never shown again.
      ${st.youtube_key_set ? `<strong>Key set (…${esc(st.youtube_key_last4)})</strong>` : "<strong>No key yet.</strong>"}
      Units used today: ${st.youtube_units_today ?? 0} of ${st.youtube_daily_units}.</p>
    <div class="row"><input id="yt-key-input" type="password" autocomplete="off" placeholder="Paste a YouTube Data API key"><button id="yt-key-save">Save key</button>
      ${st.youtube_key_set ? `<button class="danger" id="yt-key-del">Remove</button>` : ""}</div><p id="yt-msg" class="muted" role="status"></p></section>`;
  $app.innerHTML = `${top}${ytKey}<section class="panel card-pad"><h2>Studio</h2><p class="muted">Limits for every member, and how many films run at once.</p>
    <form class="form" id="settings"><div class="admin-grid">${SETTING.map(input).join("")}</div>
      <div><button class="primary" type="submit">Save settings</button></div></form><p id="msg" class="muted" role="status"></p></section>`;
  /** @type {HTMLButtonElement} */ (document.getElementById("yt-key-save")).onclick = async () => {
    const msg = document.getElementById("yt-msg");
    try { await send("PUT", "/admin/youtube-key", { key: field("yt-key-input").value.trim() }); pageSettings("general"); }
    catch (e) { msg.className = "fail"; msg.textContent = e.message; }
  };
  const ytDel = document.getElementById("yt-key-del");
  if (ytDel) ytDel.onclick = async () => { if (confirm("Remove the YouTube key?")) { await send("DELETE", "/admin/youtube-key"); pageSettings("general"); } };
  onSubmit(async () => {
    const data = {};
    for (const [k, , t] of SETTING) {
      const el = field(`s-${k}`);
      data[k] = t === "text" || t === "choice" || t === "model" ? el.value.trim() : Number(el.value);
    }
    await send("PUT", "/admin/settings", data);
    return "Saved.";
  });
}

// ---------- Settings → Worker (specs/009 FR-201-FR-206; layout from neb-creative-tool) ----------
let workerTimer = 0;
const secondsAgo = (n) => (n < 60 ? `${n} s` : n < 3600 ? `${Math.round(n / 60)} min` : `${Math.round(n / 3600)} h`);
async function settingsWorker(top) {
  clearTimeout(workerTimer);
  const w = await get("/admin/worker");
  const live = w.workers.filter((x) => x.state === "running");
  const waiting = w.counts.queued + w.counts.waiting_claude + w.counts.waiting_review > 0;
  const head = live.length
    ? pill(`Running · ${live.some((x) => x.busy_with.length) ? "busy" : "idle"}`, "ok", live.some((x) => x.busy_with.length) ? "pulse" : "")
    : w.workers.length ? pill("Not responding", "bad") : pill("Not running", waiting ? "bad" : "warn");
  const rows = w.workers.map((x) => `<li class="beat"><span class="dot ${x.state === "running" ? "on" : "off"}"></span>
      <strong>${esc(x.id)}</strong> <span class="muted">${x.state === "running"
        ? (x.busy_with.length ? `working on ${x.busy_with.map((id) => `<a href="#/jobs/${esc(id)}">${esc(id)}</a>`).join(", ")}` : "idle")
        : "not responding"}</span><span class="muted beat-ago">last beat ${secondsAgo(x.beat_ago_s)} ago</span></li>`).join("");
  const count = (n, label) => `<div class="stat panel"><b>${n}</b><span class="muted">${label}</span></div>`;
  const job = (j) => {
    const long = j.error && j.error.length > 140;
    return `<li><div class="latest-head">${badge(j.status)} <span class="muted">${esc(KIND[j.kind] || j.kind)}</span>
        <a href="#/jobs/${esc(j.id)}"><strong>${esc(j.name)}</strong></a> <span class="muted small">${esc(j.email || "")}</span>
        <span class="muted small latest-time">${j.updated_at ? `${ago(j.updated_at)} ago` : ""}</span></div>
      ${j.error ? `<p class="fail small clamp">${esc(j.error)}</p>${long ? `<details class="small"><summary class="muted">Details</summary><p class="small">${esc(j.error)}</p></details>` : ""}` : ""}</li>`;
  };
  $app.innerHTML = `${top}
    <section class="panel card-pad"><div class="provider-head" style="padding:0"><div><h2>Status</h2>
      <p class="muted">Read every 5 seconds. Starting and stopping the worker stays in the terminal.</p></div>${head}</div>
      ${rows ? `<ul class="beats">${rows}</ul>` : `<p class="notice${waiting ? " warn" : ""}">No worker is running. Start it in a terminal: <code>sh bin/studio online up</code> on the server, or <code>tools/.venv/bin/python tools/runner/worker.py</code> on this machine.</p>`}
      ${w.render ? `<p class="small" data-render="${esc(w.render.mode)}">Rendering: ${w.render.mode === "gpu"
        ? `<strong>GPU</strong> · ${esc(w.render.renderer || "")}`
        : `software · <span class="muted">${esc(w.render.reason || "")}</span>`}</p>` : ""}
      <div class="stats">${count(w.counts.queued, "jobs queued")}${count(w.counts.running, "jobs running")}${count(w.counts.waiting_review, "waiting for review")}${count(w.counts.waiting_claude, "waiting for a Claude account")}</div></section>
    <section class="panel card-pad"><h2>Latest jobs</h2>${w.latest.length ? `<ul class="latest">${w.latest.map(job).join("")}</ul>` : '<p class="muted">No jobs yet.</p>'}</section>`;
  workerTimer = setTimeout(() => { if (/^#\/settings\/worker/.test(location.hash)) route(); }, 5000);
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
  const several = list.length > 1, manual = c.order === "manual";
  const canAdd = list[0].state !== "signed_out" && list.length < MAX_CLAUDE && !login;
  const row = (a) => {
    const name = a.email || claudeLabel(a.slot);
    const title = several && a.email ? `${claudeLabel(a.slot)} · ${a.email}` : name;
    const waiting = login && login.slot === a.slot;
    const signedIn = a.state === "signed_in" || a.state === "limited";
    const first = manual && several && a === list[0];
    const badges = (first ? pill("Used first", "accent") : "") + (signedIn
      ? `${pill("Signed in", "ok")}${a.plan ? pill(a.plan) : ""}${rested(a) ? pill("Limit reached", "bad") : ""}`
      : waiting ? pill("Signing in", "accent", "pulse") : a.state === "needs_signin" ? pill("Needs sign-in", "bad") : pill("Not signed in"));
    const meta = rested(a) ? `Back ${resetLabel(a.rest_until)}. Calls use the other accounts until then.`
      : a.state === "needs_signin" ? "Its sign-in stopped working: sign in again." : !signedIn && !waiting && a.slot === 1 && !several
        ? (c.api_key ? "The API key is used until you sign in." : "Jobs cannot run until you sign in.") : "";
    const menu = [several && !(manual && a === list[0]) && '<button data-act="top">Move to top</button>',
      signedIn && '<button data-act="login">Sign in again</button>', a.state !== "signed_out" && '<button data-act="logout" class="danger">Sign out</button>',
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
    ${c.waiting ? `<p class="notice warn">${c.waiting} job${c.waiting === 1 ? " is" : "s are"} waiting for a Claude account. They start as soon as one is signed in.</p>` : ""}
    <section class="provider panel" id="claude-plan">
      <div class="provider-head"><div><div class="acc-name"><h2>Claude · plan</h2>${live.length ? pill(live.length > 1 ? `${live.length} signed in` : "Signed in", "ok") : pill("Not signed in")}</div>
        <p class="muted">Films, styles and the content check run on your Claude Pro or Max plan. When an account reaches its limit, calls move to the next signed-in account.</p></div>
        <button id="refresh">Check again</button></div>
      <p id="msg" class="muted" role="status"></p>
      <ul class="acc-rows">${list.map(row).join("")}</ul>
      <div class="provider-foot">
        ${canAdd ? '<div class="foot-row"><button id="add">Add account</button><span class="muted">Sign in with a different Claude account: calls then rotate over them.</span></div>' : ""}
        ${several ? `<div class="foot-row"><span class="muted">Order</span><div class="seg" role="radiogroup" aria-label="Order">
          <button data-order="auto" role="radio" aria-checked="${!manual}" class="${manual ? "" : "on"}">Auto: least used first</button>
          <button data-order="manual" role="radio" aria-checked="${manual}" class="${manual ? "on" : ""}">Manual: top to bottom</button></div></div>` : ""}
        <details class="how"><summary>How it works</summary><div>
          <p>The sign-in is Claude Code's own, kept on this server in the data folder (claude/). It never goes into a job's sandbox: jobs reach Claude only through the studio.</p>
          <p>Calls count against the plan's limits, shared with Claude Code and claude.ai on the same account.</p>
          <p>Several accounts, Auto: each call goes to the one the studio used least in the last 5 hours. Manual: each call goes to the account at the top, and to the next one only while it is at its limit or needs signing in. Move to top in an account's ⋯ menu.</p>
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
    if (b.dataset.act === "top") act(() => post(`/admin/claude/accounts/${slot}/top`));
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
  (/** @type {NodeListOf<HTMLButtonElement>} */ ($app.querySelectorAll(".seg button[data-order]"))).forEach((b) => b.addEventListener("click", () => {
    if (!b.classList.contains("on")) act(() => send("PUT", "/admin/claude/order", { mode: b.dataset.order }));
  }));
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
    <h2>API tokens</h2><div id="tokens"></div>
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
  tokensSection(document.getElementById("tokens"), "me");
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

// ---------- API tokens (specs/009 FR-208-FR-218; layout from neb-creative-tool's Settings → API tokens) ----------
const TOKEN_STATUS = { active: ["Active", "ok"], ended: ["Ended", "bad"], revoked: ["Revoked", ""] };
const EXPIRY = [["7d", "7 days"], ["30d", "30 days"], ["90d", "90 days"], ["1y", "1 year"], ["never", "Never"]];
/** What an agent needs; `secret` fills the token in when it is known (right after it is made). */
function agentInfo(secret) {
  const origin = location.origin, tok = secret || "<token>", mcp = `${origin}/api/mcp`;
  const cmd = `claude mcp add --transport http film-studio ${mcp} --header "Authorization: Bearer ${tok}"`;
  const json = JSON.stringify({ mcpServers: { "film-studio": { type: "http", url: mcp, headers: { Authorization: `Bearer ${tok}` } } } }, null, 2);
  const brief = [`You can use Film Studio through its API.`, `Base URL: ${origin}`,
    `Send on every request: Authorization: Bearer ${tok}`,
    `API reference (OpenAPI): ${origin}/api/v1/openapi.json · readable docs: ${origin}/api/v1/docs`,
    `MCP server: ${mcp} (Claude Code: ${cmd})`,
    `Ask the user before anything that uses a film or learn credit.`,
    `When you make a job, send an Idempotency-Key header (any unique text) and send the same one if you retry.`,
    `Films take minutes: check the job again (GET /api/v1/jobs/<id>) instead of waiting on one request.`,
    `To upload a video, ask for a link with POST /api/v1/uploads/tickets, then PUT the file to it.`].join("\n");
  return { origin, mcp, cmd, json, brief };
}
async function copyText(btn, text) {
  try { await navigator.clipboard.writeText(text); } catch { prompt("Copy this:", text); return; }
  const was = btn.textContent; btn.textContent = "Copied"; setTimeout(() => { btn.textContent = was; }, 1500);
}
function forAgentsBox() {
  const i = agentInfo("");
  const row = (label, value, copy) => `<div class="kv"><span class="muted">${label}</span><code>${esc(value)}</code>${copy ? `<button type="button" data-copy="${esc(value)}">Copy</button>` : ""}</div>`;
  return `<details class="panel card-pad for-agents"><summary><strong>For agents</strong> <span class="muted">· what a script or an AI agent needs</span></summary>
    ${row("Base URL", i.origin, true)}${row("Header", "Authorization: Bearer <token>", false)}
    ${row("API reference", `${i.origin}/api/v1/openapi.json`, true)}${row("Readable docs", `${i.origin}/api/v1/docs`, true)}${row("MCP server", i.mcp, true)}
    <p class="small muted">Claude Code</p><pre class="code">${esc(i.cmd)}</pre><button type="button" data-copy="${esc(i.cmd)}">Copy</button>
    <p class="small muted">Other MCP clients (JSON)</p><pre class="code">${esc(i.json)}</pre><button type="button" data-copy="${esc(i.json)}">Copy</button>
    <p class="small muted">A token acts as you, never with more than your role. It cannot make or see tokens, manage users, touch Claude accounts, or change your password or account. An agent on another computer needs the studio's real address over HTTPS.</p></details>`;
}
/** The token list of one person ("me") or of everyone ("admin", Settings → API tokens). */
async function tokensSection(el, scope) {
  const base = scope === "me" ? "/me/tokens" : "/admin/tokens";
  const { tokens } = await get(base);
  const row = (t) => {
    const [label, tone] = TOKEN_STATUS[t.status] || [t.status, ""];
    return `<li data-id="${esc(t.id)}"><div class="tok-head">
        <div class="tok-name"><strong>${esc(t.name)}</strong> <code class="muted">${esc(t.prefix)}…</code>
          ${scope === "admin" ? `<span class="muted small">${esc(t.owner.email || "(deleted)")}</span>` : ""}</div>
        <div class="tok-badges">${pill(t.role === "admin" ? "Owner" : "Member", t.role === "admin" ? "accent" : "")}${t.can_spend ? pill("Can use credits", "warn") : ""}${pill(label, tone)}</div>
        <details class="menu"><summary aria-label="Actions for ${esc(t.name)}">⋯</summary><div class="menu-list">
          <button data-act="log">Log</button>${t.status === "active" ? '<button data-act="revoke" class="danger">Revoke</button>' : ""}</div></details></div>
      <p class="muted small">${t.requests_today} request${t.requests_today === 1 ? "" : "s"} today${t.blocked_today ? ` · <span class="fail">${t.blocked_today} blocked</span>` : ""} · ${t.rate_per_min}/min ·
        ${t.last_used_at ? `used ${ago(t.last_used_at)} ago` : "never used"} · ${t.revoked_at ? "revoked" : t.expires_at ? `ends ${when(t.expires_at)}` : '<span class="fail">never ends</span>'}</p>
      <div class="tok-log"></div></li>`;
  };
  const owner = ME && ME.role === "admin";
  el.innerHTML = `${scope === "me" ? `<p class="muted">For your own scripts and AI agents (Claude Code and others). A token acts as you.</p>
      <p><button class="primary" id="tok-new">New token</button></p>
      <form id="tok-form" class="form panel" hidden>
        <label>Name <input id="tok-name" maxlength="60" placeholder="Claude Code on my laptop" required></label>
        <div class="admin-grid">
          ${owner ? '<label>Role <select id="tok-role"><option value="customer">Member</option><option value="admin">Owner</option></select></label>' : ""}
          <label>Requests per minute <select id="tok-rate">${[10, 30, 60, 120, 300].map((n) => `<option ${n === 60 ? "selected" : ""}>${n}</option>`).join("")}</select></label>
          <label>Ends <select id="tok-exp">${EXPIRY.map(([v, l]) => `<option value="${v}" ${v === "90d" ? "selected" : ""}>${l}</option>`).join("")}</select></label></div>
        <label class="check"><input id="tok-spend" type="checkbox"> <span>Can use my film and learn credits (make films, learn styles)</span></label>
        <p id="tok-never" class="notice warn small" hidden>A token that never ends stays valid until you revoke it.</p>
        <div><button class="primary" type="submit">Create</button> <button type="button" id="tok-cancel">Cancel</button></div></form>
      <div id="tok-secret"></div>` : `<p class="muted">Every person's tokens. People make their own on their account page; you can revoke any.</p>`}
    <p id="tok-msg" class="muted" role="status"></p>
    ${tokens.length ? `<ul class="tokens panel">${tokens.map(row).join("")}</ul>` : '<p class="panel muted card-pad">No tokens yet.</p>'}
    ${forAgentsBox()}`;
  const msg = /** @type {HTMLElement} */ (el.querySelector("#tok-msg"));
  el.querySelectorAll("button[data-copy]").forEach((b) => b.addEventListener("click", () => copyText(/** @type {HTMLButtonElement} */ (b), /** @type {HTMLElement} */ (b).dataset.copy)));
  el.querySelectorAll(".tokens button[data-act]").forEach((b) => b.addEventListener("click", async () => {
    const li = /** @type {HTMLElement} */ (b.closest("li")), id = encodeURIComponent(li.dataset.id);
    b.closest("details")?.removeAttribute("open");
    if (/** @type {HTMLElement} */ (b).dataset.act === "revoke") {
      if (!confirm("Revoke this token? Anything using it stops working at once.")) return;
      try { await send("DELETE", `${base}/${id}`); await tokensSection(el, scope); } catch (e) { msg.className = "fail"; msg.textContent = e.message; }
      return;
    }
    const box = /** @type {HTMLElement} */ (li.querySelector(".tok-log"));
    if (box.innerHTML) { box.innerHTML = ""; return; }
    const { requests } = await get(`${base}/${id}/log?limit=200`);
    box.innerHTML = requests.length ? `<div class="table-wrap"><table><tr><th>When</th><th>Request</th><th>Result</th><th>IP</th></tr>${requests.map((r) =>
      `<tr><td>${when(r.at)}</td><td><code>${esc(r.method)} ${esc(r.path)}</code></td><td class="${r.outcome === "allowed" || r.outcome === "replay" ? "" : "fail"}">${esc(r.outcome)}</td><td class="muted">${esc(r.ip || "")}</td></tr>`).join("")}</table></div>`
      : '<p class="muted small">No requests yet.</p>';
  }));
  if (scope !== "me") return;
  const form = /** @type {HTMLFormElement} */ (el.querySelector("#tok-form")), newBtn = /** @type {HTMLButtonElement} */ (el.querySelector("#tok-new"));
  newBtn.addEventListener("click", () => { form.hidden = false; newBtn.hidden = true; field("tok-name").focus(); });
  el.querySelector("#tok-cancel").addEventListener("click", () => { form.hidden = true; newBtn.hidden = false; });
  const exp = /** @type {HTMLSelectElement} */ (el.querySelector("#tok-exp"));
  exp.addEventListener("change", () => { /** @type {HTMLElement} */ (el.querySelector("#tok-never")).hidden = exp.value !== "never"; });
  form.onsubmit = async (e) => {
    e.preventDefault();
    const role = /** @type {HTMLSelectElement | null} */ (el.querySelector("#tok-role"));
    try {
      const r = await post("/me/tokens", { name: field("tok-name").value.trim(), role: role ? role.value : "customer",
        can_spend: field("tok-spend").checked, rate_per_min: Number(/** @type {HTMLSelectElement} */ (el.querySelector("#tok-rate")).value), expires: exp.value });
      await tokensSection(el, scope);
      const i = agentInfo(r.secret);
      el.querySelector("#tok-secret").innerHTML = `<div class="notice secret-box"><p><strong>Copy it now: it is shown only this once.</strong></p>
        <pre class="code" id="tok-value">${esc(r.secret)}</pre>
        <p><button type="button" class="primary" data-copy="${esc(r.secret)}">Copy token</button>
          <button type="button" data-copy="${esc(i.cmd)}">Copy MCP command</button>
          <button type="button" data-copy="${esc(i.brief)}">Copy for an agent</button></p></div>`;
      el.querySelectorAll("#tok-secret button[data-copy]").forEach((b) => b.addEventListener("click", () => copyText(/** @type {HTMLButtonElement} */ (b), /** @type {HTMLElement} */ (b).dataset.copy)));
    } catch (err) { msg.className = "fail"; msg.textContent = err.message; }
  };
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
  [/^#\/new(\?.*)?$/, pageNew, "new"], [/^#\/learn$/, pageLearn, "learn"], [/^#\/(?:admin|settings)(?:\/(general|users|usage|worker|tokens|lessons))?(\?.*)?$/, pageSettings, "settings"], [/^#\/admin\/claude$/, pageClaude, "ai"],
  [/^#\/account$/, pageAccount, "account"],
  [/^#\/channels$/, pageChannels, "channels"], [/^#\/channels\/([^/?]+)$/, pageChannel, "channels"],
];
/** pages open without logging in (online mode) */
const PUBLIC = [
  [/^#\/login$/, pageLogin], [/^#\/setup$/, pageSetup], [/^#\/forgot$/, pageForgot],
  [/^#\/verify\/([^/?]+)$/, pageVerify], [/^#\/reset\/([^/?]+)$/, pageReset],
];
let rendering = null;
async function route() {
  const h = location.hash || "#/";
  $app.classList.remove("wide-film");
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
    const jobPage = h.match(/^#\/jobs\/([^/]+)$/);
    if (!editing && jobPage && document.getElementById("done-slot")) refreshJob(decodeURIComponent(jobPage[1]));   // specs/025
    else if (!editing && !/^#\/(films\/|sets|styles|library)/.test(h)) route();   // the Films list follows jobs live
  }, 300);
}
function connect() {
  const es = new EventSource(API + "/events");
  const live = () => document.getElementById("live") || document.createElement("small");      // redrawn with the account menu
  es.onopen = () => { live().classList.add("on"); live().textContent = "● Live updates on"; };
  es.onerror = () => { live().classList.remove("on"); live().textContent = "Disconnected, reconnecting…"; };      // EventSource reconnects by itself
  ["job.updated", "review.created", "review.decided"].forEach((t) => es.addEventListener(t, onChange));
  es.addEventListener("film.updated", onFilmUpdated);       // specs/029: the open film page follows outside changes
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
