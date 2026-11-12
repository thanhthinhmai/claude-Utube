// Tests for tools/render/chrome-gpu.sh (specs/019 T006): flags in, flags out, missing Chromium.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const WRAPPER = path.join(ROOT, 'tools/render/chrome-gpu.sh');

test('drops headless flags, adds GPU and off-screen flags, keeps the rest in order', () => {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'wrap-'));
  const fake = path.join(d, 'chrome');
  fs.writeFileSync(fake, '#!/bin/sh\nfor a in "$@"; do echo "$a"; done\necho "GALLIUM=$GALLIUM_DRIVER"\n'); fs.chmodSync(fake, 0o755);
  const r = spawnSync('sh', [WRAPPER, '--headless=new', '--hide-scrollbars', '--remote-debugging-pipe', '--mute-audio', '--user-data-dir=/x', 'about:blank'],
    { env: { ...process.env, STUDIO_CHROMIUM: fake }, encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  const args = r.stdout.trim().split('\n');
  for (const gone of ['--headless=new', '--hide-scrollbars', '--mute-audio']) assert.ok(!args.includes(gone), gone);
  for (const f of ['--use-angle=gl', '--enable-gpu', '--ignore-gpu-blocklist', '--ozone-platform=x11', '--window-position=-3000,-3000',
    '--disable-backgrounding-occluded-windows']) assert.ok(args.includes(f), f);
  const kept = args.filter(a => ['--remote-debugging-pipe', '--user-data-dir=/x', 'about:blank'].includes(a));
  assert.deepEqual(kept, ['--remote-debugging-pipe', '--user-data-dir=/x', 'about:blank']);
  assert.ok(args.includes('GALLIUM=d3d12'));
});

test('missing Chromium: exit 127 and the fix', () => {
  const r = spawnSync('sh', [WRAPPER, '--headless'], { env: { ...process.env, STUDIO_CHROMIUM: '/nonexistent/chrome' }, encoding: 'utf8' });
  assert.equal(r.status, 127);
  assert.match(r.stderr, /sh bin\/studio deps gpu/);
});
