// specs/023 T037: acting is a pure function of time (act list, blink, talk, breath) and the arm blend of figure.js.
import test from 'node:test';
import assert from 'node:assert/strict';
import { actState, blinkOn, talkOn, breath, riseOf, ease, BLINK_S, blackAt, streakAt } from '../acting.js';
import { check } from '../plan.js';
import { joints, makeFigure } from '../figure.js';

test('an arm act rises in the rise time, then holds', () => {
  const acts = [[0.5, 'raise-hand']];
  assert.equal(actState(acts, 0.4).arms, null);
  const mid = actState(acts, 0.5 + 0.2, 0.4), done = actState(acts, 2.0, 0.4);
  assert.equal(mid.arms, 'raise-hand');
  assert.ok(mid.w > 0.3 && mid.w < 0.7, `w ${mid.w}`);
  assert.equal(done.w, 1);
  assert.equal(actState(acts, 3.0, 0.4).w, 1);                      // holds
});

test('a second arm act blends from the first; face, tilt, look and nod', () => {
  const acts = [[0.2, 'raise-hand'], [1.0, 'pose:cheer'], [1.2, 'face:wow'], [1.4, 'tilt-head'], [1.5, 'look:left'], [2.0, 'nod']];
  const st = actState(acts, 1.1, 0.4);
  assert.equal(st.from, 'raise-hand'); assert.equal(st.arms, 'cheer');
  assert.equal(actState(acts, 1.3, 0.4).face, 'wow');
  assert.ok(actState(acts, 3, 0.4).tilt > 0.2);
  assert.ok(actState(acts, 3, 0.4).turn > 0.5);
  assert.ok(actState(acts, 2.3, 0.4).pitch > 0.2);                  // mid-nod
  assert.ok(Math.abs(actState(acts, 3.0, 0.4).pitch) < 1e-9);        // the nod is over
});

test('rise time comes from the template and stays in the measured range', () => {
  assert.equal(riseOf({ motion: { rise_s_p50: 0.417 } }), 0.417);
  assert.equal(riseOf({ motion: { rise_s_p50: 2 } }), 0.83);
  assert.equal(riseOf(null), 0.417);
  assert.equal(ease(-1), 0); assert.equal(ease(2), 1);
});

test('blinks: seeded, 0.12 s long, every 2–5 s, the same for the same t', () => {
  const on = [];
  for (let t = 0; t < 60; t += 0.01) if (blinkOn(1, t)) on.push(Math.round(t * 100) / 100);
  const starts = on.filter((t, i) => i === 0 || t - on[i - 1] > 0.05);
  assert.ok(starts.length >= 60 / 5 - 1 && starts.length <= 60 / 2 + 1, `${starts.length} blinks`);
  for (let i = 1; i < starts.length; i++) assert.ok(starts[i] - starts[i - 1] >= 2 - 0.02);
  assert.ok(on.length / starts.length <= BLINK_S / 0.01 + 1);
  assert.equal(blinkOn(1, starts[2] + 0.05), true);
  assert.notDeepEqual(starts, (() => { const o = []; for (let t = 0; t < 60; t += 0.01) if (blinkOn(2, t)) o.push(t); return o; })().slice(0, starts.length));
});

test('talk and breath', () => {
  const n = Array.from({ length: 100 }, (_, k) => talkOn([[0, 1]], k / 100)).filter(Boolean).length;
  assert.ok(n > 40 && n < 80, `${n}`);
  assert.equal(talkOn([[0, 1]], 1.5), false);
  assert.ok(Math.abs(breath(1, 0.9) - 1) <= 0.012);
});

test('figure: arms blend between two acts, the wave moves the hand', () => {
  const a = joints('stand', 0), b = joints('stand', 0, { mix: { to: 'raise-hand', w: 1 } });
  const half = joints('stand', 0, { mix: { to: 'raise-hand', w: 0.5 } });
  assert.ok(b.arms[1].hand.y > a.arms[1].hand.y + 0.5);
  assert.ok(Math.abs(half.arms[1].hand.y - (a.arms[1].hand.y + b.arms[1].hand.y) / 2) < 1e-9);
  assert.equal(b.arms[-1].hand.y, a.arms[-1].hand.y);              // the other arm rests
  const w = joints('stand', 0, { mix: { to: 'wave', w: 1, wave: 1 } });
  assert.ok(Math.abs(w.arms[1].hand.x - b.arms[1].hand.x - 0.08) < 1e-9);
});

test('figure: every face, blinking and talking, builds without error', () => {
  const f = makeFigure({ hair: 'bun' });
  for (const name of ['dot', 'half', 'wow', 'happy', 'blank', 'angry', 'sad', 'sweat']) {
    f.face(name); f.face(name, { blink: true }); f.face(name, { talk: true });
  }
  f.pose('sit', 1.2, { mix: { to: 'hands-face', w: 0.7 }, breath: 1.01 });
});

test('transitions: a dip is black across the cut, a fade ramps; the swap streak peaks at its time (T068)', () => {
  const TR = { dip_s: [0.117, 0.162], fade_s: [0.259, 0.267], streak_s: 0.15 };
  const a = { dur: 2, trans: 'cut' }, b = { dur: 2, trans: 'dip' }, c = { dur: 2, trans: 'fade' };
  assert.equal(blackAt(a, b, 1.96, TR), 1);              // the end of the scene before a dip
  assert.equal(blackAt(b, null, 0.03, TR), 1);           // the start of the dipped scene
  assert.equal(blackAt(b, null, 0.1, TR), 0);
  assert.equal(blackAt(a, a, 1.99, TR), 0);              // a cut has no black
  assert.ok(blackAt(a, c, 1.95, TR) > 0.5 && blackAt(a, c, 1.95, TR) < 1);
  assert.ok(Math.abs(blackAt(c, null, 0.0, TR) - 1) < 1e-9);
  assert.equal(blackAt(c, null, 0.2, TR), 0);
  assert.equal(streakAt(1.0, 1.0, TR), 1);
  assert.ok(streakAt(1.05, 1.0, TR) > 0 && streakAt(1.05, 1.0, TR) < 1);
  assert.equal(streakAt(1.08, 1.0, TR), 0);
});

test('plan.check: light and swap', () => {
  const S = (extra) => ({ id: 'A', dur: 2, set: 'void', cam: 'close', ...extra });
  check([S({ light: 1 })]);
  assert.throws(() => check([S({ light: 2 })]), /A: light is/);
  check([S({ cast: [{ who: 'hero', act: [[0.5, 'swap']], swap: { hoodie: '#7a5cc0' } }] })]);
  assert.throws(() => check([S({ cast: [{ who: 'hero', swap: { hoodie: '#7a5cc0' } }] })]), /A: swap is/);
});
