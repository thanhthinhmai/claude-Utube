// Pure part of the film kit (specs/022 T006): scene table → SHOTS/CARDS, every rule fails with the scene id.
import test from 'node:test';
import assert from 'node:assert/strict';
import { plan, check, sceneAt, cardsOf, CATALOG } from '../plan.js';

const S = (id, extra = {}) => ({ id, dur: 2, set: 'classroom', cam: 'mid-eye', ...extra });

test('SHOTS are contiguous from 0 to DUR', () => {
  const p = plan([S('S001', { dur: 1.8 }), S('S002', { dur: 2.4, set: 'gym' }), S('S003', { dur: 3.1, cam: { name: 'ots', yaw: 10 } })]);
  assert.equal(p.DUR, 7.3);
  assert.deepEqual(p.SHOTS[0], [0, 1.8, 'classroom', 'S001']);
  for (let i = 1; i < p.SHOTS.length; i++) assert.equal(p.SHOTS[i][0], p.SHOTS[i - 1][1]);
  assert.equal(p.SHOTS.at(-1)[1], p.DUR);
});

test('CARDS come from every graphic with text, at scene time', () => {
  const p = plan([S('S001'), S('S002', { gfx: [{ type: 'counter', prefix: '$', from: 0, to: 20, at: 0.3 }, { type: 'title', text: 'WHAT IF', sub: 'YOU NEVER SLEPT', at: 0.5, until: 1.8 }] })]);
  assert.deepEqual(p.CARDS, [[2.3, 4, 'S002.counter', '$20'], [2.5, 3.8, 'S002.title.1', 'WHAT IF · YOU NEVER SLEPT']]);
  assert.deepEqual(cardsOf(S('X', { gfx: [{ type: 'bubble', text: 'No way?' }] }), 10), [[10, 12, 'X.bubble', 'No way?']]);
});

test('CUES are clipped to the film', () => {
  const p = plan([S('S001')], [[0, 1, 'one'], [1.5, 3, 'two'], [5, 6, 'gone']]);
  assert.deepEqual(p.CUES, [[0, 1, 'one'], [1.5, 3, 'two']]);
  assert.deepEqual(plan([S('S001')], [{ t0: 0.2, t1: 1, text: 'obj' }]).CUES, [[0.2, 1, 'obj']]);
});

const bad = (scenes, re) => assert.throws(() => check(scenes), re);
test('each rule fails with the scene id', () => {
  bad([S('S001'), S('S001')], /S001: duplicate id/);
  bad([S('S002', { dur: 0.8 })], /S002: dur 0.8 outside/);
  bad([S('S003', { dur: 7 })], /S003: dur 7 outside/);
  bad([S('S004', { set: 'moon' })], /S004: unknown set "moon"/);
  check([S('S005', { set: 'custom:train-car' })]);
  bad([S('S006', { cam: 'dutch' })], /S006: unknown cam "dutch"/);
  bad([S('S007', { cast: [{ who: 'hero', pose: 'hold-lamp' }] })], /S007: unknown pose "hold-lamp"/);
  bad([S('S008', { cast: [{ who: 'hero', face: 'smirk' }] })], /S008: unknown face/);
  bad([S('S009', { cast: [{ who: 'villain' }] })], /S009: unknown cast/);
  bad([S('S010', { crowd: { n: 6000 } })], /S010: crowd.n/);
  bad([S('S011', { gfx: [{ type: 'confetti' }] })], /S011: unknown gfx/);
  bad([S('S012', { gfx: [{ type: 'stat', text: 'ONE IN TEN', at: 1, until: 2.5 }] })], /S012: gfx "stat" outside the scene/);
  bad([S('S013', { gfx: [{ type: 'chapter', text: 'Level two' }] })], /S013: gfx "chapter" text must be caps/);
  bad([S('S014', { mood: 'sepia' })], /S014: unknown mood/);
  bad([S('S015', { grade: { exposure: 1.2 } })], /S015: grade.exposure/);
  bad([S('S016', { grade: { saturation: 0.5 } })], /S016: grade.saturation/);
  bad([S('A', { fade: 'out' }), S('B', { fade: 'in' }), S('C', { fade: 'out' })], /C: more than 2 fades/);
  bad([S('S017', { cast: [{ who: 'hero', hat: 'crown' }] })], /S017: unknown hat/);
});

test('sceneAt at the edges', () => {
  const { scenes } = plan([S('A', { dur: 1.5 }), S('B'), S('C', { dur: 3 })]);
  assert.equal(sceneAt(scenes, 0).id, 'A');
  assert.equal(sceneAt(scenes, 1.499).id, 'A');
  assert.equal(sceneAt(scenes, 1.5).id, 'B');
  assert.equal(sceneAt(scenes, 3.5).id, 'C');
  assert.equal(sceneAt(scenes, 6.5).id, 'C');
  assert.equal(sceneAt(scenes, 99).id, 'C');
});

test('catalogue: 8+ sets, every shot label of shots.json has a cam', async () => {
  assert.ok(CATALOG.sets.length >= 8);
  const { readFile } = await import('node:fs/promises');
  const shots = JSON.parse(await readFile(new URL('../../shots.json', import.meta.url)));
  const cams = Object.values(CATALOG.cams);
  for (const s of Object.keys(shots.scale_share)) assert.ok(cams.some((c) => c.scale === s), `no cam for scale ${s}`);
  for (const a of Object.keys(shots.angle_share)) assert.ok(cams.some((c) => c.angle === a), `no cam for angle ${a}`);
});
