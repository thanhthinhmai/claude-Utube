// City rooftop at dusk (specs/027 US2): a flat roof with a railing, a water tank, air units, the stair hut with a lamp,
// string lights, the city skyline and the dusk sky behind; potted plants and a chair in the foreground.
import * as THREE from 'three';
import { box, chair, cyl, duskSky, floor, lamp, mesh, plant, prop, railing, skyDome, stringLights } from './parts.js';

export const info = { outdoor: true, room: { x0: -8.5, x1: 8.5, z0: -8.5, z1: 9 } };

export function build() {
  const g = new THREE.Group(), lights = [];
  skyDome(g, { sun: [0.6, 0.05, -1] });
  duskSky(g, { x: 0, y: 4, z: -70, w: 200, h: 30, blocks: 90, skylineY: -6 });
  floor(g, { w: 18, d: 18, color: '#6e5068', lines: 9, tile: true, z: 0 });
  box(g, 18.4, 0.5, 0.3, '#6a5068', 0, 0.25, -9); box(g, 0.3, 0.5, 18.4, '#6a5068', -9, 0.25, 0); box(g, 0.3, 0.5, 18.4, '#6a5068', 9, 0.25, 0);   // parapet
  railing(g, -9, 9, -9); railing(g, -9, 9, -9, { along: 'z' }); railing(g, -9, 9, 9, { along: 'z' });
  const tank = new THREE.Group(); tank.position.set(-5.5, 0, -6); g.add(tank); prop(tank, 'tank');
  cyl(tank, 1.0, 1.8, '#9a7a6a', 0, 2.2, 0, 18); for (const [x, z] of [[-0.7, -0.7], [0.7, -0.7], [-0.7, 0.7], [0.7, 0.7]]) cyl(tank, 0.06, 1.3, '#4a4058', x, 0.65, z, 6);
  for (const [x, z] of [[3.6, -6.8], [5.2, -6.6]]) { const u = prop(box(g, 1.1, 0.8, 0.9, '#b8b0c8', x, 0.4, z), 'ac'); mesh(g, new THREE.CylinderGeometry(0.3, 0.3, 0.02, 16), '#5a5068', [x, 0.81, z]); void u; }
  const hut = prop(box(g, 2.4, 2.6, 2.2, '#6e4e80', 6.3, 1.3, -2), 'hut');
  box(g, 0.9, 1.9, 0.05, '#3a2e50', 5.2, 0.95, -0.88); void hut;
  lamp(g, lights, { x: 5.2, y: 2.2, z: -0.8, r: 0.1, power: 1.4, range: 6 });
  prop(cyl(g, 0.03, 3.5, '#4a4058', -7.5, 1.75, -7.8, 6), 'antenna');
  stringLights(g, { x0: -8, x1: 8, y: 2.6, z: -4.5, n: 30 });
  plant(g, 3.4, 3.2, { h: 1.2 }); plant(g, 4.2, 3.6); chair(g, -3.2, 3.4, { ry: 0.6 });                  // foreground
  return {
    group: g, lights, room: info.room, fog: [20, 120], grade: { exposure: 0.66, saturation: 1.05 },
    anchors: { hero: { x: 0, y: 0, z: 0, ry: 0 }, heroSeat: { x: -3.2, z: 3.4, ry: 0.6, seat: 0.6 },
      extras: [{ x: -1.3, y: 0, z: -1, ry: 0.4 }, { x: 1.4, y: 0, z: -1.3, ry: -0.4 }, { x: -2.6, y: 0, z: -3, ry: 0.3 }],
      crowd: { area: { x0: -6, x1: 6, z0: -7, z1: -3 } }, fg: [{ x: 3.4, y: 0.8, z: 3.2 }] },
  };
}
