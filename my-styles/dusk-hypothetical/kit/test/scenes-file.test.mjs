// specs/026 T026: the scene table as data (scenes.json).
import test from 'node:test';
import assert from 'node:assert/strict';
import { sceneFile, check } from '../plan.js';

const S = (id, extra = {}) => ({ id, dur: 2, set: 'classroom', cam: 'mid-eye', ...extra });

test('scenes.json gives the scene table', () => {
  const doc = { custom: ['platform'], scenes: [S('S01'), S('S02', { set: 'custom:platform' })] };
  const scenes = sceneFile(doc, { platform: () => ({}) });
  assert.equal(scenes.length, 2);
  check(scenes);
});

test('a custom set must be declared and built', () => {
  assert.throws(() => sceneFile({ custom: [], scenes: [S('S02', { set: 'custom:platform' })] }), /S02: custom set "platform" is not declared/);
  assert.throws(() => sceneFile({ custom: ['platform'], scenes: [S('S01')] }, {}), /custom set "platform" in scenes.json has no builder/);
  assert.throws(() => sceneFile({ scenes: 'nope' }), /scenes.json:/);
  sceneFile({ custom: ['platform'], scenes: [S('S01')] });          // the file check alone needs no builders
});
