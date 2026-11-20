// Quiet neighbourhood street at dusk (specs/027 US2): houses with lit windows on both sides, sidewalks, trees, parked
// cars and lamps receding to the warm horizon; a tree and a car in the foreground, the dusk sky overhead.
import * as THREE from 'three';
import { car, cyl, floor, house, mulberry, prop, skyDome, streetLamp, tree } from './parts.js';

export const info = { outdoor: true, room: { x0: -6.5, x1: 6.5, z0: -60, z1: 14 } };

export function build() {
  const g = new THREE.Group(), lights = [], r = mulberry(27);
  skyDome(g, { sun: [0, 0.04, -1] });
  floor(g, { w: 7, d: 80, color: '#4e3a56', lines: 0, z: -25 });
  for (const sx of [-1, 1]) floor(g, { w: 2.6, d: 80, color: '#8a6e80', lines: 30, tile: true, x: sx * 4.8, z: -25, y: 0.1 });
  const COL = ['#6e4e80', '#7a5a7a', '#5a4874', '#8a6a80'];
  for (const sx of [-1, 1]) for (let i = 0; i < 9; i++) {
    const z = 2 - i * 7 - r() * 1.5;
    house(g, sx * (9 + r()), z, { w: 5, h: 3.5 + r() * 3, d: 5.5, color: COL[(i + (sx > 0 ? 1 : 0)) % 4], seed: 70 + i * 2 + (sx > 0 ? 1 : 0), lit: 0.45 });
    if (i % 2 === 0) tree(g, sx * 5.9, z - 3, { h: 2.6 + r() * 0.6, seed: 90 + i });
    if (i % 3 === 1) streetLamp(g, lights, sx * 3.7, z - 1.5, { ry: sx > 0 ? Math.PI : 0, power: i < 4 ? 1.4 : 0 });
    if (i % 3 === 2) car(g, sx * 2.6, z, { color: ['#c0423e', '#3f6fc0', '#d9b23a', '#4f8f4a'][i % 4], ry: Math.PI / 2 });
  }
  tree(g, -4.6, 3.8, { h: 2.8, seed: 5 }); car(g, 3.4, 2.6, { color: '#7a5cc0', ry: Math.PI / 2 });     // foreground
  prop(cyl(g, 0.12, 0.6, '#c0423e', -3.4, 0.4, 1.6, 10), 'hydrant');
  return {
    group: g, lights, room: info.room, fog: [16, 80], grade: { exposure: 0.66, saturation: 1.08 },
    anchors: { hero: { x: 0, y: 0, z: 0, ry: 0 }, heroSeat: null,
      extras: [{ x: -1.3, y: 0, z: -1, ry: 0.4 }, { x: 1.4, y: 0, z: -1.3, ry: -0.4 }, { x: -2.2, y: 0.1, z: -4, ry: 0.3 }, { x: 2.4, y: 0.1, z: -5, ry: -0.3 }],
      crowd: { area: { x0: -3, x1: 3, z0: -30, z1: -6 } }, fg: [{ x: -4.6, y: 1.5, z: 3.8 }] },
  };
}
