// Outdoor basketball court at dusk (specs/027 US2): a painted court behind a chain-link fence, a hoop, street lamps,
// lit houses and trees behind, the dusk sky; three layers of props for the default wide shot.
import * as THREE from 'three';
import { backpack, ball, bench, canvasTex, fence, floor, hoop, house, mesh, prop, skyDome, stdMat, streetLamp, tree, cyl } from './parts.js';

export const info = { outdoor: true, room: { x0: -14, x1: 14, z0: -16, z1: 14 } };

export function build() {
  const g = new THREE.Group(), lights = [];
  skyDome(g);
  floor(g, { w: 60, d: 60, color: '#4e3a52', lines: 0, z: -6 });                              // street asphalt around
  const court = canvasTex('court-out', 512, 512, (c, W, H) => {
    c.fillStyle = '#6a3a6a'; c.fillRect(0, 0, W, H); c.fillStyle = '#7e4676'; c.fillRect(W / 2 - 60, 24, 120, 150); c.strokeStyle = '#f4e8f0'; c.lineWidth = 7;
    c.strokeRect(24, 24, W - 48, H - 48); c.beginPath(); c.arc(W / 2, 24, 120, 0, Math.PI); c.stroke();
    c.strokeRect(W / 2 - 60, 24, 120, 150); c.beginPath(); c.moveTo(24, H * 0.75); c.lineTo(W - 24, H * 0.75); c.stroke();
  });
  // a deep purple court with bright lines (reference court cells: v-court sheets, 2026-11-19 board)
  mesh(g, new THREE.BoxGeometry(18, 0.04, 18), stdMat('#ffffff', { map: court, rough: 0.8 }), [0, 0.02, -2]);
  hoop(g, 0, -10.4);
  fence(g, -10, 10, -11.5); fence(g, -11.5, 7, -10, { along: 'z' }); fence(g, -11.5, 7, 10, { along: 'z' });
  [[-9, -19, 5, 6, '#6e4e80'], [-3, -20, 4, 8, '#5a4874'], [3, -19, 5, 5, '#7a5a7a'], [9, -20, 4, 7, '#6e4e80']].forEach(([x, z, w, h, c], i) => house(g, x, z, { w, h, d: 4, color: c, seed: 40 + i, lit: 0.4 }));
  [[-12.5, -13, 3.2], [12.5, -12.5, 3.0], [-13, -3, 2.8], [13, -2, 3.2]].forEach(([x, z, h], i) => tree(g, x, z, { h, seed: i + 3 }));
  streetLamp(g, lights, -10.6, -10.8, { ry: 0 }); streetLamp(g, lights, 10.6, -10.8, { ry: Math.PI });
  streetLamp(g, lights, 10.6, 3.5, { ry: Math.PI, power: 1.2 });                                  // fore, at the right edge
  bench(g, -6.5, -1.5, { ry: Math.PI / 2 }); backpack(g, -6.4, -0.6, { color: '#3f9a9a', ry: 0.4 });
  ball(g, 1.6, 0.12, 2.6); ball(g, -7.5, 0.12, -9.6, { color: '#d9b23a' });                       // one in front, one by the fence
  prop(cyl(g, 0.25, 0.8, '#3a5a4a', -4.2, 0.4, 3.6, 12), 'bin');                                // a bin in the foreground
  return {
    group: g, lights, room: info.room, fog: [18, 90], grade: { exposure: 0.66, saturation: 1.05 },
    anchors: { hero: { x: 0, y: 0, z: 0, ry: 0 }, heroSeat: { x: -6.5, z: -1.5, ry: Math.PI / 2, seat: 0.6 },
      extras: [{ x: -1.4, y: 0, z: -1.2, ry: 0.4 }, { x: 1.5, y: 0, z: -1.4, ry: -0.4 }, { x: -2.8, y: 0, z: -3.2, ry: 0.3 }, { x: 3, y: 0, z: -3.5, ry: -0.3 }],
      crowd: { area: { x0: -8, x1: 8, z0: -9, z1: -4 } }, fg: [{ x: -4.2, y: 0.8, z: 3.6 }] },
  };
}
