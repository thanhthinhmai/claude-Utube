// @ts-check
// Shared helpers for the studio's render tools (specs/019): film lookup, Chromium lookup, renderer check,
// source fingerprint, chunk plan. No browser is started here.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const LIB = process.env.STUDIO_LIB || path.join(ROOT, 'lib', 'lemo-opuscar');
export const WRAPPER = path.join(ROOT, 'tools', 'render', 'chrome-gpu.sh');

/** A software WebGL renderer string (SwiftShader, llvmpipe…). */
export const isSoftware = (/** @type {string|null|undefined} */ r) => !r || /swiftshader|llvmpipe|softpipe|software/i.test(r);

/** Path of the full Playwright Chromium matching the library's playwright-core, or null when it is not there. */
export function findChromium() {
  if (process.env.STUDIO_CHROMIUM) return fs.existsSync(process.env.STUDIO_CHROMIUM) ? process.env.STUDIO_CHROMIUM : null;
  let rev = null;
  try {
    const b = JSON.parse(fs.readFileSync(path.join(LIB, 'node_modules', 'playwright-core', 'browsers.json'), 'utf8'));
    rev = b.browsers.find((/** @type {any} */ x) => x.name === 'chromium')?.revision ?? null;
  } catch { return null; }
  const base = process.env.PLAYWRIGHT_BROWSERS_PATH || path.join(os.homedir(), '.cache', 'ms-playwright');
  const exe = path.join(base, `chromium-${rev}`, process.platform === 'darwin' ? 'chrome-mac/Chromium.app/Contents/MacOS/Chromium' : 'chrome-linux64/chrome');
  return fs.existsSync(exe) ? exe : null;
}

/** A film name under films/, or a path to a folder holding index.html. Throws when neither. */
export function resolveFilm(/** @type {string} */ nameOrPath) {
  const cands = [path.resolve(nameOrPath), path.join(ROOT, 'films', nameOrPath)];
  for (const c of cands) if (fs.existsSync(path.join(c, 'index.html'))) return c;
  throw new Error(`no film "${nameOrPath}": expected films/<name>/index.html or a folder with index.html`);
}

/** The WebGL renderer string the page's browser really uses. */
export async function readRenderer(/** @type {any} */ page) {
  return page.evaluate(() => {
    const g = document.createElement('canvas').getContext('webgl2') || document.createElement('canvas').getContext('webgl');
    if (!g) return null;
    const e = g.getExtension('WEBGL_debug_renderer_info');
    return String(e ? g.getParameter(e.UNMASKED_RENDERER_WEBGL) : g.getParameter(g.RENDERER));
  });
}

const SKIP_DIRS = new Set(['out', 'stills', 'publish', '.check', 'node_modules']);
const SKIP_FILE = /\.(mp4|log)$|^(checks\.json|CHECKS\.md|qc-exceptions\.json)$/;   // 020: exceptions never re-record chunks

/** SHA-256 over the film's source files (sorted relative path + bytes) and the output shape (data-model.md). */
export function fingerprint(/** @type {string} */ dir, /** @type {number} */ w, /** @type {number} */ h, /** @type {number} */ fps, /** @type {number|null} */ until = null) {
  const files = [];
  const walk = (/** @type {string} */ d, /** @type {string} */ rel) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const r = rel ? `${rel}/${e.name}` : e.name;
      if (e.isDirectory()) { if (!(rel === '' && SKIP_DIRS.has(e.name))) walk(path.join(d, e.name), r); }
      else if (e.isFile() && !SKIP_FILE.test(e.name)) files.push(r);
    }
  };
  walk(dir, '');
  files.sort();
  const hash = crypto.createHash('sha256');
  for (const f of files) { hash.update(f + '\0'); hash.update(fs.readFileSync(path.join(dir, f))); hash.update('\0'); }
  hash.update(`${w}x${h}@${fps}` + (until != null ? `:${until}` : ''));
  return hash.digest('hex').slice(0, 16);
}

/** Chunks [{c, a, z}] covering frames [0, N) with `size` frames each (the last one shorter). */
export function planChunks(/** @type {number} */ N, /** @type {number} */ size) {
  const out = [];
  for (let c = 0, a = 0; a < N; c++, a += size) out.push({ c, a, z: Math.min(N, a + size) });
  return out;
}
