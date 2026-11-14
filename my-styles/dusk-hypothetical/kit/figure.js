// Figures of the Dusk Hypothetical kit (specs/022 R3), from the proof frame's figure(): sphere head ≈ 1/3 of the
// height, dot eyes, no nose or ears, hoodie with hood and drawstrings, two-segment limbs with round knee and elbow
// joints, ball hands, matte plastic. Limbs are rebuilt from joint points each pose() call, so walking and turning are
// pure functions of t. No DOM needed: node tests build figures too.
import * as THREE from 'three';

export const SKIN = '#e2d6ee';            // lavender in the violet light (proof round 8)
export const INK = '#120c1a';
export const SEAT = 0.6;                  // seat top of the kit's chairs and benches (proof round 1)
const UP = new THREE.Vector3(0, 1, 0);
const V = (x, y, z) => new THREE.Vector3(x, y, z);

const MATS = new Map();
export function mat(color, rough = 0.9, emissive, ei = 1) {
  const k = `${color}|${rough}|${emissive || ''}|${ei}`;
  if (!MATS.has(k)) MATS.set(k, new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: 0, ...(emissive ? { emissive, emissiveIntensity: ei } : {}) }));
  return MATS.get(k);
}
const inkMat = new THREE.MeshBasicMaterial({ color: INK });
const GEO = {
  limb: new THREE.CylinderGeometry(1, 1, 1, 10), joint: new THREE.SphereGeometry(1, 12, 8),
  head: new THREE.SphereGeometry(0.34, 40, 28), eye: new THREE.SphereGeometry(0.042, 12, 8),
  brow: new THREE.BoxGeometry(0.11, 0.016, 0.01), mouth: new THREE.TorusGeometry(0.045, 0.008, 6, 18, Math.PI),
  line: new THREE.BoxGeometry(0.08, 0.012, 0.01), blush: new THREE.SphereGeometry(0.05, 10, 8),
  drop: new THREE.SphereGeometry(0.035, 10, 8), o: new THREE.TorusGeometry(0.035, 0.01, 6, 18),
};

// ---------- poses: joint points in the figure's frame (y up, z forward), for side sx = -1 (left) / +1 (right) ----------
// legs(sx, t) → {lift, hip, knee, ankle}; arms(sx, lift, t) → {elbow, hand}; head pitch in radians
const LEGS = {
  stand: (sx) => ({ lift: 0.55, hip: V(sx * 0.08, 0.55, 0), knee: V(sx * 0.08, 0.3, 0.03), ankle: V(sx * 0.08, 0.06, 0) }),
  sit: (sx, t, seat = SEAT) => ({ lift: seat, hip: V(sx * 0.1, seat + 0.02, 0), knee: V(sx * 0.12, seat + 0.03, 0.34), ankle: V(sx * 0.13, Math.max(0.06, seat - 0.29), 0.4) }),
  walk: (sx, t) => {
    const ph = t * Math.PI * 2 * 1.6 + (sx > 0 ? Math.PI : 0), s = Math.sin(ph), lift = 0.55 + 0.012 * Math.abs(Math.cos(ph));
    return { lift, hip: V(sx * 0.08, lift, 0), knee: V(sx * 0.08, 0.31 + 0.03 * Math.max(0, s), 0.03 + 0.11 * s), ankle: V(sx * 0.08, 0.06 + 0.06 * Math.max(0, s), 0.16 * s - 0.02) };
  },
};
const ARMS = {
  rest: (sx, L, t, sit) => sit ? { elbow: V(sx * 0.27, L + 0.24, 0.08), hand: V(sx * 0.19, L + 0.1, 0.26) } : { elbow: V(sx * 0.28, L + 0.22, 0), hand: V(sx * 0.27, L - 0.02, 0.04) },
  swing: (sx, L, t) => { const s = Math.sin(t * Math.PI * 2 * 1.6 + (sx > 0 ? 0 : Math.PI)); return { elbow: V(sx * 0.28, L + 0.22, 0.06 * s), hand: V(sx * 0.27, L - 0.01, 0.04 + 0.14 * s) }; },
  hold: (sx, L) => ({ elbow: V(sx * 0.27, L + 0.25, 0.14), hand: V(sx * 0.09, L + 0.3, 0.3) }),
  low: (sx, L) => ({ elbow: V(sx * 0.27, L + 0.2, 0.1), hand: V(sx * 0.13, L + 0.17, 0.27) }),
  point: (sx, L, t, sit) => sx > 0 ? { elbow: V(0.3, L + 0.44, 0.2), hand: V(0.32, L + 0.54, 0.5) } : ARMS.rest(sx, L, t, sit),
  cheer: (sx, L) => ({ elbow: V(sx * 0.36, L + 0.7, 0.02), hand: V(sx * 0.3, L + 0.98, 0.06) }),
  shrug: (sx, L) => ({ elbow: V(sx * 0.36, L + 0.28, 0.06), hand: V(sx * 0.44, L + 0.46, 0.14) }),
};
// pose name → legs, arms, held item, head pitch
export const POSES = {
  stand: { legs: 'stand', arms: 'rest' },
  sit: { legs: 'sit', arms: 'rest' },
  walk: { legs: 'walk', arms: 'swing' },
  'hold-phone': { legs: 'stand', arms: 'hold', item: 'phone', pitch: 0.35 },
  'hold-book': { legs: 'stand', arms: 'hold', item: 'book', pitch: 0.3 },
  'hold-bag': { legs: 'stand', arms: 'low', item: 'bag' },
  'hold-cup': { legs: 'stand', arms: 'hold', item: 'cup', pitch: 0.12 },
  'hold-paper': { legs: 'stand', arms: 'hold', item: 'paper', pitch: 0.25 },
  point: { legs: 'stand', arms: 'point' },
  cheer: { legs: 'stand', arms: 'cheer', pitch: -0.15 },
  shrug: { legs: 'stand', arms: 'shrug', tilt: 0.12 },
};
export const FACES = ['dot', 'half', 'wow', 'happy', 'blank', 'angry', 'sad', 'sweat'];
export const HAIR = ['bald', 'short', 'bun', 'curly'];
export const HATS = ['cap', 'beanie'];
export const ITEMS = ['phone', 'book', 'bag', 'cup', 'paper'];

// joint points of a pose at time t; sit: true seats any pose (legs from 'sit')
export function joints(name, t = 0, { sit = false, seat = SEAT } = {}) {
  const p = POSES[name]; if (!p) throw new Error(`unknown pose "${name}"`);
  const legsName = sit || name === 'sit' ? 'sit' : p.legs;
  const out = { legs: {}, arms: {}, item: p.item || null, pitch: p.pitch || 0, tilt: p.tilt || 0 };
  for (const sx of [-1, 1]) out.legs[sx] = LEGS[legsName](sx, t, seat);
  out.lift = out.legs[1].lift;
  for (const sx of [-1, 1]) out.arms[sx] = ARMS[p.arms](sx, out.lift, t, legsName === 'sit');
  out.shoulder = { [-1]: V(-0.22, out.lift + 0.48, 0), 1: V(0.22, out.lift + 0.48, 0) };
  return out;
}

// ---------- figure ----------
export function makeFigure({ hoodie = '#c0423e', strings = '#f4eef8', hair = 'bald', hairColor = '#4a2e22', hat = null, hatColor = '#2a2a3a', glasses = false, scale = 1 } = {}) {
  const group = new THREE.Group(); group.scale.setScalar(scale);
  const skin = mat(SKIN, 0.6), cloth = mat(hoodie, 0.95);
  const add = (geo, m, parent = group) => { const o = new THREE.Mesh(geo, m); o.castShadow = o.receiveShadow = true; parent.add(o); return o; };
  const body = new THREE.Group(); group.add(body);
  const neck = add(new THREE.CylinderGeometry(0.04, 0.04, 0.16, 10), skin, body);
  const torso = add(new THREE.CapsuleGeometry(0.23, 0.24, 6, 14), cloth, body);
  const hood = add(new THREE.TorusGeometry(0.12, 0.055, 10, 24), cloth, body); hood.rotation.x = Math.PI / 2 - 0.25;
  const pouch = add(new THREE.SphereGeometry(0.15, 16, 10), cloth, body); pouch.scale.set(1, 0.8, 0.7);
  const cords = [-1, 1].map(() => { const c = add(new THREE.CylinderGeometry(0.008, 0.008, 0.16, 6), mat(strings, 0.7), body); c.rotation.x = -0.15; return c; });
  const pocket = add(new THREE.BoxGeometry(0.26, 0.1, 0.03), mat(new THREE.Color(hoodie).multiplyScalar(0.82).getStyle(), 0.95), body); pocket.rotation.x = -0.12;
  // limbs: two segments each, joints, feet and hands
  const seg = () => add(GEO.limb, skin), ball = () => add(GEO.joint, skin);
  const L = {};
  for (const sx of [-1, 1]) L[sx] = { thigh: seg(), shin: seg(), knee: ball(), foot: ball(), upper: seg(), fore: seg(), elbow: ball(), hand: ball() };
  // head
  const head = new THREE.Group(); group.add(head);
  add(GEO.head, skin, head).position.y = 0.3;
  const face = new THREE.Group(); head.add(face);
  const fm = (geo, m = inkMat) => { const o = new THREE.Mesh(geo, m); face.add(o); return o; };
  const onHead = (x, y, lift = 0.006) => Math.sqrt(Math.max(0, 0.34 * 0.34 - x * x - (y - 0.3) ** 2)) + lift;   // z of the head surface
  const eyes = [-1, 1].map((sx) => { const e = fm(GEO.eye); e.position.set(sx * 0.12, 0.35, 0.325); return e; });
  const brows = [-1, 1].map((sx) => { const b = fm(GEO.brow); b.position.set(sx * 0.13, 0.47, onHead(0.13, 0.47)); return b; });
  const mouth = fm(GEO.mouth); mouth.position.set(0, 0.2, 0.335);
  const flat = fm(GEO.line); flat.position.set(0, 0.2, 0.335);
  const oMouth = fm(GEO.o); oMouth.position.set(0, 0.19, 0.333);
  const blush = [-1, 1].map((sx) => { const b = fm(GEO.blush, mat('#f2a0b4', 0.8)); b.position.set(sx * 0.2, 0.26, onHead(0.2, 0.26, 0)); b.scale.set(1, 0.6, 0.3); return b; });
  const drop = fm(GEO.drop, mat('#9ad0f0', 0.3)); drop.position.set(0.25, 0.46, onHead(0.25, 0.46, 0.01)); drop.scale.set(0.8, 1.3, 0.5);
  // hair, hats, glasses
  if (hair === 'short' || hair === 'bun' || hair === 'curly') {
    // shell tilted back: the hairline sits above the brows at the front, low at the back
    const sh = add(new THREE.SphereGeometry(0.355, 32, 20, 0, Math.PI * 2, 0, Math.PI * 0.42), mat(hairColor, 0.8), head); sh.position.set(0, 0.31, -0.02); sh.rotation.x = -0.42;
    if (hair === 'bun') add(new THREE.SphereGeometry(0.11, 16, 12), mat(hairColor, 0.8), head).position.set(0, 0.64, -0.12);
    if (hair === 'curly') for (let i = 0; i < 9; i++) { const a = i / 9 * Math.PI * 2; add(new THREE.SphereGeometry(0.085, 12, 8), mat(hairColor, 0.8), head).position.set(Math.cos(a) * 0.27, 0.52 + 0.04 * Math.sin(a * 3), Math.sin(a) * 0.27 - 0.04); }
  }
  if (hat === 'cap') {
    const cap = new THREE.Group(); cap.position.y = 0.31; cap.rotation.x = -0.42; head.add(cap);
    add(new THREE.SphereGeometry(0.355, 28, 16, 0, Math.PI * 2, 0, Math.PI * 0.4), mat(hatColor), cap);
    add(new THREE.CylinderGeometry(0.2, 0.2, 0.03, 20, 1, false, -Math.PI / 2, Math.PI), mat(hatColor), cap).position.set(0, 0.1, 0.3);
  } else if (hat === 'beanie') {
    const bn = new THREE.Group(); bn.position.y = 0.31; bn.rotation.x = -0.4; head.add(bn);
    add(new THREE.SphereGeometry(0.365, 28, 16, 0, Math.PI * 2, 0, Math.PI * 0.38), mat(hatColor), bn);
    const rim = add(new THREE.TorusGeometry(0.33, 0.04, 8, 28), mat(hatColor), bn); rim.position.y = 0.13; rim.rotation.x = Math.PI / 2;
    add(new THREE.SphereGeometry(0.06, 10, 8), mat(hatColor), bn).position.y = 0.39;
  }
  if (glasses) {
    for (const sx of [-1, 1]) { const g = fm(new THREE.TorusGeometry(0.07, 0.01, 6, 20)); g.position.set(sx * 0.12, 0.35, 0.335); }
    const br = fm(new THREE.BoxGeometry(0.1, 0.01, 0.01)); br.position.set(0, 0.36, 0.34);
  }
  // held items, built once and shown on demand; placed at the hands' midpoint
  const items = {};
  const ig = (name, build) => { const g = new THREE.Group(); build(g); g.visible = false; group.add(g); items[name] = g; };
  ig('phone', (g) => { add(new THREE.BoxGeometry(0.13, 0.22, 0.02), mat('#1c1626', 0.4), g); const s = add(new THREE.PlaneGeometry(0.11, 0.19), new THREE.MeshBasicMaterial({ color: '#7d9cc0' }), g); s.position.z = -0.011; s.rotation.y = Math.PI; g.rotation.x = -0.6; });
  ig('book', (g) => { add(new THREE.BoxGeometry(0.3, 0.03, 0.22), mat('#c8563e'), g); g.rotation.x = 0.9; });
  ig('bag', (g) => { add(new THREE.BoxGeometry(0.34, 0.26, 0.16), mat('#5a6a3a'), g).position.y = -0.1; });
  ig('cup', (g) => { add(new THREE.CylinderGeometry(0.06, 0.05, 0.13, 14), mat('#f0e6d8', 0.6), g); });
  ig('paper', (g) => { add(new THREE.BoxGeometry(0.22, 0.3, 0.005), mat('#f4efe4', 0.8), g); g.rotation.x = -0.5; });

  const limb = (o, p, q, r) => { o.position.copy(p).add(q).multiplyScalar(0.5); o.scale.set(r, p.distanceTo(q), r); o.quaternion.setFromUnitVectors(UP, q.clone().sub(p).normalize()); };
  const place = (o, p, r, sy = 1, sz = 1) => { o.position.copy(p); o.scale.set(r, r * sy, r * sz); };
  let held = null, last = null;
  const fig = {
    group, head, items,
    // set the pose at time t; opts: {sit, seat, turn, tilt} (radians) → returns the joints used
    pose(name = 'stand', t = 0, opts = {}) {
      const j = joints(name, t, opts); last = j;
      const lift = j.lift;
      neck.position.set(0, lift + 0.64, 0); torso.position.set(0, lift + 0.35, 0);
      hood.position.set(0, lift + 0.6, -0.02); pouch.position.set(0, lift + 0.6, -0.13); pocket.position.set(0, lift + 0.22, 0.225);
      cords.forEach((c, i) => c.position.set((i ? 1 : -1) * 0.05, lift + 0.5, 0.21));
      for (const sx of [-1, 1]) {
        const g = j.legs[sx], a = j.arms[sx], l = L[sx], sh = j.shoulder[sx];
        limb(l.thigh, g.hip, g.knee, 0.045); place(l.knee, g.knee, 0.05); limb(l.shin, g.knee, g.ankle, 0.04);
        place(l.foot, V(g.ankle.x, g.ankle.y - 0.02, g.ankle.z + 0.05), 0.065, 0.8, 1.3);
        limb(l.upper, sh, a.elbow, 0.033); place(l.elbow, a.elbow, 0.036); limb(l.fore, a.elbow, a.hand, 0.031); place(l.hand, a.hand, 0.07);
      }
      head.position.set(0, lift + 0.72, 0);
      head.rotation.set(j.pitch + (opts.nod || 0), opts.turn || 0, j.tilt + (opts.tilt || 0), 'YXZ');
      fig.hold(opts.hold === undefined ? j.item : opts.hold);
      return j;
    },
    // show one held item (or none) between the hands
    hold(item) {
      if (held) items[held].visible = false; held = item && items[item] ? item : null;
      if (held && last) {
        const m = last.arms[-1].hand.clone().add(last.arms[1].hand).multiplyScalar(0.5);
        if (held === 'bag') m.y -= 0.04;
        items[held].position.copy(m).add(V(0, 0.03, 0.03)); items[held].visible = true;
      }
      return fig;
    },
    face(name = 'dot') {
      if (!FACES.includes(name)) throw new Error(`unknown face "${name}"`);
      const lid = name === 'half', happy = name === 'happy';
      eyes.forEach((e, i) => {
        const sx = i ? 1 : -1;
        e.scale.set(name === 'wow' ? 1.35 : name === 'blank' ? 0.7 : 1, lid ? 0.32 : happy ? 0.3 : name === 'wow' ? 1.6 : name === 'blank' ? 0.7 : 1.25, 0.3);
        e.position.y = lid ? 0.33 : 0.35;
        const b = brows[i]; b.visible = name !== 'blank';
        b.position.y = lid ? 0.4 : name === 'wow' ? 0.52 : 0.47; b.position.z = onHead(0.13, b.position.y);
        b.rotation.z = lid ? sx * 0.06 : name === 'angry' ? sx * 0.45 : name === 'sad' ? -sx * 0.4 : name === 'wow' ? 0 : -sx * 0.16;
      });
      mouth.visible = ['dot', 'half', 'happy', 'sad', 'sweat'].includes(name);
      mouth.rotation.z = name === 'sad' ? 0 : Math.PI + (lid ? 0.25 : 0);
      mouth.position.set(lid ? 0.04 : 0, name === 'sad' ? 0.16 : 0.2, 0.335);
      mouth.scale.setScalar(happy ? 1.5 : 1);
      flat.visible = name === 'blank' || name === 'angry';
      oMouth.visible = name === 'wow';
      blush.forEach((b) => (b.visible = happy));
      drop.visible = name === 'sweat';
      return fig;
    },
    // world-space height of the top of the head (for tests and framing)
    get joints() { return last; },
  };
  fig.pose('stand'); fig.face('dot');
  return fig;
}

// head-to-height ratio of the standing figure (style rule: ≈ 1/3)
export const HEAD_RATIO = 0.68 / (0.55 + 0.72 + 0.3 + 0.34);
