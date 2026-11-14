// Classroom at dusk: a grid of desks and chairs, window band on the back wall, light strips, a board on the side.
import * as THREE from 'three';
import { floor, wall, ceiling, lightStrip, windows, grid, desk, chair, box, plant, lamp } from './parts.js';

export function build() {
  const g = new THREE.Group(), lights = [], seats = [];
  floor(g, { w: 14, d: 16, color: '#9c7068', lines: 18, z: -3 });
  wall(g, { len: 14, at: -10, color: '#4d3b66' });
  wall(g, { len: 16, along: 'z', at: -7, from: -3 }); wall(g, { len: 16, along: 'z', at: 7, from: -3 });
  ceiling(g, { w: 14, d: 16, z: -3 });
  windows(g, { z: -9.88, n: 5, gap: 2.5, y: 2.0, h: 1.6 });
  for (const x of [-3, 0, 3]) lightStrip(g, lights, { x, z: -4, len: 11, along: 'z', every: 5.5 });
  box(g, 3.6, 1.3, 0.06, '#2f4a3e', 6.88, 1.8, -3).rotation.y = -Math.PI / 2;   // board on the side wall
  // desks: 5 across, 5 deep; the hero's desk is front centre
  grid(g, { nx: 5, nz: 5, dx: 1.5, dz: 1.55, x0: 0, z0: 0, make: (gg, x, z, i, j) => {
    desk(gg, x, z + 0.45, { w: 0.9, d: 0.55 });
    chair(gg, x, z, { color: '#a8745e' });
    if (!(i === 2 && j === 0)) seats.push({ x, y: 0, z: z + 0.05, ry: 0, sit: true });
  } });
  plant(g, -6.2, -9); plant(g, 6.2, -9);
  lamp(g, lights, { x: 5.6, y: 2.2, z: -9.6, r: 0.14, power: 1.2 });
  seats.sort((a, b) => Math.hypot(a.x, a.z) - Math.hypot(b.x, b.z));
  return {
    group: g, lights, room: { x0: -6.8, x1: 6.8, z0: -9.7, z1: 8, y1: 3.15 },
    anchors: { hero: { x: 0, y: 0, z: 0.9, ry: 0 }, heroSeat: { x: 0, z: 0.05, ry: 0 }, extras: seats.slice(0, 8), crowd: { slots: seats }, fg: [{ x: -0.9, y: 0.9, z: 1.6 }] },
  };
}
