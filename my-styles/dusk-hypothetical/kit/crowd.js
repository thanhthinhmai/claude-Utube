// Crowds of the Dusk Hypothetical kit (specs/022 R4): from a few extras to thousands in one shot, told apart by
// hoodie colour, then hair or headwear. Three levels by distance to the camera:
//   near (≤ 6 m, at most NEAR_MAX people): full jointed figures (figure.js)
//   mid  (≤ 40 m): InstancedMesh, one draw per body part for everyone
//   far  (> 40 m): coloured points
// Everyone stands still or shares one tiny idle bob (STYLE.md motion), so a frame depends only on t and the camera.
import * as THREE from 'three';
import { makeFigure, mat, SKIN, SEAT } from './figure.js';
import { mulberry, CATALOG } from './plan.js';

export const NEAR_M = 6, FAR_M = 40, NEAR_MAX = 12;
const POSES_STAND = ['stand', 'stand', 'hold-phone', 'stand', 'hold-cup', 'point', 'cheer'];

// slots: [{x, y, z, ry, sit}] from the set; or an area {x0, x1, z0, z1, y} filled as a loose grid
export function slotsFor(n, { slots, area, seed = 1 } = {}) {
  const r = mulberry(seed * 7919 + 13);
  if (slots && slots.length) {
    const idx = slots.map((_, i) => i);
    for (let i = idx.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [idx[i], idx[j]] = [idx[j], idx[i]]; }
    return idx.slice(0, Math.min(n, idx.length)).map((i) => slots[i]);
  }
  const a = { x0: -6, x1: 6, z0: -8, z1: -2, y: 0, ...(area || {}) };
  const w = a.x1 - a.x0, d = a.z1 - a.z0, step = Math.max(0.55, Math.sqrt((w * d) / Math.max(1, n)));
  const out = [];
  for (let z = a.z0; z <= a.z1 && out.length < n; z += step)
    for (let x = a.x0; x <= a.x1 && out.length < n; x += step)
      out.push({ x: x + (r() - 0.5) * step * 0.5, y: a.y, z: z + (r() - 0.5) * step * 0.4, ry: (r() - 0.5) * 0.8, sit: !!a.sit });
  return out;
}

// one person's look, from the seed and index
export function lookOf(seed, i) {
  const r = mulberry(seed * 104729 + i * 31 + 1);
  const hoodie = CATALOG.hoodies[Math.floor(r() * CATALOG.hoodies.length)];
  const pick = r();
  const hair = pick < 0.45 ? CATALOG.hair[1 + Math.floor(r() * 3)] : 'bald';
  const hat = pick >= 0.45 && pick < 0.62 ? CATALOG.hats[Math.floor(r() * 2)] : null;
  return {
    hoodie, hair, hat,
    hairColor: CATALOG.hair_colours[Math.floor(r() * CATALOG.hair_colours.length)],
    hatColor: CATALOG.hoodies[Math.floor(r() * CATALOG.hoodies.length)],
    pose: POSES_STAND[Math.floor(r() * POSES_STAND.length)], face: r() < 0.6 ? 'dot' : r() < 0.5 ? 'happy' : 'wow',
    phase: r() * Math.PI * 2, turn: (r() - 0.5) * 0.6,
  };
}

export function makeCrowd({ n = 0, slots, area, seed = 1, bob = true, scale = 1 } = {}) {
  const group = new THREE.Group();
  const people = slotsFor(n, { slots, area, seed }).map((s, i) => ({ ...s, ...lookOf(seed, i) }));
  const N = people.length;
  // mid level: instanced parts (torso, head, legs, hair shell)
  const parts = {
    torso: new THREE.InstancedMesh(new THREE.CapsuleGeometry(0.23, 0.24, 4, 10), new THREE.MeshStandardMaterial({ roughness: 0.95 }), Math.max(1, N)),
    head: new THREE.InstancedMesh(new THREE.SphereGeometry(0.34, 18, 12), mat(SKIN, 0.6), Math.max(1, N)),
    legL: new THREE.InstancedMesh(new THREE.CapsuleGeometry(0.045, 0.42, 3, 8), mat(SKIN, 0.6), Math.max(1, N)),
    legR: new THREE.InstancedMesh(new THREE.CapsuleGeometry(0.045, 0.42, 3, 8), mat(SKIN, 0.6), Math.max(1, N)),
    armL: new THREE.InstancedMesh(new THREE.CapsuleGeometry(0.033, 0.42, 3, 8), mat(SKIN, 0.6), Math.max(1, N)),
    armR: new THREE.InstancedMesh(new THREE.CapsuleGeometry(0.033, 0.42, 3, 8), mat(SKIN, 0.6), Math.max(1, N)),
    hair: new THREE.InstancedMesh(new THREE.SphereGeometry(0.355, 16, 10, 0, Math.PI * 2, 0, Math.PI * 0.55), new THREE.MeshStandardMaterial({ roughness: 0.8 }), Math.max(1, N)),
  };
  const c = new THREE.Color();
  people.forEach((p, i) => {
    parts.torso.setColorAt(i, c.set(p.hoodie));
    parts.hair.setColorAt(i, c.set(p.hat ? p.hatColor : p.hairColor));
  });
  for (const m of Object.values(parts)) { m.castShadow = true; m.receiveShadow = true; m.frustumCulled = false; group.add(m); if (m.instanceColor) m.instanceColor.needsUpdate = true; }
  // far level: points
  const pos = new Float32Array(Math.max(1, N) * 3), col = new Float32Array(Math.max(1, N) * 3);
  people.forEach((p, i) => { c.set(p.hoodie); col.set([c.r, c.g, c.b], i * 3); });
  const pgeo = new THREE.BufferGeometry();
  pgeo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); pgeo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const points = new THREE.Points(pgeo, new THREE.PointsMaterial({ size: 0.42 * scale, vertexColors: true, sizeAttenuation: true }));
  points.frustumCulled = false; group.add(points);
  // near level: figures made on demand, kept per person
  const figures = new Map();
  const UPV = new THREE.Vector3(0, 1, 0), Q2 = new THREE.Quaternion();
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), S = new THREE.Vector3(), P = new THREE.Vector3(), E = new THREE.Euler();
  const hide = new THREE.Matrix4().makeScale(0, 0, 0);
  const levels = { near: 0, mid: 0, far: 0 };

  function update(camera, t = 0) {
    const cp = camera.getWorldPosition(new THREE.Vector3());
    const dist = people.map((p, i) => [Math.hypot(p.x - cp.x, (p.y || 0) + 1 - cp.y, p.z - cp.z), i]);
    const near = new Set(dist.filter(([d]) => d <= NEAR_M).sort((a, b) => a[0] - b[0]).slice(0, NEAR_MAX).map(([, i]) => i));
    levels.near = levels.mid = levels.far = 0;
    let far = 0;
    for (const [d, i] of dist) {
      const p = people[i], y0 = p.y || 0, b = bob ? 0.012 * Math.sin(t * 2.4 + p.phase) : 0;
      let f = figures.get(i);
      if (near.has(i)) {
        if (!f) { f = makeFigure({ ...p, scale }); figures.set(i, f); group.add(f.group); f.face(p.face); }
        f.group.visible = true; f.group.position.set(p.x, y0 + b, p.z); f.group.rotation.y = p.ry || 0;
        f.pose(p.sit ? 'sit' : p.pose, t, { sit: p.sit, turn: p.turn });
        for (const m of Object.values(parts)) m.setMatrixAt(i, hide);
        levels.near++;
        continue;
      }
      if (f) f.group.visible = false;
      if (d <= FAR_M) {
        const lift = (p.sit ? SEAT : 0.55) * scale, ry = p.ry || 0;
        Q.setFromEuler(E.set(0, ry, 0)); S.setScalar(scale);
        M.compose(P.set(p.x, y0 + lift + 0.35 * scale + b, p.z), Q, S); parts.torso.setMatrixAt(i, M);
        M.compose(P.set(p.x, y0 + lift + 1.02 * scale + b, p.z), Q, S); parts.head.setMatrixAt(i, M);
        if (p.hair !== 'bald' || p.hat) parts.hair.setMatrixAt(i, M.compose(P.set(p.x, y0 + lift + 1.04 * scale + b, p.z), Q, S)); else parts.hair.setMatrixAt(i, hide);
        const side = (sx) => new THREE.Vector3(sx, 0, 0).applyAxisAngle(UPV, ry);
        for (const [m, sx] of [[parts.legL, -0.09], [parts.legR, 0.09]]) {
          const o = side(sx);
          if (p.sit) {                                         // thigh forward on the seat, shin down
            const f = new THREE.Vector3(0, 0, 0.2).applyAxisAngle(UPV, ry);
            m.setMatrixAt(i, M.compose(P.set(p.x + o.x + f.x, y0 + (SEAT - 0.03) * scale, p.z + o.z + f.z), Q2.setFromEuler(E.set(Math.PI / 2, ry, 0, 'YXZ')), S));
          } else m.setMatrixAt(i, M.compose(P.set(p.x + o.x * scale, y0 + 0.28 * scale + b, p.z + o.z * scale), Q, S));
        }
        for (const [m, sx] of [[parts.armL, -0.27], [parts.armR, 0.27]]) {
          const o = side(sx);
          m.setMatrixAt(i, M.compose(P.set(p.x + o.x * scale, y0 + lift + 0.24 * scale + b, p.z + o.z * scale), Q, S));
        }
        pos.set([0, -999, 0], i * 3);
        levels.mid++;
      } else {
        for (const m of Object.values(parts)) m.setMatrixAt(i, hide);
        pos.set([p.x, y0 + ((p.sit ? SEAT : 0.55) + 0.6) * scale, p.z], i * 3); far++;
        levels.far++;
      }
    }
    for (const m of Object.values(parts)) m.instanceMatrix.needsUpdate = true;
    pgeo.attributes.position.needsUpdate = true;
    return levels;
  }
  return { group, people, update, levels };
}
