// Shared set parts of the Dusk Hypothetical kit (specs/022 T013): floors, walls, repeated prop grids, practical
// lights with bloom, self-lit ceilings, dusk windows. Every set is built from these, so rooms share the proof frame's
// materials and never go black at the far end (round 9). A set returns {group, anchors, lights, fog?, grade?}
// (fog: [near, far] for big places; grade: the set's {exposure, saturation} nudge, within the kit's limits):
//   room          {x0, x1, z0, z1, y1?}  inside of the walls and under the ceiling: the camera stays in it
//   anchors.hero  {x, y, z, ry, seat?}   where the hero stands (or sits, seat = seat height)
//   anchors.extras [{x, y, z, ry, sit}]   slots for named extras of the scene's cast, nearest first
//   anchors.crowd {slots} | {area}        where a crowd goes
//   anchors.fg    [{x, y, z}]              spots for foreground cover (poles, rails), used by over-shoulder framing
import * as THREE from 'three';
import { mat } from '../figure.js';
import { mulberry } from '../plan.js';

export { mat, mulberry };
export const DUSK = ['#4a3478', '#9a5c90', '#e09a7c', '#f2b88a'];

export function mesh(parent, geo, m, [x, y, z] = [0, 0, 0], shadow = true) {
  const o = new THREE.Mesh(geo, typeof m === 'string' ? mat(m) : m);
  o.position.set(x, y, z); o.castShadow = o.receiveShadow = shadow; parent.add(o); return o;
}
export const box = (parent, w, h, d, m, x, y, z) => mesh(parent, new THREE.BoxGeometry(w, h, d), m, [x, y, z]);
export const cyl = (parent, r, h, m, x, y, z, seg = 12) => mesh(parent, new THREE.CylinderGeometry(r, r, h, seg), m, [x, y, z]);

const TEX = new Map();
export function canvasTex(key, w, h, draw, repeat) {
  if (typeof document === 'undefined') return null;           // node tests: no canvas, plain colours
  if (!TEX.has(key)) {
    const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; TEX.set(key, t);
  }
  const t = TEX.get(key).clone(); t.needsUpdate = true; if (repeat) t.repeat.set(...repeat); return t;
}
export function stdMat(color, { map, rough = 0.85, emissive, ei = 1 } = {}) {
  return new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: 0, ...(map ? { map } : {}), ...(emissive ? { emissive, emissiveIntensity: ei } : {}) });
}

// floor with planks or tiles (lines), receives shadows
export function floor(g, { w = 30, d = 30, color = '#9c7068', lines = 16, tile = false, x = 0, z = 0, y = 0 } = {}) {
  const map = canvasTex(`floor-${lines}-${tile}`, 256, 256, (c, W, H) => {
    c.fillStyle = '#fff'; c.fillRect(0, 0, W, H); c.fillStyle = 'rgba(60,30,60,.25)';
    for (let i = 0; i < lines; i++) { c.fillRect(0, i * (H / lines), W, 2); if (tile) c.fillRect(i * (W / lines), 0, 2, H); }
  }, [w / 5, d / 5]);
  return mesh(g, new THREE.BoxGeometry(w, 0.1, d), stdMat(color, { map, rough: 0.8 }), [x, y - 0.05, z]);
}
// a wall along x (facing +z) or along z (facing ±x)
export function wall(g, { len = 30, h = 3.3, along = 'x', at = -6, from = 0, color = '#4d3b66', band = '#5a4874' } = {}) {
  const [w, d] = along === 'x' ? [len, 0.2] : [0.2, len];
  const [x, z] = along === 'x' ? [from, at] : [at, from];
  box(g, w, h, d, color, x, h / 2, z);
  if (band) box(g, along === 'x' ? len : 0.25, 0.3, along === 'x' ? 0.25 : len, band, x, h * 0.42, z + (along === 'x' ? 0.05 : 0));
}
// self-lit ceiling so the far end never goes black (proof round 9)
export function ceiling(g, { w = 30, d = 30, y = 3.3, color = '#6e5c88', glow = '#4a3a66', x = 0, z = 0 } = {}) {
  return mesh(g, new THREE.BoxGeometry(w, 0.1, d), mat(color, 0.9, glow, 0.5), [x, y, z], false);
}
// practical light strip: an emissive bar (blooms) plus a soft point light every `every` metres
export function lightStrip(g, lights, { x = 0, y = 3.17, z = 0, len = 20, along = 'x', color = '#ffd8b0', ei = 0.45, lamp = '#ffe0b8', power = 2.4, every = 6, range = 7 } = {}) {
  const geo = along === 'x' ? new THREE.BoxGeometry(len, 0.06, 0.22) : new THREE.BoxGeometry(0.22, 0.06, len);
  mesh(g, geo, mat('#c8b6b8', 0.5, color, ei), [x, y, z], false);
  const n = Math.max(1, Math.floor(len / every));
  for (let i = 0; i < n; i++) {
    const k = (i + 0.5) / n - 0.5;
    const p = new THREE.PointLight(lamp, power, range); p.position.set(along === 'x' ? x + k * len : x, y - 0.6, along === 'x' ? z : z + k * len);
    g.add(p); lights.push(p);
  }
}
// a lamp: a glowing sphere (bokeh point) with a light
export function lamp(g, lights, { x, y, z, r = 0.12, color = '#ffd29a', power = 2, range = 6 } = {}) {
  mesh(g, new THREE.SphereGeometry(r, 14, 10), mat('#fff0d8', 0.4, color, 1.2), [x, y, z], false);
  if (power) { const p = new THREE.PointLight(color, power, range); p.position.set(x, y - 0.1, z); g.add(p); lights.push(p); }
}
// string lights: a row of small glowing bulbs (no lights of their own; bloom does the work)
export function stringLights(g, { x0, x1, y, z, n = 24, sag = 0.25, color = '#ffd29a' } = {}) {
  for (let i = 0; i < n; i++) {
    const k = i / (n - 1), x = x0 + (x1 - x0) * k, yy = y - sag * 4 * k * (1 - k);
    mesh(g, new THREE.SphereGeometry(0.045, 8, 6), mat('#fff0d8', 0.4, color, 1.6), [x, yy, z], false);
  }
}
// repeated grid of props: make(group, x, z, i, j)
export function grid(g, { nx, nz, dx, dz, x0 = 0, z0 = 0, make }) {
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) make(g, x0 + (i - (nx - 1) / 2) * dx, z0 - j * dz, i, j);
}
// dusk sky with a skyline of lit window grids, as seen through windows or at the end of a street
export function duskSky(g, { x = 0, y = 3, z = -14, w = 60, h = 10, blocks = 40, seed = 7, skylineY = 0.9 } = {}) {
  const sky = canvasTex('dusk-sky', 4, 256, (c) => {
    const gr = c.createLinearGradient(0, 0, 0, 256); DUSK.forEach((col, i) => gr.addColorStop([0, 0.5, 0.82, 1][i], col)); c.fillStyle = gr; c.fillRect(0, 0, 4, 256);
  });
  mesh(g, new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: sky ? '#ffffff' : '#9a5c90', map: sky, fog: false }), [x, y, z], false);
  const r = mulberry(seed);
  const winT = canvasTex('skyline-win', 32, 64, (c, cw, ch) => {
    c.fillStyle = '#fff'; c.fillRect(0, 0, cw, ch);
    for (let yy = 4; yy < ch - 4; yy += 8) for (let xx = 3; xx < cw - 3; xx += 7) { c.fillStyle = r() < 0.18 ? '#ffd29a' : '#4c3c6a'; c.fillRect(xx, yy, 4, 5); }
  });
  for (let i = 0; i < blocks; i++) {
    const bw = 0.8 + r() * 1.6, bh = 0.8 + r() * 3, bx = x - w / 2 + (i + 0.5) * (w / blocks) + (r() - 0.5) * 0.4;
    const m = new THREE.MeshBasicMaterial({ color: i % 3 ? '#3e2e58' : '#352650', map: winT ? Object.assign(winT.clone(), { needsUpdate: true }) : null, fog: false });
    if (m.map) m.map.repeat.set(Math.round(bw * 2), Math.round(bh * 1.5));
    mesh(g, new THREE.PlaneGeometry(bw, bh), m, [bx, skylineY + bh / 2, z + 1 + (i % 4) * 0.3], false);
  }
}
// window band in a wall along x: frames, sill, the dusk sky behind
export function windows(g, { z = -6, y = 2.1, h = 1.5, w = 1.9, n = 6, gap = 2.2, x0 = 0, frame = '#5a4876', face = 1 } = {}) {
  for (let i = 0; i < n; i++) {
    const x = x0 + (i - (n - 1) / 2) * gap;
    box(g, 0.14, h + 0.1, 0.22, frame, x - w / 2, y, z); box(g, 0.14, h + 0.1, 0.22, frame, x + w / 2, y, z);
    box(g, w, 0.1, 0.24, frame, x, y - h / 2, z); box(g, w, 0.1, 0.24, frame, x, y + h / 2, z);
  }
  duskSky(g, { x: x0, y: y + 0.3, z: z - face * 3, w: n * gap + 6, h: 6, blocks: n * 5, skylineY: y - h / 2 - 0.3 });
}

// ---------- furniture (matte plastic, rounded where it matters) ----------
export function chair(g, x, z, { color = '#a8745e', back = '#82588a', ry = 0, seat = 0.6 } = {}) {
  const c = new THREE.Group(); c.position.set(x, 0, z); c.rotation.y = ry; g.add(c);
  box(c, 0.5, 0.08, 0.5, color, 0, seat - 0.04, 0);
  box(c, 0.5, 0.5, 0.07, back, 0, seat + 0.25, -0.24);
  for (const [a, b] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) cyl(c, 0.025, seat - 0.08, '#3a2e48', a * 0.21, (seat - 0.08) / 2, b * 0.21, 6);
  return c;
}
export function desk(g, x, z, { color = '#c89a6e', h = 0.86, w = 1.0, d = 0.6 } = {}) {
  box(g, w, 0.06, d, color, x, h, z);
  box(g, w - 0.1, 0.35, 0.04, '#7a5a7a', x, h - 0.2, z - d / 2 + 0.05);
  for (const sx of [-1, 1]) box(g, 0.05, h, d - 0.06, '#5a4874', x + sx * (w / 2 - 0.04), h / 2, z);
}
export function locker(g, x, z, { color = '#3f6f8f', h = 2.0, w = 0.45, face = 1 } = {}) {
  box(g, w - 0.02, h, 0.45, color, x, h / 2, z);
  box(g, 0.03, 0.18, 0.02, '#e0d6c8', x + w * 0.3, h * 0.55, z + face * 0.235);
  for (let i = 0; i < 3; i++) box(g, w * 0.6, 0.015, 0.02, '#2a3a52', x, h * 0.82 + i * 0.05, z + face * 0.235);
}
export function bench(g, x, z, { len = 2, color = '#b07a5e', seat = 0.6, ry = 0 } = {}) {
  const b = new THREE.Group(); b.position.set(x, 0, z); b.rotation.y = ry; g.add(b);
  box(b, len, 0.08, 0.45, color, 0, seat - 0.04, 0);
  for (const sx of [-1, 1]) box(b, 0.06, seat - 0.08, 0.4, '#5a4874', sx * (len / 2 - 0.15), (seat - 0.08) / 2, 0);
  return b;
}
export function table(g, x, z, { w = 1.8, d = 0.8, h = 0.86, color = '#d0a070' } = {}) {
  box(g, w, 0.06, d, color, x, h, z);
  for (const [a, b] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) cyl(g, 0.035, h, '#5a4874', x + a * (w / 2 - 0.1), h / 2, z + b * (d / 2 - 0.08), 8);
}
export function plant(g, x, z, { h = 1.0 } = {}) {
  cyl(g, 0.16, 0.3, '#b0603e', x, 0.15, z);
  mesh(g, new THREE.SphereGeometry(0.3 * h, 12, 10), '#4f8f4a', [x, 0.3 + 0.3 * h, z]);
}
