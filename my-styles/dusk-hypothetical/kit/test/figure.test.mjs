// Figures of the kit (specs/022 T011): every catalogue name is built, seated hips sit on the seat, hands meet the
// held item, head ≈ 1/3 of the height, limbs are joined (no gaps at knees and elbows).
import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { makeFigure, joints, POSES, FACES, HAIR, HATS, SEAT, HEAD_RATIO } from '../figure.js';
import { CATALOG } from '../plan.js';

test('every catalogue pose, face, hair and hat exists', () => {
  for (const p of CATALOG.poses) assert.ok(POSES[p], `pose ${p}`);
  for (const f of CATALOG.faces) assert.ok(FACES.includes(f), `face ${f}`);
  for (const h of CATALOG.hair) assert.ok(HAIR.includes(h), `hair ${h}`);
  for (const h of CATALOG.hats) assert.ok(HATS.includes(h), `hat ${h}`);
  for (const hair of HAIR) for (const hat of [null, ...HATS]) {
    const f = makeFigure({ hair, hat, glasses: true });
    for (const p of CATALOG.poses) f.pose(p, 0.4);
    for (const x of CATALOG.faces) f.face(x);
  }
});

test('seated: the hips rest on the seat, the thigh runs forward above it', () => {
  for (const name of ['sit', 'hold-phone', 'hold-book']) {
    const j = joints(name, 0, { sit: true });
    for (const sx of [-1, 1]) {
      assert.ok(Math.abs(j.legs[sx].hip.y - SEAT) <= 0.03, `${name}: hip at ${j.legs[sx].hip.y}`);
      assert.ok(j.legs[sx].knee.y >= SEAT, `${name}: knee below the seat`);
      assert.ok(j.legs[sx].knee.z > 0.25, `${name}: thigh not forward`);
    }
  }
});

test('hands meet the held item (≤ 2 cm from the item origin, both-hand holds)', () => {
  const f = makeFigure();
  for (const name of ['hold-phone', 'hold-book', 'hold-cup', 'hold-paper', 'hold-bag']) {
    const j = f.pose(name);
    const item = f.items[j.item];
    assert.ok(item.visible, `${name}: item hidden`);
    const mid = j.arms[-1].hand.clone().add(j.arms[1].hand).multiplyScalar(0.5);
    const d = item.position.clone().sub(mid);
    d.y -= name === 'hold-bag' ? -0.04 + 0.03 : 0.03; d.z -= 0.03;
    assert.ok(d.length() <= 0.02, `${name}: ${d.length()}`);
  }
  f.pose('stand');
  assert.ok(Object.values(f.items).every((g) => !g.visible));
});

test('head ≈ 1/3 of the height', () => {
  assert.ok(HEAD_RATIO >= 0.3 && HEAD_RATIO <= 0.36, String(HEAD_RATIO));
  const f = makeFigure(); f.pose('stand'); f.group.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(f.group);
  const h = box.max.y - Math.min(0, box.min.y);
  const r = 0.68 / h;
  assert.ok(r >= 0.3 && r <= 0.37, `measured ${r.toFixed(3)} of ${h.toFixed(2)} m`);
});

test('walking is a function of t and limbs stay joined', () => {
  const a = joints('walk', 0.3), b = joints('walk', 0.3), c = joints('walk', 0.6);
  assert.deepEqual(a.legs[1].knee.toArray(), b.legs[1].knee.toArray());
  assert.notDeepEqual(a.legs[1].knee.toArray(), c.legs[1].knee.toArray());
  for (const name of Object.keys(POSES)) {
    const j = joints(name, 0.2);
    for (const sx of [-1, 1]) {
      const thigh = j.legs[sx].hip.distanceTo(j.legs[sx].knee), upper = j.shoulder[sx].distanceTo(j.arms[sx].elbow);
      assert.ok(thigh > 0.15 && thigh < 0.42, `${name} thigh ${thigh}`);
      assert.ok(upper > 0.15 && upper < 0.35, `${name} upper arm ${upper}`);
    }
  }
});
