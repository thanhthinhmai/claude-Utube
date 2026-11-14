// Empty violet backdrop for inserts and cards: a seamless floor-to-wall sweep, a soft spot, a stool.
import * as THREE from 'three';
import { mesh, mat, box, cyl } from './parts.js';

export function build() {
  const g = new THREE.Group(), lights = [];
  mesh(g, new THREE.CylinderGeometry(14, 14, 12, 48, 1, true, Math.PI * 0.75, Math.PI * 1.5), mat('#3a2a5a', 0.95, '#2a1e44', 0.6), [0, 6, -2], false).material.side = THREE.BackSide;
  mesh(g, new THREE.CircleGeometry(14, 48), mat('#45326a', 0.9, '#2a1e44', 0.4), [0, 0, -2]).rotation.x = -Math.PI / 2;
  const spot = new THREE.SpotLight('#ffd8c8', 30, 14, 0.45, 0.6, 1.2); spot.position.set(0, 7, 2); spot.target.position.set(0, 0.8, 0); g.add(spot, spot.target); lights.push(spot);
  box(g, 0.45, 0.04, 0.45, '#a8745e', 1.4, 0.58, -0.6); cyl(g, 0.04, 0.56, '#3a2e48', 1.4, 0.28, -0.6, 8);
  return {
    group: g, lights, room: { x0: -11, x1: 11, z0: -13, z1: 10 },
    anchors: { hero: { x: 0, y: 0, z: 0, ry: 0 }, heroSeat: { x: 1.4, z: -0.6, ry: -0.3 }, extras: [{ x: -1.2, y: 0, z: -0.6, ry: 0.4 }, { x: 1.3, y: 0, z: -0.7, ry: -0.4 }, { x: -2.4, y: 0, z: -1.4, ry: 0.4 }, { x: 2.5, y: 0, z: -1.5, ry: -0.4 }], crowd: { area: { x0: -6, x1: 6, z0: -8, z1: -2 } }, fg: [] },
  };
}
