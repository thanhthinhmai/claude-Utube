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
  return prop(c, 'chair');
}
export function desk(g, x, z, { color = '#c89a6e', h = 0.86, w = 1.0, d = 0.6 } = {}) {
  prop(box(g, w, 0.06, d, color, x, h, z), 'desk');
  box(g, w - 0.1, 0.35, 0.04, '#7a5a7a', x, h - 0.2, z - d / 2 + 0.05);
  for (const sx of [-1, 1]) box(g, 0.05, h, d - 0.06, '#5a4874', x + sx * (w / 2 - 0.04), h / 2, z);
}
export function locker(g, x, z, { color = '#3f6f8f', h = 2.0, w = 0.45, face = 1 } = {}) {
  prop(box(g, w - 0.02, h, 0.45, color, x, h / 2, z), 'locker');
  box(g, 0.03, 0.18, 0.02, '#e0d6c8', x + w * 0.3, h * 0.55, z + face * 0.235);
  for (let i = 0; i < 3; i++) box(g, w * 0.6, 0.015, 0.02, '#2a3a52', x, h * 0.82 + i * 0.05, z + face * 0.235);
}
export function bench(g, x, z, { len = 2, color = '#b07a5e', seat = 0.6, ry = 0 } = {}) {
  const b = new THREE.Group(); b.position.set(x, 0, z); b.rotation.y = ry; g.add(b);
  box(b, len, 0.08, 0.45, color, 0, seat - 0.04, 0);
  for (const sx of [-1, 1]) box(b, 0.06, seat - 0.08, 0.4, '#5a4874', sx * (len / 2 - 0.15), (seat - 0.08) / 2, 0);
  return prop(b, 'bench');
}
export function table(g, x, z, { w = 1.8, d = 0.8, h = 0.86, color = '#d0a070' } = {}) {
  prop(box(g, w, 0.06, d, color, x, h, z), 'table');
  for (const [a, b] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) cyl(g, 0.035, h, '#5a4874', x + a * (w / 2 - 0.1), h / 2, z + b * (d / 2 - 0.08), 8);
}
export function plant(g, x, z, { h = 1.0 } = {}) {
  prop(cyl(g, 0.16, 0.3, '#b0603e', x, 0.15, z), 'plant');
  mesh(g, new THREE.SphereGeometry(0.3 * h, 12, 10), '#4f8f4a', [x, 0.3 + 0.3 * h, z]);
}

// ---------- story props (specs/023, TEMPLATE.md §6): one or two per set that tell what the place is for ----------
const PROP_COLS = ['#d9608c', '#3f9a9a', '#e07a3a', '#7a5cc0', '#4f8f4a', '#c99a2e', '#3f6fc0'];
// a poster on a wall: a coloured sheet with a simple drawn shape; face: +1 faces +z, or a ry in radians
export function poster(g, x, y, z, { w = 0.6, h = 0.85, seed = 1, ry = 0 } = {}) {
  const r = mulberry(seed * 31 + 7), col = PROP_COLS[Math.floor(r() * PROP_COLS.length)];
  const map = canvasTex(`poster-${seed}`, 64, 90, (c, W, H) => {
    c.fillStyle = col; c.fillRect(0, 0, W, H); c.fillStyle = 'rgba(255,240,220,.85)';
    const k = Math.floor(r() * 3);
    if (k === 0) { c.beginPath(); c.arc(W / 2, H * 0.42, W * 0.28, 0, Math.PI * 2); c.fill(); }
    else if (k === 1) { c.beginPath(); c.moveTo(W / 2, H * 0.15); c.lineTo(W * 0.85, H * 0.7); c.lineTo(W * 0.15, H * 0.7); c.fill(); }
    else c.fillRect(W * 0.2, H * 0.2, W * 0.6, H * 0.45);
    c.fillRect(W * 0.2, H * 0.8, W * 0.6, H * 0.06);
  });
  const o = mesh(g, new THREE.PlaneGeometry(w, h), stdMat(col, { map, rough: 0.9 }), [x, y, z], false); o.rotation.y = ry; return prop(o, 'poster');
}
export function backpack(g, x, z, { color = '#3f6fc0', y = 0, ry = 0 } = {}) {
  const b = new THREE.Group(); b.position.set(x, y, z); b.rotation.y = ry; g.add(b);
  mesh(b, new THREE.BoxGeometry(0.34, 0.42, 0.18), stdMat(color), [0, 0.21, 0]);
  mesh(b, new THREE.BoxGeometry(0.26, 0.16, 0.06), stdMat(new THREE.Color(color).multiplyScalar(0.8).getStyle()), [0, 0.14, 0.11]);
  return prop(b, 'backpack');
}
export function ball(g, x, y, z, { color = '#e07a3a', r = 0.12 } = {}) { return prop(mesh(g, new THREE.SphereGeometry(r, 16, 12), stdMat(color, { rough: 0.7 }), [x, y, z]), 'ball'); }
export function tray(g, x, y, z, { seed = 1 } = {}) {
  const r = mulberry(seed * 13 + 3), t = new THREE.Group(); t.position.set(x, y, z); g.add(t);
  mesh(t, new THREE.BoxGeometry(0.42, 0.025, 0.3), stdMat('#c8b8d8', { rough: 0.6 }), [0, 0.012, 0]);
  mesh(t, new THREE.CylinderGeometry(0.08, 0.07, 0.04, 14), stdMat(['#e0b040', '#c0423e', '#4f8f4a'][Math.floor(r() * 3)]), [-0.09, 0.045, 0]);
  mesh(t, new THREE.BoxGeometry(0.09, 0.05, 0.12), stdMat('#f0e0c0'), [0.1, 0.05, 0.02]);
  mesh(t, new THREE.CylinderGeometry(0.03, 0.03, 0.11, 10), stdMat(PROP_COLS[Math.floor(r() * PROP_COLS.length)]), [0.12, 0.08, -0.09]);
  return prop(t, 'tray');
}
// a self-lit sign or board with a few bars of text-like marks (no words)
export function litBoard(g, x, y, z, { w = 2, h = 0.7, color = '#2a2040', glow = '#ffd8a8', ry = 0, rows = 3 } = {}) {
  const map = canvasTex(`board-${rows}-${glow}`, 128, 48, (c, W, H) => {
    c.fillStyle = color; c.fillRect(0, 0, W, H); c.fillStyle = glow;
    for (let i = 0; i < rows; i++) c.fillRect(W * 0.1, H * (0.2 + i * 0.25), W * (0.5 + 0.3 * ((i * 37) % 3) / 2), H * 0.1);
  });
  const o = mesh(g, new THREE.PlaneGeometry(w, h), stdMat('#ffffff', { map, emissive: '#ffffff', ei: 0.5, rough: 0.6 }), [x, y, z], false);
  o.material.emissiveMap = map; o.rotation.y = ry; return prop(o, 'board');
}
export function globe(g, x, y, z) {
  prop(mesh(g, new THREE.CylinderGeometry(0.08, 0.1, 0.05, 12), stdMat('#5a4874'), [x, y + 0.025, z]), 'globe');
  mesh(g, new THREE.SphereGeometry(0.17, 20, 14), stdMat('#3f8fb0', { rough: 0.6 }), [x, y + 0.24, z]);
  mesh(g, new THREE.TorusGeometry(0.19, 0.008, 6, 24, Math.PI), stdMat('#c99a2e'), [x, y + 0.24, z]).rotation.y = Math.PI / 2;
}
export function laptop(g, x, y, z, { ry = 0 } = {}) {
  const l = new THREE.Group(); l.position.set(x, y, z); l.rotation.y = ry; g.add(l);
  mesh(l, new THREE.BoxGeometry(0.34, 0.015, 0.24), stdMat('#2a2438'), [0, 0.008, 0]);
  const s = mesh(l, new THREE.BoxGeometry(0.34, 0.22, 0.012), stdMat('#7d9cc0', { emissive: '#7d9cc0', ei: 0.9 }), [0, 0.12, -0.12]); s.rotation.x = -0.25;
  return prop(l, 'laptop');
}
export function trophy(g, x, y, z) {
  prop(mesh(g, new THREE.BoxGeometry(0.14, 0.06, 0.14), stdMat('#3a2e50'), [x, y + 0.03, z]), 'trophy');
  mesh(g, new THREE.CylinderGeometry(0.02, 0.02, 0.1, 8), stdMat('#d9b23a', { rough: 0.3, emissive: '#5a4010', ei: 0.4 }), [x, y + 0.11, z]);
  mesh(g, new THREE.CylinderGeometry(0.09, 0.04, 0.12, 14), stdMat('#d9b23a', { rough: 0.3, emissive: '#5a4010', ei: 0.4 }), [x, y + 0.22, z]);
}
export function pennants(g, { x0, x1, y, z, n = 14, seed = 2 } = {}) {
  const r = mulberry(seed * 17 + 1);
  for (let i = 0; i < n; i++) {
    const u = i / (n - 1), x = x0 + (x1 - x0) * u, yy = y - 0.18 * Math.sin(Math.PI * u);
    const tri = new THREE.Shape(); tri.moveTo(-0.12, 0); tri.lineTo(0.12, 0); tri.lineTo(0, -0.24);
    mesh(g, new THREE.ShapeGeometry(tri), new THREE.MeshStandardMaterial({ color: PROP_COLS[Math.floor(r() * PROP_COLS.length)], side: THREE.DoubleSide, roughness: 0.9 }), [x, yy, z], false);
  }
}
export function car(g, x, z, { color = '#c0423e', ry = 0 } = {}) {
  const c = new THREE.Group(); c.position.set(x, 0, z); c.rotation.y = ry; g.add(c);
  mesh(c, new THREE.BoxGeometry(1.8, 0.5, 0.9), stdMat(color, { rough: 0.5 }), [0, 0.45, 0]);
  mesh(c, new THREE.BoxGeometry(1.0, 0.4, 0.82), stdMat('#3a3050', { rough: 0.3 }), [-0.1, 0.88, 0]);
  for (const [wx, wz] of [[-0.6, 0.45], [0.6, 0.45], [-0.6, -0.45], [0.6, -0.45]]) mesh(c, new THREE.CylinderGeometry(0.2, 0.2, 0.14, 14), stdMat('#1c1626'), [wx, 0.2, wz]).rotation.x = Math.PI / 2;
  mesh(c, new THREE.SphereGeometry(0.06, 8, 6), stdMat('#ffe0b8', { emissive: '#ffe0b8', ei: 1.5 }), [0.92, 0.5, 0.3]);
  mesh(c, new THREE.SphereGeometry(0.06, 8, 6), stdMat('#ffe0b8', { emissive: '#ffe0b8', ei: 1.5 }), [0.92, 0.5, -0.3]);
  return prop(c, 'car');
}
export function foodCart(g, lights, x, z, { color = '#e07a3a', ry = 0 } = {}) {
  const c = new THREE.Group(); c.position.set(x, 0, z); c.rotation.y = ry; g.add(c);
  mesh(c, new THREE.BoxGeometry(1.4, 0.9, 0.7), stdMat(color), [0, 0.65, 0]);
  mesh(c, new THREE.BoxGeometry(1.6, 0.06, 0.9), stdMat('#f0e6d8'), [0, 1.65, 0]);
  for (const sx of [-0.7, 0.7]) mesh(c, new THREE.CylinderGeometry(0.025, 0.025, 0.55, 8), stdMat('#5a4874'), [sx, 1.38, 0.3]);
  for (const sx of [-0.45, 0.45]) mesh(c, new THREE.CylinderGeometry(0.16, 0.16, 0.06, 14), stdMat('#1c1626'), [sx, 0.16, 0.37]).rotation.x = Math.PI / 2;
  lamp(c, lights, { x: 0, y: 1.55, z: 0.25, r: 0.07, power: 1.4, range: 4 });
  return prop(c, 'cart');
}

// ---------- specs/027: props are counted by layer (catalog.json → set_info.props_min) ----------
// prop(obj, kind): marks an object as one story or dressing prop; countProps(group, hero) sorts them into the layers
// of the default wide shot looking toward -z at the hero: fore (between the camera and the hero), mid (around the
// hero, up to 3 m behind) and back (further behind)
export function prop(obj, kind) { obj.userData.prop = kind; return obj; }
export function countProps(group, hero = { z: 0 }) {
  const out = { total: 0, fore: 0, mid: 0, back: 0, kinds: {} };
  group.updateMatrixWorld(true);
  const p = new THREE.Vector3();
  group.traverse((o) => {
    if (!o.userData.prop) return;
    o.getWorldPosition(p);
    const layer = p.z > hero.z + 0.8 ? 'fore' : p.z >= hero.z - 3 ? 'mid' : 'back';
    out.total++; out[layer]++; out.kinds[o.userData.prop] = (out.kinds[o.userData.prop] || 0) + 1;
  });
  return out;
}
const tagGroup = (g, x, y, z, kind, ry = 0) => { const o = new THREE.Group(); o.position.set(x, y, z); o.rotation.y = ry; g.add(o); return prop(o, kind); };

// a round-topped tree: trunk and three leaf balls in dusk greens
export function tree(g, x, z, { h = 2.6, seed = 1 } = {}) {
  const t = tagGroup(g, x, 0, z, 'tree'), r = mulberry(seed * 19 + 5);
  cyl(t, 0.09, h * 0.55, '#5a3e3a', 0, h * 0.275, 0, 8);
  const greens = ['#3f6e4a', '#4a7a52', '#365e46'];
  for (let i = 0; i < 3; i++) mesh(t, new THREE.SphereGeometry(h * (0.24 + 0.06 * r()), 12, 10), greens[i], [(r() - 0.5) * h * 0.25, h * (0.62 + 0.12 * i), (r() - 0.5) * h * 0.2]);
  return t;
}
// a street lamp: a pole, an arm and a glowing head with its light (bloom point)
export function streetLamp(g, lights, x, z, { h = 3.4, ry = 0, power = 1.6 } = {}) {
  const s = tagGroup(g, x, 0, z, 'lamp', ry);
  cyl(s, 0.05, h, '#2a2238', 0, h / 2, 0, 8);
  box(s, 0.6, 0.05, 0.05, '#2a2238', 0.3, h, 0);
  lamp(s, lights, { x: 0.6, y: h - 0.08, z: 0, r: 0.13, color: '#ffd29a', power, range: 7 });
  return s;
}
// a chain-link fence along x from x0 to x1 at z: posts, a top rail and a see-through mesh
export function fence(g, x0, x1, z, { h = 2.2, along = 'x' } = {}) {
  const len = Math.abs(x1 - x0), mid = (x0 + x1) / 2, f = tagGroup(g, along === 'x' ? mid : z, 0, along === 'x' ? z : mid, 'fence', along === 'x' ? 0 : Math.PI / 2);
  for (let i = 0; i <= Math.ceil(len / 2.5); i++) cyl(f, 0.03, h, '#4a4058', -len / 2 + Math.min(len, i * 2.5), h / 2, 0, 6);
  box(f, len, 0.04, 0.04, '#4a4058', 0, h, 0);
  mesh(f, new THREE.PlaneGeometry(len, h), new THREE.MeshStandardMaterial({ color: '#8a7a9a', transparent: true, opacity: 0.22, side: THREE.DoubleSide, roughness: 0.9 }), [0, h / 2, 0], false);
  return f;
}
// a house or shop block with a grid of lit windows (self-lit, so they glow at dusk) and a flat roof edge
export function house(g, x, z, { w = 4, h = 5, d = 4, color = '#6e4e80', seed = 1, lit = 0.35, ry = 0 } = {}) {
  const o = tagGroup(g, x, 0, z, 'house', ry), r = mulberry(seed * 23 + 11);
  const map = canvasTex(`house-${seed}-${lit}`, 64, 96, (c, W, H) => {
    c.fillStyle = '#000'; c.fillRect(0, 0, W, H);
    for (let yy = 8; yy < H - 10; yy += 18) for (let xx = 6; xx < W - 8; xx += 16) { c.fillStyle = r() < lit ? '#ffd29a' : '#2a2040'; c.fillRect(xx, yy, 9, 11); }
  });
  const m = stdMat(color, { rough: 0.9, emissive: '#ffffff', ei: map ? 0.9 : 0 });
  if (map) { m.emissiveMap = map; map.repeat.set(Math.max(1, Math.round(w / 2)), Math.max(1, Math.round(h / 3))); }
  mesh(o, new THREE.BoxGeometry(w, h, d), m, [0, h / 2, 0]);
  box(o, w + 0.2, 0.2, d + 0.2, new THREE.Color(color).multiplyScalar(0.7).getStyle(), 0, h + 0.1, 0);
  return o;
}
// a basketball hoop on a pole facing +z (ry turns it)
export function hoop(g, x, z, { ry = 0 } = {}) {
  const o = tagGroup(g, x, 0, z, 'hoop', ry);
  cyl(o, 0.07, 3.0, '#3a3050', 0, 1.5, 0, 8);
  box(o, 0.05, 0.05, 0.6, '#3a3050', 0, 3.0, 0.3);
  box(o, 1.6, 1.0, 0.05, '#f0e6d8', 0, 3.3, 0.6);
  mesh(o, new THREE.TorusGeometry(0.23, 0.02, 6, 20), '#e07a3a', [0, 3.0, 0.85]).rotation.x = Math.PI / 2;
  return o;
}
// a railing along x at z (rooftop edge, balcony)
export function railing(g, x0, x1, z, { h = 1.05, along = 'x' } = {}) {
  const len = Math.abs(x1 - x0), mid = (x0 + x1) / 2, o = tagGroup(g, along === 'x' ? mid : z, 0, along === 'x' ? z : mid, 'railing', along === 'x' ? 0 : Math.PI / 2);
  for (let i = 0; i <= Math.ceil(len / 1.2); i++) cyl(o, 0.025, h, '#5a5068', -len / 2 + Math.min(len, i * 1.2), h / 2, 0, 6);
  box(o, len, 0.05, 0.06, '#6a6078', 0, h, 0);
  box(o, len, 0.03, 0.03, '#5a5068', 0, h * 0.5, 0);
  return o;
}
// parking bay lines: n white stripes across z from x0, every `gap` m
export function parkLines(g, { x0 = -8, z = -4, n = 8, gap = 2.6, len = 4.5 } = {}) {
  for (let i = 0; i <= n; i++) box(g, 0.1, 0.012, len, '#e8e0f0', x0 + i * gap, 0.006, z);
}
// a sky dome: a gradient from lilac overhead to a warm glow at the horizon, with a soft sun disc (fog-free)
export function skyDome(g, { r = 100, sun = [-0.5, 0.06, -1], top = '#7a6ac0', mid = '#d49ac0', low = '#ffc49a' } = {}) {
  const map = canvasTex(`sky-dome-${top}-${low}`, 4, 256, (c) => {
    const gr = c.createLinearGradient(0, 0, 0, 256);
    gr.addColorStop(0, top); gr.addColorStop(0.42, mid); gr.addColorStop(0.5, low); gr.addColorStop(1, low);
    c.fillStyle = gr; c.fillRect(0, 0, 4, 256);
  });
  const d = mesh(g, new THREE.SphereGeometry(r, 32, 16), new THREE.MeshBasicMaterial({ color: map ? '#ffffff' : mid, map, side: THREE.BackSide, fog: false, depthWrite: false }), [0, 0, 0], false);
  d.renderOrder = -1; d.name = 'sky';
  const s = new THREE.Vector3(...sun).normalize().multiplyScalar(r * 0.9);
  mesh(g, new THREE.SphereGeometry(r * 0.06, 16, 12), new THREE.MeshBasicMaterial({ color: '#fff0d0', fog: false }), [s.x, s.y, s.z], false);
  return d;
}
// a window lit from outside: a glowing pane (blooms) that reads as dusk light coming in
export function windowGlow(g, x, y, z, { w = 1.6, h = 1.3, ry = 0, color = '#ffc89a', ei = 1.1 } = {}) {
  const o = mesh(g, new THREE.PlaneGeometry(w, h), mat('#fff0e0', 0.6, color, ei), [x, y, z], false);
  o.rotation.y = ry; return prop(o, 'window');
}
// a shaft of low sun through a window: a slanted, faint warm plane drawn over the scene (no light of its own)
export function sunBeam(g, x, y, z, { w = 1.4, h = 4, ry = 0, tilt = 0.75, color = '#ffc89a', opacity = 0.12 } = {}) {
  const o = mesh(g, new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false }), [x, y, z], false);
  o.rotation.set(-tilt, ry, 0); o.renderOrder = 2; return o;
}
