// School gym: wooden court with lines, stepped bleachers full of seats at the back, hoops, high lamps.
import * as THREE from 'three';
import { ball, box, canvasTex, ceiling, floor, lamp, litBoard, mat, mesh, pennants, stdMat, bench, backpack, cyl, prop } from './parts.js';

export function build() {
  const g = new THREE.Group(), lights = [], seats = [];
  const court = canvasTex('court', 512, 512, (c, W, H) => {
    c.fillStyle = '#fff'; c.fillRect(0, 0, W, H); c.strokeStyle = 'rgba(255,240,220,.9)'; c.lineWidth = 6;
    c.strokeRect(30, 30, W - 60, H - 60); c.beginPath(); c.moveTo(30, H / 2); c.lineTo(W - 30, H / 2); c.stroke();
    c.beginPath(); c.arc(W / 2, H / 2, 60, 0, 7); c.stroke();
    c.fillStyle = 'rgba(80,40,40,.18)'; for (let i = 0; i < 32; i++) c.fillRect(0, i * 16, W, 2);
  });
  mesh(g, new THREE.BoxGeometry(24, 0.1, 30), stdMat('#b0663a', { map: court, rough: 0.7 }), [0, -0.05, -6]);   // warm orange wood (v04 shot cell #7)
  for (const sx of [-1, 1]) box(g, 0.2, 9, 30, '#4d3b66', sx * 12, 4.5, -6);
  box(g, 24, 9, 0.2, '#4d3b66', 0, 4.5, -21);
  ceiling(g, { w: 24, d: 30, y: 9, z: -6 });
  // bleachers: 9 stepped rows at the back
  for (let row = 0; row < 9; row++) {
    const y = 0.45 * row, z = -13 - row * 0.8;
    box(g, 22, 0.45, 0.8, row % 2 ? '#7a5a8a' : '#6e4e80', 0, y + 0.22, z);
    box(g, 22, 0.08, 0.42, '#c89a6e', 0, y + 0.45 + 0.04, z + 0.15);
    for (let i = 0; i < 40; i++) seats.push({ x: -10.5 + i * 0.54, y: y + 0.45 - 0.6 + 0.08, z: z + 0.15, ry: 0, sit: true });
  }
  for (const z of [7, -19]) {                                  // hoops
    box(g, 1.8, 1.1, 0.06, '#f0e6d8', 0, 3.4, z); mesh(g, new THREE.TorusGeometry(0.23, 0.02, 6, 20), '#e07a3a', [0, 3.05, z + (z > 0 ? -0.3 : 0.3)]).rotation.x = Math.PI / 2;
  }
  for (const x of [-8, -3, 3, 8]) for (const z of [-2, -12]) lamp(g, lights, { x, y: 8.2, z, r: 0.3, color: '#ffe6c0', power: x === -3 || x === 3 ? 1.6 : z === -12 ? 1.2 : 0, range: 12 });
  // a side hoop on the left wall, in the frame of a wide shot toward the bleachers (v04 shot cell #7)
  const side = new THREE.Group(); side.position.set(-11.85, 0, -7); side.rotation.y = Math.PI / 2; g.add(side);
  box(side, 1.8, 1.1, 0.06, '#f0e6d8', 0, 3.4, 0.05);
  mesh(side, new THREE.TorusGeometry(0.23, 0.02, 6, 20), '#e07a3a', [0, 3.05, 0.4]).rotation.x = Math.PI / 2;
  box(g, 5, 1.4, 0.1, '#2a1e40', 0, 7, -20.8);
  mesh(g, new THREE.PlaneGeometry(4.6, 1.1), mat('#1c1626', 0.5, '#d9608c', 0.25), [0, 7, -20.7], false);
  // story props: a ball rack, a lit scoreboard, pennants over the bleachers (TEMPLATE.md §6)
  for (let i = 0; i < 6; i++) ball(g, -5.4 + (i % 3) * 0.26, 0.14 + Math.floor(i / 3) * 0.26, -1.5, { color: i % 2 ? '#e07a3a' : '#d9b23a' });
  litBoard(g, 0, 4.2, -11.9, { w: 2.4, h: 0.9, glow: '#ff9e70', rows: 2 });
  pennants(g, { x0: -8, x1: 8, y: 4.6, z: -11.6, n: 18 });
  // specs/027 (FR-008): dressing in all three layers of the default wide shot
  bench(g, -4.2, 2.6, { ry: 0.3 }); backpack(g, -3.7, 2.9, { color: '#c0423e', ry: 0.5 });
  for (const [x, z] of [[2.6, 2.2], [3.3, 2.7]]) prop(cyl(g, 0.12, 0.42, '#e07a3a', x, 0.21, z, 10), 'cone');
  prop(cyl(g, 0.18, 0.9, '#3f6fc0', 9.5, 0.45, -3, 14), 'cooler');
  return {
    group: g, lights, room: { x0: -11.7, x1: 11.7, z0: -20.7, z1: 10, y1: 8.7 }, fog: [12, 40], grade: { exposure: 0.62, saturation: 0.95 },
    anchors: { hero: { x: 0, y: 0, z: 0, ry: 0 }, heroSeat: { x: 0, z: -12.85, ry: 0, y: -0.6 + 0.53 }, extras: [{ x: -1.2, y: 0, z: -1, ry: 0.4 }, { x: 1.3, y: 0, z: -1.2, ry: -0.4 }, { x: -2.4, y: 0, z: -2.5, ry: 0.3 }, { x: 2.6, y: 0, z: -2.8, ry: -0.3 }], crowd: { slots: seats }, fg: [] },
  };
}
