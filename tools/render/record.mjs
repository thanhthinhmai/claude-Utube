// @ts-check
// The studio's video recorder (specs/019, research R5–R7, data-model "Recording run").
//   node tools/render/record.mjs <film> [--fps 24] [--workers N] [--out FILE] [--size 1920x1080] [--until SECONDS]
// Same capture as the library's core/render/video.mjs (JPEG screenshots piped to ffmpeg as MJPEG, x264 medium crf 14),
// but in chunks of 10 s of film that survive a closed browser and resume across runs. The browser comes from
// STUDIO_RENDER_MODE / PLAYWRIGHT_CHROME (set by `sh bin/studio render`); a GPU run whose browser falls back to
// software is thrown away and recorded again in software, so one video never mixes the two.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { LIB, isSoftware, resolveFilm, fingerprint, planChunks } from './lib.mjs';
import { checkChunk, combine } from './chunkcheck.mjs';

const argv = process.argv.slice(2);
const opt = (/** @type {string} */ k, /** @type {string|null} */ d) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : d; };
if (!argv[0] || argv[0].startsWith('--')) { console.error('usage: record.mjs <film> [--fps N] [--workers N] [--out FILE] [--size WxH] [--until S]'); process.exit(2); }
const FILM = resolveFilm(argv[0]);
const FPS = +(opt('--fps', '24') ?? 24);
const [W, H] = String(opt('--size', '1920x1080')).split('x').map(Number);
const UNTIL = opt('--until', null) != null ? +(/** @type {string} */ (opt('--until', null))) : null;
const OUT = path.resolve(opt('--out', null) || path.join(FILM, 'out', 'video.mp4'));
const CHUNK_MAX = +(process.env.STUDIO_RENDER_CHUNK || 10 * FPS);   // ≤ 10 s of film per chunk (FR-008)
// specs/020 tier 3: each finished chunk is checked (black frames, stills); a fault stops the run unless --no-stop
const NO_STOP = argv.includes('--no-stop'), FRESH = argv.includes('--fresh');
const LIMITS = (() => { try { return JSON.parse(process.env.STUDIO_QC_LIMITS || '{}'); } catch { return {}; } })();
const STILL_MAX = +(LIMITS.still_max || 6);
if (!(FPS > 0) || !(W > 0 && H > 0 && W % 2 === 0 && H % 2 === 0) || (UNTIL != null && !(UNTIL > 0))) { console.error('bad --fps, --size or --until'); process.exit(2); }

const { chromium } = await import(pathToFileURL(path.join(LIB, 'node_modules', 'playwright-core', 'index.mjs')).href);
const { ARGS } = await import(pathToFileURL(path.join(LIB, 'core', 'render', 'browser.mjs')).href);
const { server } = await import(pathToFileURL(path.join(LIB, 'core', 'render', 'page.mjs')).href);
const { pageURL } = await import(pathToFileURL(path.join(LIB, 'core', 'render', 'serve.mjs')).href);

fs.mkdirSync(path.join(FILM, 'out'), { recursive: true });
const LOG = path.join(FILM, 'out', 'render.log');
fs.writeFileSync(LOG, process.env.STUDIO_RENDER_SKIPPED_CHECKS ? `render: checks skipped — ${process.env.STUDIO_RENDER_SKIPPED_CHECKS}\n` : '');   // specs/020 FR-009
const t0 = Date.now();
const log = (/** @type {string} */ s) => { console.log(s); fs.appendFileSync(LOG, s + '\n'); };
const secs = () => Math.round((Date.now() - t0) / 1000);

let mode = process.env.STUDIO_RENDER_MODE === 'gpu' ? 'gpu' : 'software';
const GPU_EXE = process.env.PLAYWRIGHT_CHROME || undefined;
const procs = new Set();     // running ffmpeg processes
const browsers = new Set();
let crashHookUsed = false;   // test hook: STUDIO_RENDER_TEST_CRASH_AT=<frame> closes the browser once
class GpuLost extends Error {}
class QcStop extends Error { constructor(/** @type {any[]} */ faults) { super('tier 3 fault'); this.faults = faults; } }
class Abort extends Error {}
let abort = /** @type {Error|null} */ (null);

const { port } = await server();
const url = pageURL(path.resolve(LIB), port, FILM);

async function openPage() {
  const b = await chromium.launch({ executablePath: mode === 'gpu' ? GPU_EXE : undefined, args: ARGS });
  browsers.add(b);
  const p = await b.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  p.on('pageerror', (/** @type {Error} */ e) => { log(`[pageerror] ${e.message}`); cleanupAndExit(1); });
  await p.goto(url);
  await p.waitForFunction(() => /** @type {any} */ (window).READY === true, null, { timeout: 180000 });
  const r = await p.evaluate(() => {
    const g = document.createElement('canvas').getContext('webgl2') || document.createElement('canvas').getContext('webgl');
    if (!g) return null;
    const e = g.getExtension('WEBGL_debug_renderer_info');
    return String(e ? g.getParameter(e.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER));
  });
  if (mode === 'gpu' && isSoftware(r)) { await b.close().catch(() => {}); browsers.delete(b); throw new GpuLost(String(r)); }
  return { b, p, r, dur: await p.evaluate(() => /** @type {any} */ (window).DUR) };
}
async function closeCtx(/** @type {any} */ ctx) { if (ctx) { browsers.delete(ctx.b); await ctx.b.close().catch(() => {}); } }

function cleanupAndExit(/** @type {number} */ code) {
  for (const f of procs) { try { /** @type {any} */ (f).kill('SIGKILL'); } catch {} }
  for (const b of browsers) /** @type {any} */ (b).close().catch(() => {});
  if (CH) for (const f of fs.existsSync(CH) ? fs.readdirSync(CH) : []) if (f.endsWith('.part.mp4')) fs.rmSync(path.join(CH, f), { force: true });
  process.exit(code);
}
process.on('SIGINT', () => { log('render: stopped (finished chunks are kept)'); cleanupAndExit(130); });
process.on('SIGTERM', () => { log('render: stopped (finished chunks are kept)'); cleanupAndExit(143); });

let CH = /** @type {string|null} */ (null);

/** One full recording in the current mode. Throws GpuLost when a GPU launch turns out to be software. */
async function run() {
  const ctx0 = await openPage();
  const N = Math.ceil((UNTIL != null ? Math.min(UNTIL, ctx0.dur) : ctx0.dur) * FPS);
  const fp = fingerprint(FILM, W, H, FPS, UNTIL);
  const shots = await ctx0.p.evaluate(() => { const s = /** @type {any} */ (window).SHOTS; return Array.isArray(s) ? s : []; });
  const memWorkers = Math.max(1, Math.floor(os.freemem() / (1.5 * 2 ** 30)));
  const memCap = +(process.env.STUDIO_RENDER_TEST_FREE_GB ? Math.max(1, Math.floor(+process.env.STUDIO_RENDER_TEST_FREE_GB / 1.5)) : memWorkers);
  const want = Math.max(1, +(opt('--workers', null) || Math.min(2, memCap)));   // FR-011: GPU and software alike
  // short films: smaller chunks so every worker has work (SC-003); the size is part of the folder name, so a run
  // with another size never reuses chunks that cover other frames
  const CHUNK = Math.max(1, Math.min(CHUNK_MAX, Math.ceil(N / want)));
  const base = path.join(FILM, 'out', '.chunks');
  CH = path.join(base, `${fp}-${mode}-s${CHUNK}`);
  fs.mkdirSync(CH, { recursive: true });
  for (const f of fs.readdirSync(CH)) if (f.endsWith('.part.mp4')) fs.rmSync(path.join(CH, f), { force: true });
  const chunks = planChunks(N, CHUNK);
  const name = (/** @type {number} */ c) => path.join(/** @type {string} */ (CH), `c_${String(c).padStart(4, '0')}.mp4`);
  reused = reuseStopped(chunks, name, shots, fp, CHUNK);
  const todo = chunks.filter(x => !fs.existsSync(name(x.c)));
  // tier 3 results of chunks already on disk (this run's earlier attempt, or reused)
  const checked = [];
  const check = (/** @type {{c:number,a:number,z:number}} */ x) => {
    const j = name(x.c).replace(/\.mp4$/, '.json');
    let res = null;
    try { res = JSON.parse(fs.readFileSync(j, 'utf8')); } catch { res = checkChunk(name(x.c), (x.z - x.a) / FPS); fs.writeFileSync(j, JSON.stringify(res)); }
    checked.push({ c: x.c, t0: x.a / FPS, t1: x.z / FPS, res });
    const got = combine(checked, { stillMax: STILL_MAX, shots, exceptions: LIMITS.exceptions || [], dur: N / FPS, fps: FPS });
    for (const f of got) if (!faults.some(g => g.rule === f.rule && g.at === f.at)) { faults.push(f); log(`✗ render: chunk ${f.chunk} (${f.shot || '?'}, ${f.at} s) ${f.rule} ${f.measure} s`); }
    if (faults.length && !NO_STOP && !abort) abort = new QcStop(faults);
  };
  for (const x of chunks) if (fs.existsSync(name(x.c))) check(x);
  stopInfo = { fp, CHUNK, shots };
  const workers = Math.max(1, Math.min(todo.length || 1, want));
  log(`render: ${mode} · ${ctx0.r} · ${N} frames · ${chunks.length} chunks (${chunks.length - todo.length} already done) · ${workers} workers`
    + (mode === 'gpu' && GPU_EXE ? ' · a Chrome window is open off-screen, do not close it' : ''));
  let left = todo.length;

  async function renderChunk(/** @type {any} */ ctx, /** @type {{c:number,a:number,z:number}} */ x) {
    const part = name(x.c) + '.part.mp4';
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', part], { stdio: ['pipe', 'inherit', 'inherit'] });
    procs.add(ff);
    const done = new Promise((res, rej) => ff.on('close', code => { procs.delete(ff); code === 0 ? res(0) : rej(new Error('ffmpeg exit ' + code)); }));
    try {
      for (let i = x.a; i < x.z; i++) {
        if (abort) throw new Abort();
        if (!crashHookUsed && process.env.STUDIO_RENDER_TEST_CRASH_AT && i === +process.env.STUDIO_RENDER_TEST_CRASH_AT) { crashHookUsed = true; await ctx.b.close(); }
        await ctx.p.evaluate((/** @type {number} */ t) => /** @type {any} */ (window).render(t), i / FPS);
        const buf = await ctx.p.screenshot({ type: 'jpeg', quality: 95 });
        if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      }
    } catch (e) { ff.stdin.destroy(); ff.kill('SIGKILL'); await done.catch(() => {}); fs.rmSync(part, { force: true }); throw e; }
    ff.stdin.end(); await done; fs.renameSync(part, name(x.c));
    check(x);
  }

  async function worker(/** @type {number} */ w, /** @type {any} */ ctx) {
    try {
      ctx = ctx || await openPage();
      while (todo.length && !abort) {
        const x = /** @type {{c:number,a:number,z:number}} */ (todo.shift());
        for (let tries = 0; ; tries++) {
          try { await renderChunk(ctx, x); break; }
          catch (e) {
            if (e instanceof Abort || abort) throw abort || e;
            log(`w${w} chunk ${x.c} failed (${String(/** @type {any} */ (e)?.message).split('\n')[0].slice(0, 80)}); reopening the browser`);
            await closeCtx(ctx);
            if (tries >= 3) throw new Error(`chunk ${x.c} failed 4 times`);
            ctx = await openPage();
          }
        }
        left--; if (left % 5 === 0 || left === 0) log(`${chunks.length - left}/${chunks.length} chunks  ${secs()}s`);
      }
    } catch (e) { abort = abort || /** @type {Error} */ (e); } finally { await closeCtx(ctx); }
  }
  await Promise.all(Array.from({ length: workers }, (_, w) => worker(w, w === 0 ? ctx0 : null)));
  if (abort) throw abort;
  if (faults.length && !(NO_STOP)) throw new QcStop(faults);

  fs.writeFileSync(path.join(CH, 'list.txt'), chunks.map(x => `file '${path.basename(name(x.c))}'`).join('\n'));
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  const tmp = OUT + '.tmp.mp4';
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'list.txt', '-c', 'copy', tmp], { cwd: CH, stdio: 'inherit' });
  const got = +execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v', '-count_packets', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', tmp], { encoding: 'utf8' }).trim();
  if (got !== N) { fs.rmSync(tmp, { force: true }); throw new Error(`joined video has ${got} frames, expected ${N}`); }
  fs.renameSync(tmp, OUT);
  for (const d of fs.readdirSync(base)) if (path.join(base, d) !== CH) fs.rmSync(path.join(base, d), { recursive: true, force: true });
  log(`video ${OUT} · ${N} frames · ${mode} · ${secs()}s`);
}

let reused = 0;
const faults = /** @type {any[]} */ ([]);
let stopInfo = /** @type {any} */ (null);
const STOPPED = path.join(FILM, 'out', '.chunks', 'STOPPED.json');
const shotsUntil = (/** @type {any[]} */ shots, /** @type {number} */ t) => JSON.stringify(shots.filter(s => s[0] < t - 1e-6).map(s => [+(+s[0]).toFixed(3), +(+s[1]).toFixed(3), String(s[3] || '')]));

/** specs/020 R8: after a tier-3 stop and a fix, the chunks wholly before the fault (and before the first changed shot) are copied. */
function reuseStopped(/** @type {{c:number,a:number,z:number}[]} */ chunks, /** @type {(c:number)=>string} */ name, /** @type {any[]} */ shots, /** @type {string} */ fp, /** @type {number} */ chunkSize) {
  if (FRESH || !fs.existsSync(STOPPED)) return 0;
  let st; try { st = JSON.parse(fs.readFileSync(STOPPED, 'utf8')); } catch { return 0; }
  if (st.fingerprint === fp || st.chunk_size !== chunkSize || st.fps !== FPS || st.size !== `${W}x${H}` || st.mode !== mode) return 0;
  if (!fs.existsSync(st.folder)) return 0;
  let limit = st.first_bad_t;
  for (const s of st.shots) {                       // the first shot that is not the same as in the stopped run
    const n = shots.find(x => String(x[3] || '') === s[2]);
    if (!n || Math.abs(n[0] - s[0]) > 1e-3 || Math.abs(n[1] - s[1]) > 1e-3) { limit = Math.min(limit, s[0]); break; }
  }
  let k = 0;
  for (const x of chunks) {
    if (x.z / FPS > limit + 1e-6) break;
    const old = path.join(st.folder, path.basename(name(x.c)));
    if (!fs.existsSync(old) || fs.existsSync(name(x.c))) continue;
    fs.copyFileSync(old, name(x.c));
    if (fs.existsSync(old.replace(/\.mp4$/, '.json'))) fs.copyFileSync(old.replace(/\.mp4$/, '.json'), name(x.c).replace(/\.mp4$/, '.json'));
    k++;
  }
  log(`render: reused ${k} chunks from the stopped run`);
  return k;
}

function writeResult(/** @type {any} */ stopped) {
  try {
    fs.writeFileSync(path.join(FILM, 'out', 'render-qc.json'), JSON.stringify({ pass: !faults.length, faults, reused, stopped,
      no_stop: NO_STOP, skipped_checks: process.env.STUDIO_RENDER_SKIPPED_CHECKS || null, at: new Date().toISOString() }));
  } catch {}
}

try {
  try { await run(); }
  catch (e) {
    if (!(e instanceof GpuLost)) throw e;
    log(`render: GPU lost (${e.message}) → re-recording everything in software`);
    if (CH) fs.rmSync(CH, { recursive: true, force: true });
    mode = 'software'; abort = null; faults.length = 0;
    await run();
  }
  writeResult(null);
  if (faults.length) { log(`render: ${faults.length} chunk fault(s) (--no-stop): see above`); cleanupAndExit(1); }
  cleanupAndExit(0);
} catch (e) {
  if (e instanceof QcStop && CH && stopInfo) {
    const first = Math.min(...e.faults.map((/** @type {any} */ f) => f.chunk));
    for (const f of fs.readdirSync(CH)) { const m = /^c_(\d+)\.(mp4|json)$/.exec(f); if (m && +m[1] >= first) fs.rmSync(path.join(CH, f), { force: true }); }
    const f0 = e.faults.find((/** @type {any} */ f) => f.chunk === first);
    const st = { fingerprint: stopInfo.fp, chunk_size: stopInfo.CHUNK, fps: FPS, size: `${W}x${H}`, mode, folder: CH, first_bad: first,
      first_bad_t: first * stopInfo.CHUNK / FPS, shot: f0.shot, rule: f0.rule, at: f0.at,
      shots: JSON.parse(shotsUntil(stopInfo.shots, first * stopInfo.CHUNK / FPS)) };
    fs.writeFileSync(STOPPED, JSON.stringify(st));
    writeResult(st);
    log(`render: stopped at chunk ${first} (${f0.shot || '?'}, ${f0.at} s, ${f0.rule}); chunks before it are kept. Fix the shot and run again.`);
    cleanupAndExit(1);
  }
  log(`render: failed — ${String(/** @type {any} */ (e)?.message || e).split('\n')[0]}`);
  cleanupAndExit(1);
}
