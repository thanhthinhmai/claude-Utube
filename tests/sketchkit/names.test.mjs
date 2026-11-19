// Names in a scene table are checked against the kit's catalogue (specs/028 T008, FR-002, FR-004).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { checkScene, nearest, CATALOG } from '../../my-styles/sketch-explainer/kit/film.js';

const ok = { id: 'S001', dur: 3, set: 'office', cast: [{ who: 'narrator', x: 600, pose: 'palm', expr: 'happy' }, { who: 'extra:3', x: 900 }], board: { k: 'num', text: '$5' }, props: [['vault', 900, 600, 1, 0]] };

test('a scene with names from the catalogue has no error', () => {
  assert.deepEqual(checkScene(ok), []);
});

test('each wrong name gives its kind, the shot and the nearest name', () => {
  const bad = { id: 'S014', dur: 3, set: 'ofice', cast: [{ who: 'bankr', pose: 'hold-lamp', expr: 'hapy' }], props: [['vaultt', 0, 0, 1]], board: { k: 'barz' }, cam: { size: 'mid', move: 'zoom' } };
  const e = checkScene(bad);
  const by = Object.fromEntries(e.map(x => [x.kind, x]));
  assert.equal(by.unknown_set.hint, 'office');
  assert.equal(by.unknown_role.hint, 'banker');
  assert.equal(by.unknown_expr.hint, 'happy');
  assert.equal(by.unknown_prop.hint, 'vault');
  assert.equal(by.unknown_board.hint, 'bars');
  assert.equal(by.unknown_cam.hint, 'med');
  assert.ok(by.unknown_pose);
  assert.ok(e.every(x => x.shot === 'S014'));
});

test('a real person must have been copied into the film', () => {
  const sc = { id: 'S002', dur: 3, set: 'stage', cast: [{ who: 'person:some-one' }] };
  assert.equal(checkScene(sc, CATALOG, [])[0].kind, 'unknown_person');
  assert.deepEqual(checkScene(sc, CATALOG, ['some-one']), []);
});

test('custom sets name parts of the kit', () => {
  assert.deepEqual(checkScene({ id: 'S3', dur: 2, set: 'custom:roof', custom: [['sky', {}], ['skyline', {}]] }), []);
  assert.equal(checkScene({ id: 'S3', dur: 2, set: 'custom:roof', custom: [['skye', {}]] })[0].hint, 'sky');
});

test('bubbles and signs point at someone in the cast', () => {
  const e = checkScene({ id: 'S4', dur: 2, set: 'office', cast: [{ who: 'narrator' }], bub: [[3, '!', 1]], sign: { who: 2, text: 'x' } });
  assert.equal(e.filter(x => x.kind === 'bad_value').length, 2);
});

test('cards need no set', () => {
  assert.deepEqual(checkScene({ id: 'S5', dur: 2.6, card: { big: 'Chapter one' } }), []);
});

test('nearest picks the closest name', () => { assert.equal(nearest('whitebord-room', CATALOG.sets), 'whiteboard-room'); });

test('catalog.json is up to date with the code', () => {
  const kit = new URL('../../my-styles/sketch-explainer/kit/', import.meta.url);
  const fresh = execFileSync(process.execPath, [new URL('tools/catalog.mjs', kit).pathname], { encoding: 'utf8' });
  assert.deepEqual(JSON.parse(readFileSync(new URL('catalog.json', kit), 'utf8')), JSON.parse(fresh), 'run tools/catalog.mjs > catalog.json');
});
