// Xưởng phim: giao diện theo dõi và duyệt (specs/003-studio-ui). JavaScript thuần, không bước build.
"use strict";
const API = "/api/v1";
const $app = document.getElementById("app");
const STATUS = {
  running: "Đang chạy", waiting_review: "Chờ duyệt", waiting_resume: "Chờ tiếp tục", done: "Xong",
  failed: "Lỗi", stopped: "Đã dừng", inactive: "Không còn hoạt động",
};
const KIND = { learn: "Học phong cách", film: "Làm phim" };
const REVIEW = { "style-1": "Duyệt lần 1: bản phong cách", "style-2": "Duyệt lần 2: khung chứng minh" };
const DECISION = { approve: "Đồng ý", revise: "Yêu cầu sửa", accept_anyway: "Chấp nhận dù chưa đạt", stop: "Dừng" };
const SOURCE = { ui: "giao diện", chat: "khung chat" };

// ---------- helpers ----------
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const when = (iso) => (iso ? new Date(iso).toLocaleString("vi-VN") : "");
const num = (v, d = 3) => (v === null || v === undefined ? "–"
  : typeof v === "number" ? v.toLocaleString("vi-VN", { maximumFractionDigits: d }) : esc(v));
const METRIC = {
  luma_p50: "Độ sáng (trung vị, 0–1)", luma_p2: "Độ sáng vùng tối nhất", luma_p98: "Độ sáng vùng sáng nhất",
  contrast_p50: "Tương phản", sat_p50: "Độ bão hoà màu", dark_p50: "Tỷ lệ điểm ảnh rất tối", bright_p50: "Tỷ lệ điểm ảnh rất sáng",
  still_ratio: "Tỷ lệ khung camera đứng yên", motion720_p50: "Camera di chuyển (px/khung, trung vị)",
  motion720_p90: "Camera di chuyển nhanh (px/khung)", shot_len_median: "Độ dài cảnh (giây, trung vị)",
  shot_len_mean: "Độ dài cảnh (giây, trung bình)", cuts_per_min: "Số lần cắt cảnh mỗi phút",
  flashes_per_min: "Số chớp sáng mỗi phút", lufs: "Âm lượng (LUFS)", lra: "Độ dao động âm lượng (LU)",
  silence_per_min: "Khoảng lặng (giây mỗi phút)", first_voice_t: "Thời điểm có tiếng đầu tiên (giây)",
  speech_rate: "Tốc độ đọc (từ/giây)",
};
const head = (eyebrow, title, lead) => `<p class="eyebrow">${eyebrow}</p><h1>${title}</h1>${lead ? `<p class="lead">${lead}</p>` : ""}`;
const back = (href, text) => `<a class="back" href="${href}">← ${text}</a>`;
const SPARK = '<svg viewBox="0 0 24 24"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/></svg>';
const PROMPTS = [
  ["Học phong cách một kênh", "Học phong cách của kênh https://www.youtube.com/@ten-kenh, 5 video gần nhất."],
  ["Học từ video có sẵn", "Học phong cách từ các video trong references/bo-mau/videos, đặt tên bộ là bo-mau."],
  ["Phim theo phong cách đã học", "Làm phim 30 giây theo phong cách Quiet Night về một quán bánh mì đêm."],
  ["Phim theo phong cách thư viện", "Làm phim 40 giây phong cách màu nước về quán cà phê của gia đình tôi."],
];
const badge = (s) => `<span class="badge s-${esc(s)}">${esc(STATUS[s] || s)}</span>`;
async function get(path) {
  const r = await fetch(API + path);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body?.error?.message || `Lỗi ${r.status}`);
  return body;
}
async function post(path, data) {
  const r = await fetch(API + path, { method: "POST", headers: { "Content-Type": "application/json", "X-Studio": "1" }, body: JSON.stringify(data) });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(body?.error?.message || `Lỗi ${r.status}`); e.code = body?.error?.code; throw e; }
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
  $app.innerHTML = `${head("Theo dõi", "Việc", "Mọi việc Claude đang làm cho bạn: học phong cách và làm phim. Việc chờ duyệt được tô tím.")}
    <div class="row filters">
      <label>Trạng thái <select id="f-status"><option value="">Tất cả</option>${opt(STATUS, st)}</select></label>
      <label>Loại <select id="f-kind"><option value="">Tất cả</option>${opt(KIND, kd)}</select></label>
    </div>
    ${jobs.length ? `<ul class="jobs">${items}</ul>` : `<p class="panel muted">Không có việc nào khớp bộ lọc.</p>`}`;
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
      <h1>Hôm nay làm gì?</h1>
      <p class="muted">Mở Claude Code trong thư mục dự án và nói điều bạn muốn. Việc sẽ hiện ở đây, kèm các bước cần bạn duyệt.</p></div>
    <div class="prompts">${PROMPTS.map(([t, x]) => `<div class="panel prompt" tabindex="0" data-text="${esc(x)}">
      <strong>${esc(t)}</strong><p>${esc(x)}</p></div>`).join("")}</div>
    <p class="muted" style="text-align:center;margin-top:16px">Bấm một thẻ để chép câu lệnh mẫu.</p>`;
  $app.querySelectorAll(".prompt").forEach((el) => {
    const copy = async () => {
      try { await navigator.clipboard.writeText(el.dataset.text); } catch { return; }
      el.querySelector(".copied")?.remove();
      el.insertAdjacentHTML("beforeend", '<p class="copied">✓ Đã chép, dán vào Claude Code</p>');
    };
    el.onclick = copy; el.onkeydown = (e) => { if (e.key === "Enter") copy(); };
  });
}

async function pageJob(id) {
  const j = await get(`/jobs/${encodeURIComponent(id)}`);
  const pct = j.progress ? Math.round((100 * j.progress.done) / j.progress.total) : null;
  const links = [
    j.links.set && `<a href="#/sets/${esc(j.links.set)}">Hồ sơ đo: ${esc(j.links.set)}</a>`,
    j.links.film && `<a href="#/films/${esc(j.links.film)}">Phim: ${esc(j.links.film)}</a>`,
    j.links.style && `<a href="#/styles/${esc(j.links.style)}">Phong cách: ${esc(j.links.style)}</a>`,
  ].filter(Boolean).join(" · ");
  const revs = j.reviews.map((r) => `<li class="panel"><a href="#/reviews/${esc(r.id)}">${esc(REVIEW[r.kind])}</a>
      ${r.decision ? `<span class="muted">${esc(DECISION[r.decision.value])} · qua ${esc(SOURCE[r.decision.source])}</span>` : `<span class="badge s-waiting_review">Chờ bạn duyệt</span>`}</li>`).join("");
  $app.innerHTML = `${back("#/", "Việc")}
    ${head(esc(KIND[j.kind] || j.kind), `${esc(j.name)} ${badge(j.status)}`, "")}
    <div class="split"><div>
    ${j.status === "waiting_review" && j.reviews.some((r) => !r.decision) ? `<p class="notice">Việc đang chờ bạn duyệt: <a href="#/reviews/${esc(j.reviews.find((r) => !r.decision).id)}">mở trang duyệt</a>.</p>` : ""}
    ${j.status === "waiting_resume" ? `<p class="notice">Đã có quyết định nhưng phiên Claude không còn chờ. Mở lại Claude Code và nói “tiếp tục việc ${esc(j.name)}”.</p>` : ""}
    ${j.status === "inactive" ? `<p class="notice">Không có cập nhật hơn 10 phút: có thể phiên Claude đã đóng hoặc bị dừng.</p>` : ""}
    ${j.error ? `<p class="error">${esc(j.error)}</p>` : ""}
    <div class="panel"><p class="section-title">Bước hiện tại</p><p style="font-size:16px;font-weight:600">${esc(j.step)}</p>
      ${pct !== null ? `<div class="bar"><i style="width:${pct}%"></i></div>` : ""}</div>
    ${revs ? `<h2>Duyệt</h2><ul class="reviews">${revs}</ul>` : ""}
    <h2>Nhật ký</h2><pre class="log">${j.log.map((l) => `${new Date(l.t).toLocaleTimeString("vi-VN")}  ${esc(l.line)}`).join("\n") || "Chưa có dòng nào."}</pre>
    </div><aside class="aside panel"><p class="section-title">Tóm tắt</p><dl class="kv">
      <dt>Loại</dt><dd>${esc(KIND[j.kind] || j.kind)}</dd>
      <dt>Trạng thái</dt><dd>${esc(STATUS[j.status] || j.status)}</dd>
      <dt>Tiến độ</dt><dd>${pct !== null ? `${j.progress.done}/${j.progress.total}` : "—"}</dd>
      <dt>Bắt đầu</dt><dd>${when(j.started_at)}</dd>
      <dt>Cập nhật</dt><dd>${when(j.updated_at)}</dd></dl>
      ${links ? `<p class="section-title" style="margin-top:18px">Kết quả</p><p style="display:grid;gap:4px;margin:0">${links.replaceAll(" · ", "")}</p>` : ""}
    </aside></div>`;
}

function metricRows(c) {
  const rows = [
    ["Lệch độ sáng", c.luma_diff, "≤ 0,05", c.luma_diff <= 0.05],
    ["Lệch bão hoà", c.sat_median_diff, "≤ 0,08", c.sat_median_diff <= 0.08],
    ["Lệch vùng rất tối (điểm %)", c.dark_diff_pp, "≤ 5", c.dark_diff_pp <= 5],
    ["Màu khớp", c.palette_matched, `≥ ${c.palette_needed}`, c.palette_matched >= c.palette_needed],
  ];
  return rows.map(([n, v, lim, ok]) => `<tr><td>${n}</td><td class="num">${num(v)}</td><td>${lim}</td>
    <td class="${ok ? "pass" : "fail"}">${ok ? "✓ đạt" : "✗ chưa"}</td></tr>`).join("");
}

async function pageReview(id) {
  const r = await get(`/reviews/${encodeURIComponent(id)}`);
  const c = r.compare;
  const file = (p) => (p || "").split("/").pop();
  const proof = c ? `<div class="pair">
      <figure><img data-zoom src="${API}/sets/${esc(r.set)}/proof/${esc(file(c.ref))}" alt="Khung gốc"><figcaption>Khung gốc (bấm để phóng to)</figcaption></figure>
      <figure><img data-zoom src="${API}/sets/${esc(r.set)}/proof/${esc(file(c.ours))}" alt="Khung tự vẽ"><figcaption>Khung tự vẽ · vòng ${num(c.round, 0)}</figcaption></figure></div>
      <h2>Bốn chỉ số</h2><table><tr><th>Chỉ số</th><th>Giá trị</th><th>Ngưỡng</th><th></th></tr>${metricRows(c)}</table>
      <p>${c.pass ? '<span class="pass">Đạt cả 4 chỉ số.</span>' : '<span class="fail">Chưa đạt đủ 4 chỉ số.</span>'}
      ${r.final_round ? " Đã dùng hết vòng sửa." : ""}</p>` : "";
  const d = r.decision;
  const extra = r.final_round ? `<button data-v="accept_anyway">Chấp nhận dù chưa đạt</button><button class="danger" data-v="stop">Dừng</button>` : "";
  $app.innerHTML = `${back(`#/jobs/${esc(r.job_id)}`, "Việc")}
    ${head("Duyệt", esc(REVIEW[r.kind]), `Bộ tham chiếu <a href="#/sets/${esc(r.set)}">${esc(r.set)}</a> · gửi lúc ${when(r.created_at)}`)}
    ${proof}
    <h2>${c ? "Ghi chú của Claude" : "Tóm tắt"}</h2><div class="panel md">${r.summary_html}</div>
    <div class="panel decide" id="decide">${d ? decidedHtml(d) : `
      <p><strong>Quyết định của bạn</strong> <span class="muted">· việc tự chạy tiếp, không cần gõ trong khung chat</span></p>
      <textarea id="note" placeholder="Góp ý (bắt buộc khi yêu cầu sửa)"></textarea>
      <div class="row" style="margin-top:8px"><button class="primary" data-v="approve">Đồng ý</button><button data-v="revise">Yêu cầu sửa</button>${extra}</div>
      <p id="msg" class="muted"></p>`}</div>`;
  zoomable($app);
  $app.querySelectorAll("#decide button[data-v]").forEach((b) => b.addEventListener("click", async () => {
    const v = b.dataset.v, note = document.getElementById("note").value.trim(), msg = document.getElementById("msg");
    if (v === "revise" && note.length < 3) { msg.textContent = "Hãy ghi góp ý (ít nhất 3 ký tự) trước khi yêu cầu sửa."; msg.className = "fail"; return; }
    $app.querySelectorAll("#decide button").forEach((x) => (x.disabled = true));
    try {
      const res = await post(`/reviews/${encodeURIComponent(id)}/decision`, { value: v, note });
      document.getElementById("decide").innerHTML = decidedHtml(res);
      askNotify();
    } catch (e) {
      msg.textContent = e.code === "already_decided" ? "Yêu cầu này đã được duyệt ở nơi khác." : e.message; msg.className = "fail";
      if (e.code === "already_decided") setTimeout(route, 800); else $app.querySelectorAll("#decide button").forEach((x) => (x.disabled = false));
    }
  }));
}
const decidedHtml = (d) => `<p class="done-box">Đã duyệt: <strong>${esc(DECISION[d.value])}</strong> (qua ${esc(SOURCE[d.source])}, ${when(d.at)})
  ${d.note ? `<br>Góp ý: ${esc(d.note)}` : ""}</p>`;

async function pageFilms() {
  const { films } = await get("/films");
  $app.innerHTML = `${head("Kết quả", "Phim", "Phim đã render trong thư mục films/.")}${films.length ? `<div class="grid">${films.map((f) => `<a class="panel card" href="#/films/${esc(f.name)}">
      ${f.has_poster ? `<img src="${API}/films/${esc(f.name)}/poster" alt="">` : ""}<p><strong>${esc(f.name)}</strong>
      ${f.rendering ? '<span class="badge s-running">Đang render</span>' : ""}</p></a>`).join("")}</div>`
    : `<p class="panel muted">Chưa có phim nào trong thư mục films/.</p>`}`;
}

async function pageFilm(name) {
  const f = await get(`/films/${encodeURIComponent(name)}`);
  const base = `${API}/films/${encodeURIComponent(name)}`;
  $app.innerHTML = `${back("#/films", "Phim")}${head("Phim", esc(f.name), "")}
    ${f.has_video ? `<video controls preload="metadata" ${f.has_poster ? `poster="${base}/poster"` : ""}>
        <source src="${base}/video" type="video/mp4">
        ${f.has_subtitles ? `<track kind="subtitles" srclang="vi" label="Phụ đề" src="${base}/subtitles.vtt" default>` : ""}
      </video><p class="muted">Bật tắt phụ đề bằng nút CC của trình phát.</p>`
    : `<p class="notice">${f.rendering ? "Phim đang được render: xem tiến độ ở trang Việc." : "Chưa có tệp phim."}</p>`}
    ${f.treatment_html ? `<h2>Kịch bản (TREATMENT)</h2><div class="panel md">${f.treatment_html}</div>` : ""}
    ${f.credits ? `<h2>Tài sản bên thứ ba (CREDITS)</h2><pre class="log">${esc(f.credits)}</pre>` : ""}`;
}

async function pageSets() {
  const { sets } = await get("/sets");
  $app.innerHTML = `${head("Thư viện", "Hồ sơ đo", "Số đo từng khung hình của các bộ video tham chiếu đã học.")}${sets.length ? `<ul class="jobs">${sets.map((s) => `<li><a class="panel job" href="#/sets/${esc(s.set)}">
      <strong>${esc(s.set)}</strong><span class="muted">${s.measured}/${s.videos} video đã đo</span>
      <span class="muted">${s.media_removed ? "Video tham chiếu đã xoá" : "Video tham chiếu còn trên máy"}</span></a></li>`).join("")}</ul>`
    : `<p class="panel muted">Chưa có bộ tham chiếu nào.</p>`}`;
}

async function pageSet(name) {
  const s = await get(`/sets/${encodeURIComponent(name)}`);
  const sh = await get(`/sets/${encodeURIComponent(name)}/sheets`);
  const sum = s.summary || {};
  const groups = Object.entries(sum.by_orientation || {}).map(([o, g]) => `<h2>${esc({ landscape: "Video ngang", portrait: "Video dọc", square: "Video vuông" }[o] || o)} · ${g.videos} video</h2>
    <div class="swatches">${(g.palette || []).map((c) => `<span class="swatch" title="${esc(c.hex)} ${Math.round(c.share * 100)}%" style="background:${esc(c.hex)}"></span>`).join("")}</div>
    <table><tr><th>Chỉ số</th><th>Trung vị</th><th>Thấp nhất</th><th>Cao nhất</th></tr>
    ${Object.entries(g.metrics).map(([k, m]) => `<tr><td title="${esc(k)}">${esc(METRIC[k] || k)}</td><td class="num">${num(m.median)}</td><td class="num">${num(m.min)}</td><td class="num">${num(m.max)}</td></tr>`).join("")}</table>`).join("");
  const warns = [sum.low_count_warning && "Dưới 5 video: kết luận kém tin cậy.",
    (sum.dispersion_warnings || []).length && `Phân tán lớn: ${sum.dispersion_warnings.join(", ")}.`,
    (sum.no_speech || []).length && `Không phát hiện lời nói: ${sum.no_speech.join(", ")}.`,
    (sum.audio_unverified || []).length && `Chưa xác định được tiếng gốc: ${sum.audio_unverified.join(", ")}.`].filter(Boolean);
  const vids = Object.keys(sh.sheets || {});
  $app.innerHTML = `${back("#/sets", "Hồ sơ đo")}${head("Hồ sơ đo", esc(s.set), `${sum.videos_measured ?? 0} video · ${num(sum.measured_seconds, 1)} giây đã đo`)}
    ${warns.map((w) => `<p class="notice">${esc(w)}</p>`).join("")}${groups || '<p class="muted">Chưa có bản tổng hợp.</p>'}
    <h2>Ảnh ghép mỗi 2 giây</h2>${sh.removed ? '<p class="muted">Đã xoá cùng video tham chiếu.</p>' : `
      <div class="row"><select id="sv">${vids.map((v) => `<option>${esc(v)}</option>`).join("")}</select>
      <button id="prev">←</button><span id="pos" class="muted"></span><button id="next">→</button></div>
      <p><img id="sheet" class="shot" data-zoom alt="Ảnh ghép"></p>`}`;
  if (!sh.removed) {
    let i = 0;
    const show = () => {
      const files = sh.sheets[document.getElementById("sv").value]; i = Math.max(0, Math.min(i, files.length - 1));
      document.getElementById("sheet").src = `${API}/sets/${encodeURIComponent(name)}/sheets/${files[i]}`;
      document.getElementById("pos").textContent = `${i + 1}/${files.length} · giây ${i * 2}–${i * 2 + 2}`;
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
  $app.innerHTML = `${head("Thư viện", "Phong cách riêng", "Phong cách đã học và lưu trong my-styles/, dùng để làm phim.")}${styles.length ? `<div class="grid">${styles.map((s) => `<a class="panel card" href="#/styles/${esc(s.slug)}">
      ${s.has_styleframe ? `<img src="${API}/styles/${esc(s.slug)}/styleframe" alt="">` : ""}
      <p><strong>${esc(s.en || s.slug)}</strong><br><span class="muted">dựa trên ${esc(s.based_on || "–")}${s.source === "learned" ? " · học từ video" : ""}</span></p></a>`).join("")}</div>`
    : `<p class="panel muted">Chưa có phong cách riêng. Học một phong cách bằng cách nói với Claude: “Học phong cách của kênh …”.</p>`}`;
}

async function pageStyle(slug) {
  const s = await get(`/styles/${encodeURIComponent(slug)}`);
  const ref = s.reference || {};
  $app.innerHTML = `${back("#/styles", "Phong cách")}${head(esc(slug), esc(s.en || slug), `Kỹ thuật nền ${esc(s.based_on || "–")} · ${s.source === "learned" ? `học từ ${ref.videos ?? "?"} video, ${num(ref.measured_seconds, 0)} giây đã đo` : "phong cách riêng"}${s.created ? ` · lưu ngày ${esc(s.created)}` : ""}`)}
    ${s.has_styleframe ? `<p><img class="shot" data-zoom src="${API}/styles/${esc(slug)}/styleframe" alt="Khung chứng minh"></p>` : ""}
    <h2>STYLE.md</h2><div class="panel md">${s.style_html}</div>
    ${s.evidence_html ? `<h2>Bằng chứng</h2><div class="panel md">${s.evidence_html}</div>` : ""}`;
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
    try { await p; } catch (e) { if (rendering === p) $app.innerHTML = `<p class="error">${esc(e.message)}</p>${back("#/", "Việc")}`; }
    return;
  }
  $app.innerHTML = `<p class="error">Không có trang này.</p>${back("#/", "Việc")}`;
}

let pending = new Set(), seeded = false;
async function refreshPending(announce) {
  try {
    const { reviews } = await get("/reviews?status=pending");
    const ids = new Set(reviews.map((r) => r.id));
    if (announce && seeded) reviews.filter((r) => !pending.has(r.id)).forEach(notify);
    pending = ids; seeded = true;
    document.title = (ids.size ? `(${ids.size}) chờ duyệt · ` : "") + "Xưởng phim";
    const c = document.getElementById("nav-count"); c.textContent = ids.size; c.hidden = !ids.size; c.title = `${ids.size} chờ duyệt`;
  } catch { /* server restarting */ }
}
function notify(r) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  const n = new Notification("Xưởng phim: có việc chờ duyệt", { body: REVIEW[r.kind] + " · " + r.set, tag: r.id });
  n.onclick = () => { window.focus(); location.hash = `#/reviews/${r.id}`; n.close(); };
}
function askNotify() {
  if (!("Notification" in window) || Notification.permission !== "default" || document.getElementById("ask-notify")) return;
  const p = document.createElement("p");
  p.id = "ask-notify"; p.className = "notice";
  p.innerHTML = `Bật thông báo để biết ngay khi có việc chờ duyệt, kể cả khi bạn đang ở cửa sổ khác. <button>Bật thông báo</button>`;
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
  es.onopen = () => { live.classList.add("on"); live.textContent = "● Đang cập nhật trực tiếp"; };
  es.onerror = () => { live.classList.remove("on"); live.textContent = "Mất kết nối, đang nối lại…"; };      // EventSource reconnects by itself
  ["job.updated", "review.created", "review.decided"].forEach((t) => es.addEventListener(t, onChange));
}

window.addEventListener("hashchange", route);
route().then(() => { refreshPending(false); askNotify(); });
connect();
