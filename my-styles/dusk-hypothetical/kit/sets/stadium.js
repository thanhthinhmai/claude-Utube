// Stadium at dusk: a green pitch, tiered stands with thousands of seats, floodlight towers, a jumbotron.
import * as THREE from 'three';
import { floor, box, lamp, duskSky, mesh, mat, canvasTex, stdMat } from './parts.js';

export function build() {
  const g = new THREE.Group(), lights = [], seats = [];
  const grass = canvasTex('pitch', 256, 256, (c, W, H) => {
    for (let i = 0; i < 16; i++) { c.fillStyle = i % 2 ? '#ffffff' : '#e6f0e0'; c.fillRect(0, i * 16, W, 16); }
    c.strokeStyle = 'rgba(255,255,255,.9)'; c.lineWidth = 3; c.strokeRect(10, 10, W - 20, H - 20); c.beginPath(); c.arc(W / 2, H / 2, 30, 0, 7); c.stroke();
  }, [1, 1]);
  mesh(g, new THREE.BoxGeometry(120, 0.1, 90), stdMat('#346a3e', { map: grass, rough: 0.95 }), [0, -0.05, -8]);
  // back stand: 12 tiers, 200 seats each; two side stands: 8 tiers, 120 seats each
  const stand = (cx, cz, ry, tiers, n, width) => {
    const s = new THREE.Group(); s.position.set(cx, 0, cz); s.rotation.y = ry; g.add(s);
    for (let t = 0; t < tiers; t++) {
      const y = 1 + t * 0.7, z = -t * 1.0;
      box(s, width, 0.7, 1.0, t % 2 ? '#5a4874' : '#4d3b66', 0, y - 0.35, z);
      for (let i = 0; i < n; i++) {
        const lx = -width / 2 + (i + 0.5) * (width / n);
        const p = new THREE.Vector3(lx, 0, z).applyAxisAngle(new THREE.Vector3(0, 1, 0), ry).add(new THREE.Vector3(cx, 0, cz));
        seats.push({ x: p.x, y: y - 0.6, z: p.z, ry, sit: true });
      }
    }
    box(s, width, 2, 0.4, '#3a2e50', 0, 1 + tiers * 0.7, -tiers * 1.0);
  };
  stand(0, -44, 0, 12, 200, 100);
  stand(-46, -18, Math.PI / 2, 8, 120, 44);
  stand(46, -18, -Math.PI / 2, 8, 120, 44);
  box(g, 100, 1, 0.4, '#3a2e50', 0, 0.5, -43.4);                     // pitch wall
  for (const [x, z] of [[-40, -48], [40, -48], [-50, 6], [50, 6]]) {   // floodlight towers
    box(g, 0.6, 22, 0.6, '#2a2238', x, 11, z);
    for (let i = 0; i < 6; i++) lamp(g, lights, { x: x + (i % 3 - 1) * 1.1, y: 22 + Math.floor(i / 3) * 1.1, z, r: 0.45, color: '#fff0d8', power: 0 });
  }
  for (const x of [-25, 25]) { const p = new THREE.PointLight('#ffe6c8', 80, 70, 1.4); p.position.set(x, 20, -20); g.add(p); lights.push(p); }
  // jumbotron on the back stand
  box(g, 16, 7, 0.6, '#1c1626', 0, 20, -58);
  mesh(g, new THREE.PlaneGeometry(15, 6.2), mat('#2a2040', 0.5, '#7a5cc0', 0.55), [0, 20, -57.68], false);
  duskSky(g, { x: 0, y: 18, z: -75, w: 200, h: 50, blocks: 60, skylineY: 6 });
  return {
    group: g, lights, room: { x0: -44, x1: 44, z0: -42, z1: 30 }, fog: [40, 160], grade: { exposure: 0.64, saturation: 1.15 },
    anchors: { hero: { x: 0, y: 0, z: -32, ry: 0 }, heroSeat: { x: 0, z: -44, ry: 0, y: 0.4 }, extras: [{ x: -1.5, y: 0, z: -33.2, ry: 0.4 }, { x: 1.6, y: 0, z: -33.4, ry: -0.4 }, { x: -3, y: 0, z: -35, ry: 0.3 }], crowd: { slots: seats }, fg: [] },
  };
}
