// Acting schedule of the Sketch Explainer kit (specs/028 T016, FR-011, SC-004).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { schedule, stateAt } from '../../my-styles/sketch-explainer/kit/acting.js';

const two = [{ who: 'narrator', pose: 'rest' }, { who: 'banker', pose: 'palm' }];

test('deterministic for a scene id', () => {
  assert.deepEqual(schedule({ id: 'S001', dur: 6, cast: two }), schedule({ id: 'S001', dur: 6, cast: two }));
});

test('first event right after the cut, then every 2–3 s', () => {
  const ev = schedule({ id: 'S002', dur: 9, cast: two });
  assert.equal(ev[0].t, 0.15);
  for (let i = 1; i < ev.length; i++) { const g = ev[i].t - ev[i - 1].t; assert.ok(g >= 2 && g <= 3, `gap ${g}`); }
});

test('shots of 4 s have an event after the first second; shots of 6 s have two', () => {
  for (let i = 0; i < 200; i++) {
    for (const [d, need] of [[4, 1], [6, 2], [9, 3]]) {
      const ev = schedule({ id: 'Z' + i, dur: d, cast: two }).filter(e => e.t > 1);
      assert.ok(ev.length >= need, `S Z${i} dur ${d}: ${ev.length}`);
    }
  }
});

test('a person holding a sign or seated only changes face or blinks', () => {
  const ev = schedule({ id: 'S003', dur: 12, cast: [{ who: 'auditor', pose: 'hold' }] });
  assert.ok(ev.every(e => e.kind === 'expr' || e.kind === 'blink'));
});

test('a scene without people builds its board', () => {
  const ev = schedule({ id: 'S004', dur: 5, board: { k: 'num' } });
  assert.ok(ev.length >= 2 && ev.every(e => e.kind === 'build'));
});

test('hand-written events come first; the schedule keeps clear of them', () => {
  const ev = schedule({ id: 'S005', dur: 8, cast: two, acts: [[2.5, 'gesture', 0, { pose: 'up' }]] });
  assert.ok(ev.some(e => e.manual && e.t === 2.5));
  assert.ok(ev.filter(e => !e.manual).every(e => Math.abs(e.t - 2.5) >= 0.9));
});

test('state holds the pose between gestures', () => {
  const ev = [{ t: 1, kind: 'gesture', who: 0, dur: 1.25 }, { t: 3.2, kind: 'expr', who: 0, dur: 1.25 }];
  const g = ['rest', 'palm', 'raise'], x = ['neutral', 'happy'];
  assert.equal(stateAt(ev, 0, 0.5, { pose: 'rest' }, g, x).pose, 'rest');
  const s = stateAt(ev, 0, 2.5, { pose: 'rest' }, g, x);
  assert.equal(s.pose, 'palm'); assert.equal(s.poseK, 1);
  assert.equal(stateAt(ev, 0, 4, { pose: 'rest', expr: 'neutral' }, g, x).expr, 'happy');
});
