// Parking lot at dusk (specs/027 US2): painted bays with parked cars, a lit corner store with a sign, street lamps,
// a fence and trees at the sides, the dusk sky; a car and cones in the foreground.
import * as THREE from 'three';
import { car, cyl, fence, floor, house, litBoard, parkLines, prop, skyDome, streetLamp, tree } from './parts.js';

export const info = { outdoor: true, room: { x0: -14, x1: 14, z0: -14, z1: 14 } };

export function build() {
  const g = new THREE.Group(), lights = [];
  skyDome(g, { sun: [-0.8, 0.05, -1] });
  floor(g, { w: 60, d: 60, color: '#4a3a50', lines: 0, z: -6 });
  parkLines(g, { x0: -10.4, z: -5.5, n: 8, gap: 2.6 });
  ['#c0423e', '#3f6fc0', '#d9b23a', '#4f8f4a', '#7a5cc0'].forEach((c, i) => car(g, -9.1 + [0, 1, 3, 5, 6][i] * 2.6, -5.5, { color: c, ry: Math.PI / 2 }));
  house(g, 0, -13, { w: 12, h: 4.2, d: 5, color: '#5a4874', seed: 61, lit: 0.85 });                  // the store, windows lit
  litBoard(g, 0, 3.6, -10.45, { w: 4, h: 0.8, glow: '#ff9e70', rows: 1 });
  streetLamp(g, lights, -7, -8.5); streetLamp(g, lights, 7, -8.5, { ry: Math.PI }); streetLamp(g, lights, 9.5, 2.5, { ry: Math.PI, power: 1.2 });
  fence(g, -12, 6, -12, { along: 'z', h: 1.8 }); fence(g, -12, 6, 12, { along: 'z', h: 1.8 });
  [[-13, -10, 3.4], [13, -9, 3.0], [-13.5, 1, 2.8]].forEach(([x, z, h], i) => tree(g, x, z, { h, seed: i + 11 }));
  car(g, 5.2, 3.2, { color: '#3f9a9a', ry: 0.15 });                                                 // foreground
  for (const [x, z] of [[-2.6, 2.2], [-3.4, 2.6]]) prop(cyl(g, 0.12, 0.45, '#e07a3a', x, 0.22, z, 10), 'cone');
  return {
    group: g, lights, room: info.room, fog: [18, 90], grade: { exposure: 0.66, saturation: 1.05 },
    anchors: { hero: { x: 0, y: 0, z: 0, ry: 0 }, heroSeat: null,
      extras: [{ x: -1.4, y: 0, z: -1, ry: 0.4 }, { x: 1.5, y: 0, z: -1.2, ry: -0.4 }, { x: -2.8, y: 0, z: -2.6, ry: 0.3 }],
      crowd: { area: { x0: -8, x1: 8, z0: -9, z1: -2 } }, fg: [{ x: 5.2, y: 1, z: 3.2 }] },
  };
}
