// Tests for tools/render/probe.mjs decisions (specs/019 T007). No GPU needed: every case short-circuits before a
// GPU launch, except "real launch", which only checks the JSON shape and the gpu ⇒ hardware-renderer rule.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const PROBE = path.join(ROOT, 'tools/render/probe.mjs');
const FIELDS = ['mode', 'renderer', 'reason', 'fix', 'source', 'chrome', 'checked_at'];
const studio = (cfg) => { const d = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-')); if (cfg) { fs.mkdirSync(path.join(d, '.studio')); fs.writeFileSync(path.join(d, '.studio/config.json'), JSON.stringify(cfg)); } return d; };
function probe(env) {
  const base = { ...process.env }; delete base.STUDIO_RENDER_MODE; delete base.STUDIO_MODE; delete base.PLAYWRIGHT_CHROME;
  const r = spawnSync('node', [PROBE], { env: { ...base, STUDIO_ROOT: studio(), ...env }, encoding: 'utf8', timeout: 60000 });
  assert.equal(r.status, 0, r.stderr);
  const lines = r.stdout.trim().split('\n'); assert.equal(lines.length, 1, 'one JSON line');
  const j = JSON.parse(lines[0]);
  for (const f of FIELDS) assert.ok(f in j, f);
  if (j.mode === 'gpu') assert.doesNotMatch(String(j.renderer), /swiftshader|llvmpipe|software/i);
  return j;
}

test('config "render": "software" wins', () => {
  const j = probe({ STUDIO_ROOT: studio({ render: 'software' }) });
  assert.deepEqual([j.mode, j.reason, j.source], ['software', 'forced by config', 'config']);
  assert.match(j.fix, /config render auto/);
});

test('online mode is software', () => {
  assert.equal(probe({ STUDIO_MODE: 'online' }).reason, 'online mode');
});

test('Linux with no display', () => {
  const j = probe({ DISPLAY: '', STUDIO_PLATFORM: 'linux' });
  assert.equal(j.reason, 'no display');
  assert.match(j.fix, /WSLg/);
});

test('full Chromium missing', () => {
  const j = probe({ DISPLAY: ':0', STUDIO_PLATFORM: 'linux', STUDIO_CHROMIUM: '/nonexistent/chrome' });
  assert.deepEqual([j.mode, j.reason, j.fix], ['software', 'full Chromium missing', 'sh bin/studio deps gpu']);
});

test('a parent already decided: no new probe', () => {
  const t0 = Date.now();
  const j = probe({ STUDIO_RENDER_MODE: 'gpu', STUDIO_RENDER_RENDERER: 'ANGLE (Microsoft Corporation, D3D12 (Intel(R) UHD Graphics 730), OpenGL 4.1)', PLAYWRIGHT_CHROME: '/x/chrome-gpu.sh' });
  assert.deepEqual([j.mode, j.source, j.chrome], ['gpu', 'env', '/x/chrome-gpu.sh']);
  assert.ok(Date.now() - t0 < 5000);
});

test('a parent says gpu but the renderer is software: reported as software', () => {
  const j = probe({ STUDIO_RENDER_MODE: 'gpu', STUDIO_RENDER_RENDERER: 'ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)), SwiftShader driver)' });
  assert.equal(j.mode, 'software');
});
