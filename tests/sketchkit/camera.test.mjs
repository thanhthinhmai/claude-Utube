// Camera of the Sketch Explainer kit (specs/028 T015, FR-010, FR-012).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { camFor, camAt, pickMove, suggestSizes } from '../../my-styles/sketch-explainer/kit/camera.js';

const focus = { x: 1200, y: 520, s: 0.6 };

test('constant speed while running, then held for the last 20%', () => {
  const cam = camFor({ id: 'S001', dur: 5, cam: { move: 'push' } }, null, focus, null);
  const z = [0, 1, 2, 3].map(t => camAt(cam, t, 5).z);
  const steps = z.slice(1).map((v, i) => v - z[i]);
  for (const s of steps) assert.ok(Math.abs(s - steps[0]) < 1e-9, 'push speed is constant');
  assert.equal(camAt(cam, 4.1, 5).z, camAt(cam, 5, 5).z, 'held at the end');
  assert.ok(camAt(cam, 3.9, 5).z < camAt(cam, 4.0, 5).z, 'still moving before the hold');
  assert.ok(camAt(cam, 5, 5).z > cam.z, 'push ends closer');
});

test('push drifts sideways; still stays put', () => {
  const p = camFor({ id: 'S002', dur: 4, cam: { move: 'push' } }, null, focus, null);
  assert.notEqual(p.cx1, p.cx);
  const s = camFor({ id: 'S003', dur: 4, cam: { move: 'still' } }, null, focus, null);
  assert.equal(s.cx1, s.cx); assert.equal(s.z1, s.z);
});

test('pull starts closer and ends on the framing (a reveal)', () => {
  const c = camFor({ id: 'S004', dur: 4, cam: { move: 'pull' } }, null, focus, null);
  assert.ok(c.z > c.z1);
});

test('neighbouring shots do not repeat push or pull', () => {
  let prev = null;
  for (let i = 0; i < 200; i++) { const m = pickMove({ id: 'X' + i, dur: 3 }, prev); if (prev === 'push' || prev === 'pull') assert.notEqual(m, prev); prev = m; }
});

test('measured mix over many shots', () => {
  const n = 400, c = { push: 0, pull: 0, still: 0, follow: 0, drift: 0 };
  let prev = null; for (let i = 0; i < n; i++) { prev = pickMove({ id: 'S' + i, dur: 3 }, prev); c[prev]++; }
  const share = k => c[k] / n;
  assert.ok(share('push') >= 0.24 && share('push') <= 0.40, `push ${share('push')}`);
  assert.ok(share('pull') >= 0.18 && share('pull') <= 0.34, `pull ${share('pull')}`);
  assert.ok(share('still') >= 0.15 && share('still') <= 0.29, `still ${share('still')}`);
});

test('inserts and cards are locked', () => {
  assert.equal(pickMove({ id: 'S9', cam: { size: 'insert' } }, null), 'still');
  assert.equal(pickMove({ id: 'S9', card: { big: 'x' } }, null), 'still');
});

test('medium shot: a head fills about a quarter of the frame height', () => {
  const c = camFor({ id: 'S010', dur: 3, cam: { size: 'med', move: 'still' } }, null, focus, null);
  const head = 330 * focus.s * c.z / 1080;
  assert.ok(head > 0.2 && head < 0.28, `head share ${head}`);
});

test('suggested sizes: about half medium, at most 4 in a row, changes on most cuts', () => {
  const s = suggestSizes(300, 'film');
  const med = s.filter(x => x === 'med').length / s.length;
  assert.ok(med >= 0.38 && med <= 0.56, `medium ${med}`);
  let run = 1, worst = 1, changes = 0;
  for (let i = 1; i < s.length; i++) { if (s[i] === s[i - 1]) { run++; worst = Math.max(worst, run); } else { run = 1; changes++; } }
  assert.ok(worst <= 4, `run ${worst}`);
  assert.ok(changes / (s.length - 1) >= 0.55, `changes ${changes / (s.length - 1)}`);
});
