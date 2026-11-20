// specs/027 T011: over-the-shoulder by default for a two-person talk, the 180° rule, CRAFT rows, old tables unchanged.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { plan, check, withDefaults, craftOf, CATALOG } from '../plan.js';

const two = (id, speaker, extra = {}) => ({
  id, dur: 2, set: 'cafeteria',
  cast: [{ who: 'hero', at: [-0.5, 0], ry: 90 }, { who: 'extra:9', at: [0.5, 0], ry: -90 }],
  gfx: [{ type: 'bubble', text: 'Hi.', who: speaker, at: 0.2 }], ...extra,
});

test('a two-person talk with no cam is over the shoulder at the speaker', () => {
  const p = plan([two('S1', 1)]);
  assert.deepEqual(p.scenes[0].cam, { name: 'ots', subject: 1, side: 1 });   // extra:9 sorts first
  assert.equal(p.CRAFT[0][3].cam, 'ots');
});

test('the next scene of the pair turns round and keeps the side of the line', () => {
  const { scenes } = withDefaults([two('S1', 0), two('S2', 0), two('S3', 1)]);
  assert.equal(scenes[0].cam.subject, 0);
  assert.equal(scenes[1].cam.subject, 1);                                 // same speaker: shows the listener
  assert.equal(scenes[2].cam.subject, 0);                                 // the other talks on: back round
  assert.notEqual(scenes[0].cam.side, scenes[1].cam.side);                // side flips with the subject = same side of the line
  assert.equal(scenes[0].cam.side, scenes[2].cam.side);
});

test('a written cam is kept; no talk and no cam still fails as before', () => {
  assert.equal(withDefaults([two('S1', 0, { cam: 'wide-eye' })]).scenes[0].cam, 'wide-eye');
  const quiet = { id: 'S1', dur: 2, set: 'cafeteria', cast: [{ who: 'hero' }, { who: 'extra:2' }] };
  assert.throws(() => plan([quiet]), /S1: unknown cam "undefined"/);
  assert.throws(() => check([two('S1', 0)]), /unknown cam/);               // check alone has no defaults
});

test('a person outside the room gets a medium shot of both, with a note', () => {
  const info = { cafeteria: { room: { x0: -3, x1: 3, z0: -3, z1: 3 } } };
  const s = two('S1', 0); s.cast[1].at = [5, 0];
  const p = plan([s], [], undefined, null, info);
  assert.deepEqual(p.scenes[0].cam, { name: 'mid-eye', subject: 0 });
  assert.match(p.NOTES[0], /S1: someone stands outside the set's room/);
});

test('CRAFT counts action, items, outdoors and cards (data-model)', () => {
  const S = (id, x) => ({ id, dur: 2, set: 'classroom', cam: 'mid-eye', ...x });
  const c = (x) => craftOf(S('X', x));
  assert.equal(c({ cast: [{ who: 'hero', act: [[0.2, 'nod'], [0.5, 'look:left']] }] }).action, false);
  assert.equal(c({ cast: [{ who: 'hero', act: [[0.2, 'jump']] }] }).action, true);
  assert.equal(c({ cast: [{ who: 'hero', pose: 'run', path: [[0, 0, 0], [1, 1, 0]] }] }).action, true);
  assert.equal(c({ cast: [{ who: 'hero', pose: 'walk', path: [[0, 0, 0], [1, 1, 0]] }] }).action, false);
  assert.equal(c({ cast: [{ who: 'hero', pose: 'hold-phone' }] }).prop, true);
  assert.equal(c({ cast: [{ who: 'hero', item: 'keys' }] }).prop, true);
  assert.equal(c({ cast: [{ who: 'hero', act: [[0.2, 'carry']] }] }).prop, true);
  const g = c({ cast: [{ who: 'hero', act: [[0.2, 'give:cash@1']] }, { who: 'extra:1' }] });
  assert.equal(g.action && g.prop && g.people === 2, true);
  assert.equal(craftOf(S('X', { set: 'street' })).outdoor, true);
  assert.equal(craftOf(S('X', { set: 'custom:roof' }), { 'custom:roof': { outdoor: true } }).outdoor, true);
  assert.equal(craftOf(S('X', { set: 'void', cast: [{ who: 'hero', act: [[0.2, 'jump']] }] })).card, true);
  assert.equal(craftOf(S('X', { set: 'void', cast: [{ who: 'hero', act: [[0.2, 'jump']] }] })).action, false);
  assert.equal(craftOf(S('X', { gfx: [{ type: 'chapter', text: 'ONE' }] })).card, true);
});

test('a partner act needs another person', () => {
  const S = { id: 'S1', dur: 2, set: 'gym', cam: 'mid-eye', cast: [{ who: 'hero', act: [[0.2, 'give:cash@0']] }] };
  assert.throws(() => check([S]), /S1: act "give:cash@0" needs a partner/);
  assert.throws(() => check([{ ...S, cast: [{ who: 'hero', act: [[0.2, 'high-five']] }] }]), /needs a partner/);
  assert.throws(() => check([{ ...S, cast: [{ who: 'hero', item: 'piano' }] }]), /unknown item "piano"/);
});

test('the scene table of films/pause-ten-seconds plans exactly as with its own kit (FR-013 for tables)', async (t) => {
  const dir = path.resolve(import.meta.dirname, '../../../../films/pause-ten-seconds');
  if (!fs.existsSync(path.join(dir, 'kit/plan.js'))) return t.skip('films/pause-ten-seconds is not on this machine');
  const src = fs.readFileSync(path.join(dir, 'index.html'), 'utf8'), a = src.indexOf('const SCENES = '), b = src.indexOf('];', a);
  const scenes = JSON.parse(src.slice(a + 15, b + 1));
  const old = await import(path.join(dir, 'kit/plan.js'));
  const icons = ['eye', 'globe', 'orbit', 'wave', 'stopwatch', 'door', 'frames', 'hourglass'];   // the film adds these
  const was = old.plan(scenes, [], { ...old.CATALOG, icons: [...old.CATALOG.icons, ...icons] });
  const now = plan(scenes, [], { ...CATALOG, icons: [...CATALOG.icons, ...icons] });
  assert.equal(now.SHOTS.length, 175);
  for (const k of ['DUR', 'SHOTS', 'CARDS', 'CAST', 'MOVES']) assert.deepEqual(now[k], was[k], k);
  assert.deepEqual(now.NOTES, []);
});
