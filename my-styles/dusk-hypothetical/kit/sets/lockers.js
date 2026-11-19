// School corridor: rows of lockers on both sides receding to a dusk window, tiled floor, light strips overhead.
import * as THREE from 'three';
import { floor, ceiling, lightStrip, locker, duskSky, box, bench, mulberry } from './parts.js';

const COLORS = ['#3f6f8f', '#3f6f8f', '#7a5cc0', '#3f6f8f', '#c0423e'];
export function build() {
  const g = new THREE.Group(), lights = [], spots = [];
  floor(g, { w: 6, d: 34, color: '#b08a86', lines: 20, tile: true, z: -12 });
  ceiling(g, { w: 6, d: 34, y: 3.0, z: -12 });
  const r = mulberry(5);
  for (const sx of [-1, 1]) {
    box(g, 0.2, 3.0, 34, '#4d3b66', sx * 2.6, 1.5, -12);
    for (let i = 0; i < 64; i++) {
      const z = 3 - i * 0.47;
      const c = r() < 0.12 ? COLORS[Math.floor(r() * COLORS.length)] : '#3f6f8f';
      const L = new THREE.Group(); L.position.set(sx * 2.25, 0, z); L.rotation.y = -sx * Math.PI / 2; g.add(L);
      locker(L, 0, 0, { color: c });
    }
  }
  bench(g, -1.4, -6, { len: 2.2, ry: Math.PI / 2 });
  lightStrip(g, lights, { x: 0, y: 2.95, z: -12, len: 30, along: 'z', every: 5 });
  box(g, 4.8, 2.4, 0.1, '#2a1e40', 0, 1.5, -28.5);
  duskSky(g, { x: 0, y: 1.6, z: -31, w: 8, h: 4, blocks: 8, skylineY: 0.5 });
  for (let i = 0; i < 18; i++) spots.push({ x: (i % 2 ? 1 : -1) * (0.9 + 0.3 * r()), y: 0, z: -1.5 - i * 1.1, ry: (i % 2 ? -1 : 1) * 1.2, sit: false });
  return {
    group: g, lights, room: { x0: -2.3, x1: 2.3, z0: -28, z1: 6, y1: 2.85 }, fog: [8, 32],
    anchors: { hero: { x: 0, y: 0, z: 0, ry: 0 }, heroSeat: { x: -1.4, z: -6, ry: Math.PI / 2 }, extras: spots.slice(0, 8), crowd: { area: { x0: -1.6, x1: 1.6, z0: -24, z1: -2 } }, fg: [{ x: -1.9, y: 1.1, z: 1.8 }] },
  };
}
