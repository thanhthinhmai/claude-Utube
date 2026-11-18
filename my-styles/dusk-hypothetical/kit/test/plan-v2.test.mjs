// specs/023 T036: the kit v2 scene fields (act, talk, path, blink, move, frame, trans, icon), CAST, MOVES, auto moves.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { plan, check, moveOf, actOk } from '../plan.js';

const S = (id, extra = {}) => ({ id, dur: 3, set: 'classroom', cam: 'close', ...extra });
const H = (extra = {}) => ({ who: 'hero', pose: 'sit', face: 'half', ...extra });
const bad = (scenes, re) => assert.throws(() => check(scenes), re);
const TPL = JSON.parse(fs.readFileSync(new URL('../../template.json', import.meta.url)));

test('acts: catalogue names and prefixed names', () => {
  assert.ok(actOk('raise-hand') && actOk('face:wow') && actOk('pose:cheer') && actOk('look:camera'));
  assert.ok(!actOk('face:grin') && !actOk('fly') && !actOk('look:behind'));
  check([S('A', { cast: [H({ act: [[0.3, 'raise-hand'], [1.2, 'face:wow']], talk: [[0.2, 1.1]], blink: { every: [2, 5] } })] })]);
  bad([S('A', { cast: [H({ act: [[3.2, 'nod']] })] })], /A: act time 3.2 outside/);
  bad([S('A', { cast: [H({ act: [[1, 'fly']] })] })], /A: unknown act "fly"/);
  bad([S('A', { cast: [H({ talk: [[1, 4]] })] })], /A: talk is/);
  bad([S('A', { cast: [H({ blink: { every: [5, 2] } })] })], /A: blink is/);
});

test('path only with a walk, in time order', () => {
  check([S('A', { cast: [H({ pose: 'walk', path: [[0, -2, 0], [3, 1.5, 0]] })] })]);
  bad([S('A', { cast: [H({ path: [[0, 0, 0], [1, 1, 0]] })] })], /A: path needs pose "walk"/);
  bad([S('A', { cast: [H({ pose: 'walk', path: [[1, 0, 0], [0.5, 1, 0]] })] })], /A: path is/);
});

test('move, frame, trans, icon', () => {
  check([S('A', { move: 'auto', frame: 'auto', trans: 'cut' }), S('B', { move: { type: 'push', speed: 2.5 }, frame: { x: 0.4, y: 0.5 } }),
         S('C', { move: 'still', gfx: [{ type: 'stat', text: '16,000 WORDS', icon: 'speech-stack' }] })]);
  bad([S('A', { move: 'whip' })], /A: unknown move "whip"/);
  bad([S('A', { move: { type: 'push', speed: 0 } })], /A: move.speed/);
  bad([S('A', { frame: { x: 1.2, y: 0.5 } })], /A: frame is/);
  bad([S('A', { trans: 'wipe' })], /A: unknown trans "wipe"/);
  bad([S('A', { gfx: [{ type: 'stat', text: 'X', icon: 'rocket' }] })], /A: unknown icon "rocket"/);
  bad([S('A', { trans: 'fade' }), S('B', { fade: 'out' }), S('C', { trans: 'fade' })], /C: more than 2 fades/);
});

test('CAST and MOVES rows', () => {
  const p = plan([S('A', { cast: [H({ act: [[0.3, 'nod']] }), { who: 'extra:3', pose: 'stand' }], crowd: { n: 40 } }),
                  S('B', { cam: 'insert', move: 'still' })], [], undefined, TPL);
  assert.deepEqual(p.CAST, [[0, 3, 'A', 2], [3, 6, 'B', 0]]);          // the crowd is not cast
  assert.equal(p.MOVES[0][4], 1);
  assert.deepEqual(p.MOVES[1].slice(2, 4), ['B', 'still']);
});

test('auto moves follow the style: same table, same moves; shares near the measured ones', () => {
  const scenes = Array.from({ length: 400 }, (_, i) => S(`S${i}`, { cam: 'close' }));
  const a = scenes.map((s) => moveOf(s, TPL)), b = scenes.map((s) => moveOf(s, TPL));
  assert.deepEqual(a, b);
  const want = TPL.motion.cam_by_scale.cu;
  const moving = a.filter((m) => m.type !== 'still').length / a.length;
  const push = a.filter((m) => m.type === 'push').length / a.length;
  assert.ok(Math.abs(moving - want.moving) < 0.07, `moving ${moving} vs ${want.moving}`);
  assert.ok(Math.abs(push - want.push) < 0.07, `push ${push} vs ${want.push}`);
  for (const m of a.filter((m) => m.type === 'push')) {
    assert.ok(m.speed >= want.zoom_pct_s[0] && m.speed <= want.zoom_pct_s[1]);
    assert.ok(Math.abs(m.drift) >= want.drift_px_s[0] * 0.5 - 1e-9 && Math.abs(m.drift) <= want.drift_px_s[0] + 1e-9, `drift ${m.drift}`);   // T065
  }
  assert.deepEqual(moveOf(S('X'), null), { type: 'still', speed: null });  // no template: still
});

test('a 022 scene table still plans', () => {
  const p = plan([S('A', { cam: 'mid-eye', cast: [{ who: 'hero', pose: 'stand', face: 'dot' }], gfx: [{ type: 'counter', from: 0, to: 9 }] })]);
  assert.equal(p.DUR, 3);
  assert.equal(p.MOVES[0][3], 'still');
});
