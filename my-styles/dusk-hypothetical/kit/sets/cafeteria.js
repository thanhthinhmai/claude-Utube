// School cafeteria: rows of long tables with benches, a lit serving counter, windows at the back, hanging lamps.
import * as THREE from 'three';
import { bench, box, ceiling, floor, grid, lamp, litBoard, mat, mesh, pennants, table, tray, wall, windows } from './parts.js';

export function build() {
  const g = new THREE.Group(), lights = [], seats = [];
  floor(g, { w: 18, d: 20, color: '#a88a80', lines: 22, tile: true, z: -6 });
  wall(g, { len: 18, at: -15 }); wall(g, { len: 20, along: 'z', at: -9, from: -6 }); wall(g, { len: 20, along: 'z', at: 9, from: -6 });
  ceiling(g, { w: 18, d: 20, y: 3.6, z: -6 });
  windows(g, { z: -14.88, n: 6, gap: 2.6, y: 2.2, h: 1.6 });
  grid(g, { nx: 3, nz: 4, dx: 5, dz: 2.8, z0: -1, make: (gg, x, z, i, j) => {
    table(gg, x, z, { w: 3.6, d: 0.85 });
    for (const sz of [-1, 1]) {
      bench(gg, x, z + sz * 0.75, { len: 3.4 });
      for (let k = 0; k < 6; k++) seats.push({ x: x - 1.4 + k * 0.56, y: 0, z: z + sz * 0.75, ry: sz > 0 ? Math.PI : 0, sit: true });
    }
  } });
  // serving counter on the right wall, lit
  box(g, 0.9, 1.0, 8, '#8a6a8a', 8.2, 0.5, -8);
  mesh(g, new THREE.BoxGeometry(0.6, 0.06, 7.6), mat('#e8d9f0', 0.4, '#ffe0b8', 0.5), [8.2, 1.4, -8], false);
  for (let i = 0; i < 6; i++) box(g, 0.35, 0.18, 0.5, ['#e07a3a', '#4f8f4a', '#c99a2e'][i % 3], 8.2, 1.1, -11 + i * 1.2);
  for (const x of [-5, 0, 5]) for (const z of [-1, -6.6]) lamp(g, lights, { x, y: 3.0, z, r: 0.22, color: '#ffd8a8', power: 2.2, range: 7 });
  seats.sort((a, b) => Math.hypot(a.x, a.z + 0.25) - Math.hypot(b.x, b.z + 0.25));
  const hero = seats.splice(seats.findIndex((s) => s.ry === 0), 1)[0];   // the hero's seat: nearest bench facing the camera
  // story props: trays of food on the tables, a lit menu over the counter, pennants (TEMPLATE.md §6)
  [[-2.2, -2.0], [0.4, -2.0], [2.6, -3.6], [-1.0, -5.2], [1.8, -5.2], [-3.0, -3.6]].forEach(([x, z], i) => tray(g, x, 0.86, z, { seed: i + 1 }));
  litBoard(g, 6.85, 2.5, -4, { w: 2.6, h: 0.8, ry: -Math.PI / 2, glow: '#ffd8a8' });
  pennants(g, { x0: -6, x1: 6, y: 3.0, z: -1.2, n: 16 });
  return {
    group: g, lights, room: { x0: -8.7, x1: 8.7, z0: -14.7, z1: 5, y1: 3.4 }, fog: [10, 30],
    anchors: { hero: { x: 0, y: 0, z: 1.2, ry: 0 }, heroSeat: { x: hero.x, z: hero.z, ry: hero.ry }, extras: seats.slice(0, 8), crowd: { slots: seats }, fg: [{ x: 1.2, y: 0.9, z: 2.2 }] },
  };
}
