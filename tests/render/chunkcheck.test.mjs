// Tests for tools/render/chunkcheck.mjs (specs/020 T036): log parsing, joining stills across chunk edges, shots.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseLog, combine, shotAt } from '../../tools/render/chunkcheck.mjs';

const SHOTS = [[0, 12, 'a', 'S1'], [12, 20, 'b', 'S2'], [20, 30, 'c', 'S3']];
const O = { stillMax: 6, shots: SHOTS, exceptions: [], dur: 30, fps: 10 };
const ch = (c, t0, t1, black = [], stills = []) => ({ c, t0, t1, res: { black, stills } });

test('ffmpeg log: black and freeze stretches, an open freeze runs to the end', () => {
  const log = '[blackdetect @ 0x1] black_start:2.5 black_end:3 black_duration:0.5\n' +
    '[freezedetect @ 0x2] lavfi.freezedetect.freeze_start: 1.2\n[freezedetect] lavfi.freezedetect.freeze_duration: 2\n' +
    '[freezedetect] lavfi.freezedetect.freeze_end: 3.2\n[freezedetect] lavfi.freezedetect.freeze_start: 8.5\n';
  assert.deepEqual(parseLog(log, 10), { black: [[2.5, 3]], stills: [[1.2, 3.2], [8.5, 10]] });
});

test('a still across two chunks is joined, even when the chunks were checked out of order', () => {
  const later = ch(1, 10, 20, [], [[2, 10]]);                   // 8 s inside one chunk: reported at once
  assert.deepEqual(combine([later], O), [{ chunk: 1, shot: 'S2', at: 12, rule: 'still', measure: 8, limit: 6 }]);
  const a = ch(0, 0, 10, [], [[6, 10]]), b = ch(1, 10, 20, [], [[0, 3]]);
  assert.deepEqual(combine([b], O), []);                       // 3 s so far
  const got = combine([b, a], O);
  assert.equal(got.length, 1);
  assert.deepEqual(got[0], { chunk: 0, shot: 'S1', at: 6, rule: 'still', measure: 7, limit: 6 });
});

test('no join across a shot cut or a missing chunk', () => {
  const a = ch(1, 10, 20, [], [[0, 10]]), b = ch(2, 20, 30, [], [[0, 4]]);   // cut at 20 s: 10 s (S2 part) and 4 s
  const got = combine([a, b], O);
  assert.deepEqual(got.map(x => [x.shot, x.measure]), [['S1', 10]]);
  const c = ch(0, 0, 10, [], [[5, 10]]), d = ch(2, 20, 30, [], [[0, 5]]);
  assert.deepEqual(combine([c, d], { ...O, shots: [[0, 30, 'x', 'ALL']] }), []);
});

test('the still limit and exceptions', () => {
  const a = ch(0, 0, 10, [], [[1, 8]]);
  assert.equal(combine([a], O).length, 1);
  assert.equal(combine([a], { ...O, stillMax: 8 }).length, 0);
  assert.equal(combine([a], { ...O, exceptions: [{ shot: 'S1', rule: 'still' }] }).length, 0);
  assert.equal(combine([a], { ...O, exceptions: [{ shot: 'S1', rule: 'flat' }] }).length, 1);
});

test('black frames: reported in the middle, not at the film edges', () => {
  const a = ch(0, 0, 10, [[0, 0.4], [4, 4.5]]), z = ch(2, 20, 30, [[9.6, 10]]);
  assert.deepEqual(combine([a, z], O), [{ chunk: 0, shot: 'S1', at: 4, rule: 'black_frames', measure: 0.5, limit: 0.25 }]);
});

test('shotAt', () => {
  assert.equal(shotAt(SHOTS, 12), 'S2');
  assert.equal(shotAt(SHOTS, 29.99), 'S3');
  assert.equal(shotAt([], 3), '');
});
