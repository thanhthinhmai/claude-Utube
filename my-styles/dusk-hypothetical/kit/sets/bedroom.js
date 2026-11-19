// Bedroom at dusk: bed, desk with a lamp, a window with the skyline, a shelf grid of books, posters, fairy lights.
import * as THREE from 'three';
import { backpack, box, ceiling, chair, desk, floor, lamp, laptop, mesh, mulberry, plant, poster, stringLights, wall, windows, prop } from './parts.js';

export function build() {
  const g = new THREE.Group(), lights = [];
  floor(g, { w: 7, d: 7, color: '#a07a72', lines: 12, z: -1.5 });
  wall(g, { len: 7, at: -5, color: '#5a4078', band: null });
  wall(g, { len: 7, along: 'z', at: -3.5, from: -1.5, color: '#53406e', band: null });
  wall(g, { len: 7, along: 'z', at: 3.5, from: -1.5, color: '#53406e', band: null });
  ceiling(g, { w: 7, d: 7, y: 3.0, z: -1.5 });
  windows(g, { z: -4.88, n: 1, w: 1.8, h: 1.4, y: 1.8, x0: 0.6 });
  // bed on the left, along z
  box(g, 1.3, 0.45, 2.2, '#6e4e80', -2.6, 0.23, -3.2);
  box(g, 1.25, 0.18, 2.1, '#e0d0e8', -2.6, 0.52, -3.2);
  box(g, 0.9, 0.14, 0.5, '#f4eef8', -2.6, 0.66, -4.0);
  box(g, 1.27, 0.12, 1.2, '#d9608c', -2.6, 0.64, -2.7);
  // desk with a lamp on the right
  desk(g, 2.4, -4.2, { w: 1.4, d: 0.6 }); chair(g, 2.4, -3.5, { ry: Math.PI });
  lamp(g, lights, { x: 2.9, y: 1.25, z: -4.3, r: 0.1, color: '#ffd29a', power: 2.2, range: 5 });
  // shelf grid of books
  const r = mulberry(3), BOOK = ['#c0423e', '#3f9a9a', '#e07a3a', '#7a5cc0', '#c99a2e', '#4f8f4a'];
  for (let row = 0; row < 3; row++) {
    box(g, 1.8, 0.04, 0.3, '#8a6a5a', 1.6, 1.7 + row * 0.38, -4.85);
    for (let i = 0; i < 12; i++) box(g, 0.1, 0.24 + r() * 0.08, 0.22, BOOK[Math.floor(r() * 6)], 0.8 + i * 0.14, 1.85 + row * 0.38, -4.85);
  }
  for (const [x, y, c] of [[-1.2, 2.0, '#3f6fc0'], [-0.6, 2.2, '#c99a2e']]) mesh(g, new THREE.PlaneGeometry(0.5, 0.7), c, [x, y, -4.88], false);
  stringLights(g, { x0: -3.3, x1: 3.3, y: 2.85, z: -4.8, n: 30, sag: 0.3 });
  plant(g, 3.0, -1.0, { h: 0.8 });
  lamp(g, lights, { x: -1.0, y: 2.9, z: -1.5, r: 0.18, color: '#ffe0b8', power: 2.6, range: 7 });
  // story props: posters over the bed, a glowing laptop, a bag on the floor (TEMPLATE.md §6)
  poster(g, -2.6, 1.9, -2.95, { seed: 3 }); poster(g, -1.8, 2.0, -2.95, { seed: 5, w: 0.5, h: 0.7 });
  laptop(g, 2.0, 0.78, -1.9, { ry: -0.3 });
  backpack(g, 0.9, -1.4, { color: '#4f8f4a', ry: 0.4 });
  // specs/027 (FR-008): dressing in all three layers of the default wide shot
  plant(g, 1.9, 0.5, { h: 0.9 }); backpack(g, -1.3, 0.7, { color: '#d9608c', ry: 0.8 });
  poster(g, 1.2, 1.9, -4.88, { seed: 12 }); poster(g, 2.1, 1.7, -4.88, { seed: 13, w: 0.5, h: 0.7 });
  prop(box(g, 0.28, 0.12, 0.2, '#3f6fc0', 2.6, 0.06, -0.4), 'books');
  return {
    group: g, lights, room: { x0: -3.3, x1: 3.3, z0: -4.8, z1: 3.5, y1: 2.85 },
    anchors: { hero: { x: 0, y: 0, z: -1, ry: 0 }, heroSeat: { x: -2.15, z: -2.4, ry: 1.2, seat: 0.61 }, extras: [{ x: 1.0, y: 0, z: -2.2, ry: -0.4 }, { x: -1.2, y: 0, z: -1.6, ry: 0.4 }], crowd: { area: { x0: -2, x1: 2, z0: -3, z1: -1.5 } }, fg: [{ x: 2.4, y: 0.9, z: 1.2 }] },
  };
}
