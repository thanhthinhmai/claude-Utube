// @ts-check
// Tier 2: one frame per shot, measured in the page (specs/020 T024, research R5).
//   node tools/filmcheck/shots.mjs <film dir> <job.json>
// job.json = {frames: [{key, shot, t}], out: <dir>, w, h, sheet?: {marks: {key: true}, cols, per}}
// Uses the studio's renderer like tools/render/record.mjs (STUDIO_RENDER_MODE / PLAYWRIGHT_CHROME, set by
// `sh bin/studio qc …`), so GPU when the machine can. Nothing in the library is changed.
// Prints one JSON line {mode, renderer, frames: [{key, shot, t, file, texts, m: {...}}]} or, with a sheet, {sheets: [..]}.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { LIB, isSoftware, readRenderer } from '../render/lib.mjs';

const [dir, jobFile] = process.argv.slice(2);
const job = JSON.parse(fs.readFileSync(jobFile, 'utf8'));
const W = job.w || 960, H = job.h || 540;
const { chromium } = await import(pathToFileURL(path.join(LIB, 'node_modules', 'playwright-core', 'index.mjs')).href);
const { ARGS } = await import(pathToFileURL(path.join(LIB, 'core', 'render', 'browser.mjs')).href);
const { server, closeServer } = await import(pathToFileURL(path.join(LIB, 'core', 'render', 'page.mjs')).href);
const { pageURL } = await import(pathToFileURL(path.join(LIB, 'core', 'render', 'serve.mjs')).href);

let mode = process.env.STUDIO_RENDER_MODE === 'gpu' ? 'gpu' : 'software';
const { port } = await server();
async function open() {
  const b = await chromium.launch({ executablePath: mode === 'gpu' ? process.env.PLAYWRIGHT_CHROME || undefined : undefined, args: ARGS });
  const p = await b.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  p.on('pageerror', (/** @type {Error} */ e) => { console.error(`[pageerror] ${e.message}`); process.exit(1); });
  await p.goto(pageURL(path.resolve(LIB), port, path.resolve(dir)));
  await p.waitForFunction(() => /** @type {any} */ (window).READY === true, null, { timeout: 180000 });
  const r = await readRenderer(p);
  if (mode === 'gpu' && isSoftware(r)) { await b.close(); mode = 'software'; return open(); }
  return { b, p, r };
}
fs.mkdirSync(job.out, { recursive: true });

// Runs in the page: statistics of one frame (a JPEG data URL) on a 240×135 copy, text boxes left out where asked
const measure = async (/** @type {any} */ a) => {
  const img = new Image(); img.src = a.url; await img.decode();
  const w = 240, h = Math.round(240 * img.height / img.width);
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = /** @type {CanvasRenderingContext2D} */ (c.getContext('2d', { willReadFrequently: true }));
  g.drawImage(img, 0, 0, w, h);
  const d = g.getImageData(0, 0, w, h).data, n = w * h;
  const L = new Float32Array(n), S = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const r = d[i * 4] / 255, gg = d[i * 4 + 1] / 255, b = d[i * 4 + 2] / 255, mx = Math.max(r, gg, b), mn = Math.min(r, gg, b);
    L[i] = 0.2126 * r + 0.7152 * gg + 0.0722 * b; S[i] = mx > 1e-6 ? (mx - mn) / mx : 0;
  }
  const rowStat = (/** @type {number} */ y) => { let s = 0, q = 0; for (let x = 0; x < w; x++) { const v = L[y * w + x]; s += v; q += v * v; } const m = s / w; return [m, Math.sqrt(Math.max(0, q / w - m * m))]; };
  const bar = (/** @type {number} */ y) => { const [m, sd] = rowStat(y); return m < 0.03 && sd < 0.01; };
  let top = 0; while (top < h / 3 && bar(top)) top++;
  let bot = h; while (bot > h * 2 / 3 && bar(bot - 1)) bot--;
  const sx = w / a.W, sy = h / a.H, boxes = a.boxes.map((/** @type {any} */ b) => [b.x0 * sx, b.y0 * sy, b.x1 * sx, b.y1 * sy]);
  const inText = (/** @type {number} */ x, /** @type {number} */ y) => boxes.some((/** @type {number[]} */ b) => x >= b[0] && x <= b[2] && y >= b[1] && y <= b[3]);
  const bins = new Map(); let used = 0, s = 0, q = 0, textPx = 0; const Lc = [];
  for (let y = top; y < bot; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x;
    if (inText(x, y)) { textPx++; continue; }
    const k = (d[i * 4] >> 4) << 8 | (d[i * 4 + 1] >> 4) << 4 | (d[i * 4 + 2] >> 4);
    bins.set(k, (bins.get(k) || 0) + 1); used++; s += L[i]; q += L[i] * L[i]; Lc.push(L[i]);
  }
  let dom = 0; for (const v of bins.values()) dom = Math.max(dom, v);
  const m = used ? s / used : 0;
  Lc.sort((x, y) => x - y);
  const Ssorted = Array.from(S).sort((x, y) => x - y);
  let mean = 0, blown = 0; for (let i = 0; i < n; i++) { mean += L[i]; if (L[i] > 0.98) blown++; }
  return { luma_mean: mean / n, sat_p50: Ssorted[Math.floor(n / 2)], dominant_share: used ? dom / used : 1,
           luma_sd: used ? Math.sqrt(Math.max(0, q / used - m * m)) : 0, content_p50: Lc.length ? Lc[Math.floor(Lc.length / 2)] : 0,
           blown_share: blown / n, text_share: textPx / n, letterbox: [top / h, (h - bot) / h] };
};

// Runs in the page: a contact sheet from frame data URLs, each cell labelled with its shot id, faults outlined red
const sheet = async (/** @type {any} */ a) => {
  const cw = 320, ch = 180, pad = 6, lab = 22, rows = Math.ceil(a.cells.length / a.cols);
  const c = document.createElement('canvas'); c.width = a.cols * (cw + pad) + pad; c.height = rows * (ch + lab + pad) + pad;
  const g = /** @type {CanvasRenderingContext2D} */ (c.getContext('2d'));
  g.fillStyle = '#111'; g.fillRect(0, 0, c.width, c.height);
  for (let i = 0; i < a.cells.length; i++) {
    const cell = a.cells[i], x = pad + (i % a.cols) * (cw + pad), y = pad + Math.floor(i / a.cols) * (ch + lab + pad);
    const img = new Image(); img.src = cell.url; await img.decode();
    g.drawImage(img, x, y + lab, cw, ch);
    g.fillStyle = cell.bad ? '#e53935' : '#ddd'; g.font = '600 16px sans-serif'; g.fillText(cell.label, x + 2, y + 16);
    if (cell.bad) { g.strokeStyle = '#e53935'; g.lineWidth = 5; g.strokeRect(x + 2.5, y + lab + 2.5, cw - 5, ch - 5); }
  }
  return c.toDataURL('image/jpeg', 0.85);
};

const ctx = await open();
const dataURL = (/** @type {string} */ f) => 'data:image/jpeg;base64,' + fs.readFileSync(f).toString('base64');
if (job.sheet) {
  const per = job.sheet.per || 48, cols = job.sheet.cols || 6, out = [];
  for (let s = 0; s * per < job.frames.length; s++) {
    const cells = job.frames.slice(s * per, (s + 1) * per).map((/** @type {any} */ f) => ({
      url: dataURL(path.join(job.out, f.key + '.jpg')), label: f.label || f.shot, bad: !!job.sheet.marks[f.key] }));
    const url = await ctx.p.evaluate(sheet, { cells, cols });
    const file = path.join(job.out, `sheet-${s + 1}.jpg`);
    fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
    out.push(file);
  }
  console.log(JSON.stringify({ sheets: out }));
} else {
  const res = [];
  for (const f of job.frames) {
    const texts = await ctx.p.evaluate((/** @type {number} */ t) => {
      const w = /** @type {any} */ (window); w.render(t);
      return typeof w.TEXTS === 'function' ? (w.TEXTS(t) || []).filter((/** @type {any} */ b) => b && b.text) : [];
    }, f.t);
    const file = path.join(job.out, f.key + '.jpg');
    fs.writeFileSync(file, await ctx.p.screenshot({ type: 'jpeg', quality: 90 }));
    const m = await ctx.p.evaluate(measure, { url: dataURL(file), boxes: texts, W, H });
    res.push({ ...f, file, texts, m });
  }
  console.log(JSON.stringify({ mode, renderer: ctx.r, frames: res }));
}
await ctx.b.close();
closeServer();
