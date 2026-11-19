// Camera placements (specs/022 T015): every catalogue cam exists; the camera stays inside a set's room.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from 'three';
import { CAMS, place, inside } from '../camera.js';
import { CATALOG } from '../plan.js';

test('every catalogue cam has a placement', () => {
  for (const c of Object.keys(CATALOG.cams)) assert.ok(CAMS[c], c);
});

test('the camera stays inside the room and the lens widens', () => {
  const room = { x0: -5, x1: 5, z0: -10, z1: 3, y1: 3 };
  const cam = new THREE.PerspectiveCamera(50, 16 / 9, 0.05, 100);
  const head = new THREE.Vector3(0, 1.57, 0);
  for (const name of Object.keys(CAMS)) {
    place(cam, name, head, 0, {}, 0, room);
    const p = cam.position;
    assert.ok(p.x >= room.x0 && p.x <= room.x1 && p.z >= room.z0 && p.z <= room.z1 && p.y <= room.y1, `${name} at ${p.toArray().map((v) => v.toFixed(2))}`);
  }
  place(cam, 'very-wide', head, 0, {}, 0, room);
  assert.ok(cam.fov > CAMS['very-wide'].fov, 'lens not widened');
  assert.equal(inside(room, new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 1, 2)), 1);
});
