// Tests for tools/render/record.mjs (specs/019 T008, T009, T023) on the tiny 2D film, software browser (no GPU needed).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, spawnSync, execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const REC = path.join(ROOT, 'tools/render/record.mjs');
const FIX = path.join(ROOT, 'tests/render/fixtures/tiny-film');
const film = () => { const d = fs.mkdtempSync(path.join(os.tmpdir(), 'rec-')); fs.copyFileSync(path.join(FIX, 'index.html'), path.join(d, 'index.html')); return d; };
const baseEnv = (extra = {}) => { const e = { ...process.env, STUDIO_RENDER_CHUNK: '10', ...extra }; delete e.PLAYWRIGHT_CHROME; if (!('STUDIO_RENDER_MODE' in extra)) delete e.STUDIO_RENDER_MODE; return e; };
const args = (d) => [REC, d, '--fps', '10', '--size', '320x240', '--workers', '1'];
const frames = (f) => +execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v', '-count_frames', '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', f], { encoding: 'utf8' }).trim();
const run = (d, env = {}) => spawnSync('node', args(d), { env: baseEnv(env), encoding: 'utf8', timeout: 180000 });
const chunkDir = (d) => { const b = path.join(d, 'out/.chunks'); const x = fs.readdirSync(b); assert.equal(x.length, 1); return path.join(b, x[0]); };

test('software: 3 chunks, exact frame count, header line', () => {
  const d = film();
  const r = run(d);
  assert.equal(r.status, 0, r.stdout + r.stderr);
  assert.equal(frames(path.join(d, 'out/video.mp4')), 30);
  const first = fs.readFileSync(path.join(d, 'out/render.log'), 'utf8').split('\n')[0];
  assert.match(first, /^render: software · .+ · 30 frames · 3 chunks \(0 already done\) · 1 workers$/);
});

test('GPU mode with a software browser: thrown away, re-recorded in software', () => {
  const d = film();
  const r = run(d, { STUDIO_RENDER_MODE: 'gpu' });
  assert.equal(r.status, 0, r.stdout + r.stderr);
  const logTxt = fs.readFileSync(path.join(d, 'out/render.log'), 'utf8');
  assert.match(logTxt, /GPU lost .* re-recording everything in software/);
  assert.match(logTxt, /render: software · /);
  assert.equal(frames(path.join(d, 'out/video.mp4')), 30);
  assert.ok(!fs.readdirSync(path.join(d, 'out/.chunks')).some(x => x.includes('-gpu')), 'no GPU chunk kept');
});

test('stopped after a chunk: the next run keeps finished chunks', async () => {
  const d = film();
  const p = spawn('node', args(d), { env: baseEnv({ STUDIO_RENDER_CHUNK: '5' }) });
  await new Promise((res) => { const iv = setInterval(() => {
    try { if (fs.readdirSync(chunkDir(d)).some(f => /^c_\d+\.mp4$/.test(f))) { clearInterval(iv); p.kill('SIGTERM'); res(0); } } catch {}
  }, 100); });
  await new Promise(r => p.on('close', r));
  const ch = chunkDir(d);
  const done = fs.readdirSync(ch).filter(f => /^c_\d+\.mp4$/.test(f));
  assert.ok(done.length >= 1);
  assert.ok(!fs.readdirSync(ch).some(f => f.endsWith('.part.mp4')), 'no .part left after SIGTERM');
  const m0 = fs.statSync(path.join(ch, done[0])).mtimeMs;
  const r = run(d, { STUDIO_RENDER_CHUNK: '5' });
  assert.equal(r.status, 0, r.stdout + r.stderr);
  assert.match(fs.readFileSync(path.join(d, 'out/render.log'), 'utf8'), new RegExp(`6 chunks \\(${done.length} already done\\)`));
  assert.equal(fs.statSync(path.join(ch, done[0])).mtimeMs, m0, 'finished chunk not rewritten');
  assert.equal(frames(path.join(d, 'out/video.mp4')), 30);
});

test('changed source: nothing reused, old chunks removed after success', () => {
  const d = film();
  assert.equal(run(d).status, 0);
  const old = chunkDir(d);
  fs.appendFileSync(path.join(d, 'index.html'), '\n<!-- changed -->\n');
  const r = run(d);
  assert.equal(r.status, 0, r.stdout + r.stderr);
  assert.match(fs.readFileSync(path.join(d, 'out/render.log'), 'utf8'), /3 chunks \(0 already done\)/);
  assert.ok(!fs.existsSync(old));
});

test('a leftover .part file is deleted at start', () => {
  const d = film();
  assert.equal(run(d).status, 0);
  const ch = chunkDir(d);
  fs.rmSync(path.join(ch, 'c_0001.mp4'));
  fs.writeFileSync(path.join(ch, 'c_0001.mp4.part.mp4'), 'junk');
  const r = run(d);
  assert.equal(r.status, 0, r.stdout + r.stderr);
  assert.match(fs.readFileSync(path.join(d, 'out/render.log'), 'utf8'), /3 chunks \(2 already done\)/);
  assert.equal(frames(path.join(d, 'out/video.mp4')), 30);
});

test('the browser dies mid-chunk: reopened, video complete', () => {
  const d = film();
  const r = run(d, { STUDIO_RENDER_TEST_CRASH_AT: '14' });
  assert.equal(r.status, 0, r.stdout + r.stderr);
  assert.match(fs.readFileSync(path.join(d, 'out/render.log'), 'utf8'), /chunk 1 failed .*reopening the browser/);
  assert.equal(frames(path.join(d, 'out/video.mp4')), 30);
});

test('a short film is split so every worker has work', () => {
  const d = film();
  const r = spawnSync('node', [REC, d, '--fps', '10', '--size', '320x240', '--workers', '2'], { env: baseEnv({ STUDIO_RENDER_CHUNK: '100' }), encoding: 'utf8', timeout: 180000 });
  assert.equal(r.status, 0, r.stdout + r.stderr);
  assert.match(fs.readFileSync(path.join(d, 'out/render.log'), 'utf8'), /30 frames · 2 chunks \(0 already done\) · 2 workers/);
  assert.equal(frames(path.join(d, 'out/video.mp4')), 30);
});

test('--until records only the start of the film', () => {
  const d = film();
  const r = spawnSync('node', [...args(d), '--until', '1.5'], { env: baseEnv(), encoding: 'utf8', timeout: 180000 });
  assert.equal(r.status, 0, r.stdout + r.stderr);
  assert.equal(frames(path.join(d, 'out/video.mp4')), 15);
});
