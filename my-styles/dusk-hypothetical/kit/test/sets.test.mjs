// specs/027 T022: every set has its dressing in the three layers of the default wide shot (FR-008), outdoor sets have
// a sky and self-lit lights, the catalogue and the set modules agree.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { SETS } from '../sets/index.js';
import { countProps } from '../sets/parts.js';
import { CATALOG } from '../plan.js';

test('every catalogue set has a builder and set_info', () => {
  for (const name of CATALOG.sets) {
    assert.ok(SETS[name] && SETS[name].build, `${name} builder`);
    assert.ok(CATALOG.set_info[name], `${name} set_info`);
  }
  assert.ok(CATALOG.sets.filter((n) => CATALOG.set_info[n].outdoor).length >= 6);   // 4 new + street, stadium (FR-007)
});

test('props_min holds for every set: total, kinds and each layer', () => {
  for (const name of CATALOG.sets) {
    const min = CATALOG.set_info[name].props_min;
    if (!min) continue;
    const s = SETS[name].build({ THREE }), c = countProps(s.group, s.anchors.hero);
    assert.ok(c.total >= min.total, `${name}: ${c.total} props < ${min.total}`);
    assert.ok(Object.keys(c.kinds).length >= min.kinds, `${name}: ${Object.keys(c.kinds).length} kinds < ${min.kinds}`);
    for (const layer of ['fore', 'mid', 'back']) assert.ok(c[layer] >= min.layer, `${name}: ${layer} layer has ${c[layer]}`);
  }
});

test('outdoor sets: a sky, self-lit lights, info for the plan', () => {
  for (const name of ['court', 'rooftop', 'parking', 'street-dusk']) {
    const s = SETS[name].build({ THREE });
    assert.ok(s.group.getObjectByName('sky'), `${name} sky`);
    let glow = 0;
    s.group.traverse((o) => { if (o.material && o.material.emissive && o.material.emissiveIntensity > 0.5 && o.material.emissive.getHex() !== 0) glow++; });
    assert.ok(glow >= 2, `${name}: ${glow} self-lit objects`);
    assert.equal(SETS[name].info.outdoor, true);
    assert.deepEqual(SETS[name].info.room, s.room);
    assert.equal(CATALOG.set_info[name].outdoor, true);
  }
});
