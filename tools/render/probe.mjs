// @ts-check
// Decide how the studio renders (specs/019, research R8): GPU or software. Prints one JSON line (data-model.md).
//   node tools/render/probe.mjs
// Order: STUDIO_RENDER_MODE from a parent → config "render": "software" → online mode → macOS (library default
// browser) → no display → full Chromium missing → launch through chrome-gpu.sh and read the real renderer.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { ROOT, LIB, WRAPPER, isSoftware, findChromium } from './lib.mjs';

const TIMEOUT = +(process.env.STUDIO_PROBE_TIMEOUT || 30000);
const FIX_DISPLAY = 'Linux: chạy trong phiên có màn hình. Windows/WSL: cần Windows 11 có WSLg (wsl --update trong PowerShell); xưởng và app không tự bật';

function out(/** @type {Record<string, any>} */ o) {
  const r = { mode: 'software', renderer: null, reason: null, fix: null, source: 'auto', chrome: null, checked_at: new Date().toISOString(), ...o };
  if (r.mode === 'gpu' && isSoftware(r.renderer)) Object.assign(r, { mode: 'software', reason: 'the browser fell back to software' });
  console.log(JSON.stringify(r));
  process.exit(0);
}

function setting() {
  try {
    const p = path.join(process.env.STUDIO_ROOT || ROOT, '.studio', 'config.json');
    return JSON.parse(fs.readFileSync(p, 'utf8')).render || 'auto';
  } catch { return 'auto'; }
}

/** Launch a browser, read the WebGL renderer, close. */
async function launchAndRead(/** @type {string|undefined} */ exe, /** @type {string[]} */ args) {
  const { chromium } = await import(pathToFileURL(path.join(LIB, 'node_modules', 'playwright-core', 'index.mjs')).href);
  const b = await chromium.launch({ executablePath: exe, args, timeout: TIMEOUT });
  try {
    const p = await b.newPage();
    return await p.evaluate(() => {
      const g = document.createElement('canvas').getContext('webgl2') || document.createElement('canvas').getContext('webgl');
      if (!g) return null;
      const e = g.getExtension('WEBGL_debug_renderer_info');
      return String(e ? g.getParameter(e.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER));
    });
  } finally { await b.close().catch(() => {}); }
}

const timed = (/** @type {Promise<any>} */ p) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error(`no answer in ${TIMEOUT / 1000} s`)), TIMEOUT))]);

const env = process.env.STUDIO_RENDER_MODE;
if (env === 'gpu' || env === 'software') {
  out({ mode: env, renderer: process.env.STUDIO_RENDER_RENDERER || null, source: 'env', chrome: process.env.PLAYWRIGHT_CHROME || null,
    reason: env === 'software' ? (process.env.STUDIO_RENDER_REASON || null) : null });
}
if (setting() === 'software') out({ reason: 'forced by config', source: 'config', fix: 'sh bin/studio config render auto' });
// online in containers (Docker runner): no GPU. The desktop app's host is also STUDIO_MODE=online, but RUNNER=local.
if (process.env.STUDIO_MODE === 'online' && process.env.RUNNER !== 'local') out({ reason: 'online mode' });

try {
  if ((process.env.STUDIO_PLATFORM || process.platform) === 'darwin') {
    const br = await import(pathToFileURL(path.join(LIB, 'core', 'render', 'browser.mjs')).href);
    const r = await timed(launchAndRead(br.EXE, br.ARGS));
    out(isSoftware(r) ? { renderer: r, reason: 'the browser fell back to software', fix: 'kiểm driver GPU rồi chạy lại sh bin/studio status' } : { mode: 'gpu', renderer: r });
  }
  if (!process.env.DISPLAY) out({ reason: 'no display', fix: FIX_DISPLAY });
  if (!findChromium()) out({ reason: 'full Chromium missing', fix: 'sh bin/studio deps gpu' });
  const r = await timed(launchAndRead(WRAPPER, ['--enable-gpu', '--ignore-gpu-blocklist']));
  out(isSoftware(r)
    ? { renderer: r, reason: 'the browser fell back to software', fix: 'kiểm driver GPU của Windows rồi chạy lại sh bin/studio status' }
    : { mode: 'gpu', renderer: r, chrome: WRAPPER });
} catch (e) {
  out({ reason: `probe failed: ${String(/** @type {any} */ (e)?.message || e).split('\n')[0].slice(0, 160)}` });
}
