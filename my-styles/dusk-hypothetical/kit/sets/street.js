// Dusk street: a road receding to a skyline, sidewalks, buildings with lit window grids, street lamps, string lights.
import * as THREE from 'three';
import { box, canvasTex, car, duskSky, floor, foodCart, lamp, litBoard, mesh, mulberry, plant, stdMat, stringLights, tree, cyl, prop } from './parts.js';

export function build() {
  const g = new THREE.Group(), lights = [], spots = [];
  floor(g, { w: 7, d: 70, color: '#6a5070', lines: 2, z: -30 });                       // road
  for (const sx of [-1, 1]) floor(g, { w: 3, d: 70, color: '#a08088', lines: 30, tile: true, x: sx * 5, z: -30, y: 0.12 });
  const r = mulberry(11);
  const win = canvasTex('street-win', 64, 128, (c, W, H) => {
    c.fillStyle = '#fff'; c.fillRect(0, 0, W, H);
    for (let y = 6; y < H - 6; y += 14) for (let x = 5; x < W - 5; x += 12) { c.fillStyle = r() < 0.3 ? '#ffd29a' : '#5a4878'; c.fillRect(x, y, 7, 9); }
  });
  const COL = ['#5a4874', '#6e4e80', '#4d3b66', '#7a5a7a', '#5e4a6e'];
  for (const sx of [-1, 1]) for (let i = 0; i < 14; i++) {
    const w = 3 + r() * 2.5, h = 5 + r() * 9, z = 2 - i * 4.6 - r();
    const m = stdMat(COL[i % 5], { map: win ? Object.assign(win.clone(), { needsUpdate: true }) : null, rough: 0.9, emissive: '#2a1a30', ei: 0.3 });
    if (m.map) m.map.repeat.set(Math.round(w / 1.5), Math.round(h / 2.2));
    mesh(g, new THREE.BoxGeometry(4, h, w), m, [sx * (6.5 + 2 + r() * 0.5), h / 2, z]);
    box(g, 0.1, 0.5, w * 0.8, i % 3 ? '#c0423e' : '#3f9a9a', sx * 6.48, 3.1, z);       // shop awning band
  }
  for (let i = 0; i < 8; i++) {
    const z = 1 - i * 8;
    for (const sx of [-1, 1]) {
      box(g, 0.08, 4.2, 0.08, '#2a2238', sx * 3.9, 2.1, z);
      lamp(g, lights, { x: sx * 3.6, y: 4.2, z, r: 0.16, color: '#ffd8a8', power: i < 3 ? 3 : 0, range: 9 });
    }
    if (i % 2 === 0) stringLights(g, { x0: -6, x1: 6, y: 5.5, z: z - 3, n: 26, sag: 0.6 });
  }
  plant(g, -4.2, -3); plant(g, 4.3, -9);
  duskSky(g, { x: 0, y: 6, z: -66, w: 80, h: 18, blocks: 50, skylineY: 0 });
  for (let i = 0; i < 16; i++) spots.push({ x: (i % 2 ? 1 : -1) * (4.3 + r() * 1.2), y: 0.12, z: -1 - i * 2.2, ry: (i % 2 ? -1 : 1) * (0.6 + r()), sit: false });
  // story props: a parked car, a lit food cart, a lit shop sign (TEMPLATE.md §6)
  car(g, 3.2, -4.5, { color: '#3f6fc0', ry: 0 }); car(g, -3.6, -9.0, { color: '#c0423e', ry: Math.PI });
  foodCart(g, lights, -3.4, -2.2, { ry: 0.4 });
  litBoard(g, 5.5, 3.1, -7.2, { w: 1.8, h: 0.5, ry: -Math.PI / 2, glow: '#9ad0f0', rows: 1 });
  // specs/027 (FR-008): dressing in all three layers of the default wide shot
  tree(g, -5.4, 3.2, { h: 2.8, seed: 7 }); tree(g, 5.6, -2.5, { h: 3, seed: 8 }); tree(g, -5.6, -14, { h: 3, seed: 9 });
  prop(cyl(g, 0.24, 0.8, '#3a5a4a', 4.4, 0.52, 2.6, 12), 'bin');
  return {
    group: g, lights, room: { x0: -6.2, x1: 6.2, z0: -60, z1: 14 }, fog: [14, 70], grade: { exposure: 0.7, saturation: 1.08 },
    anchors: { hero: { x: 0, y: 0, z: 0, ry: 0 }, heroSeat: { x: -4.5, z: -0.5, ry: 0.6, y: 0.12 }, extras: spots.slice(0, 8), crowd: { area: { x0: -6, x1: 6, z0: -40, z1: -4 } }, fg: [{ x: -3.9, y: 2, z: 2.5 }] },
    seats: [{ x: -4.5, z: -0.5, ry: 0.6 }],
  };
}
