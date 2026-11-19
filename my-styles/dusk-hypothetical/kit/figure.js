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

// narrow the lower half of a geometry (y < 0) toward `bottom` × the width
function taper(geo, bottom) {
  const g = geo.clone(), p = g.attributes.position, box = (g.computeBoundingBox(), g.boundingBox);
  for (let i = 0; i < p.count; i++) {
    const u = (p.getY(i) - box.min.y) / (box.max.y - box.min.y), k = bottom + (1 - bottom) * Math.min(1, u * 1.6);
    p.setX(i, p.getX(i) * k); p.setZ(i, p.getZ(i) * (0.92 + 0.08 * k));
  }
  g.computeVertexNormals(); return g;
}
const MATS = new Map();
export function mat(color, rough = 0.9, emissive, ei = 1) {
  const k = `${color}|${rough}|${emissive || ''}|${ei}`;
  if (!MATS.has(k)) MATS.set(k, new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: 0, ...(emissive ? { emissive, emissiveIntensity: ei } : {}) }));
  return MATS.get(k);
}
const inkMat = new THREE.MeshBasicMaterial({ color: INK });
const GEO = {
  limb: new THREE.CylinderGeometry(1, 1, 1, 10), joint: new THREE.SphereGeometry(1, 12, 8),
  head: new THREE.SphereGeometry(0.34, 40, 28), eye: new THREE.SphereGeometry(0.03, 12, 8),
  // specs/023 face (TEMPLATE.md §1): small features low on the sphere; lids and closed eyes are thin arcs
  brow: new THREE.BoxGeometry(0.075, 0.013, 0.01), mouth: new THREE.TorusGeometry(0.034, 0.007, 6, 18, Math.PI),
  line: new THREE.BoxGeometry(0.06, 0.01, 0.01), blush: new THREE.SphereGeometry(0.045, 10, 8),
  drop: new THREE.SphereGeometry(0.03, 10, 8), o: new THREE.TorusGeometry(0.026, 0.009, 6, 18),
  lid: new THREE.TorusGeometry(0.05, 0.006, 6, 16, Math.PI * 0.8), arc: new THREE.TorusGeometry(0.03, 0.006, 6, 16, Math.PI),
  lash: new THREE.BoxGeometry(0.03, 0.006, 0.006),
  halfEye: new THREE.CircleGeometry(0.04, 20, Math.PI, Math.PI),          // the lower half of an eye under a heavy lid
  glint: new THREE.CircleGeometry(0.011, 10), oFill: new THREE.CircleGeometry(0.024, 18),
  dMouth: new THREE.CircleGeometry(0.04, 20, Math.PI, Math.PI),            // an open smile: a dark half disc
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
  hug: (sx, L) => ({ elbow: V(sx * 0.32, L + 0.36, 0.24), hand: V(-sx * 0.08, L + 0.42, 0.46) }),   // arms round someone in front
  // specs/023 acts (acting.js): one arm up, both hands to the face
  'raise-hand': (sx, L, t, sit) => sx > 0 ? { elbow: V(0.31, L + 0.62, 0.06), hand: V(0.27, L + 0.93, 0.1) } : ARMS.rest(sx, L, t, sit),
  'hands-face': (sx, L) => ({ elbow: V(sx * 0.25, L + 0.42, 0.24), hand: V(sx * 0.12, L + 0.8, 0.3) }),
};
ARMS.wave = ARMS['raise-hand'];
ARMS['shrug-up'] = ARMS.shrug;
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
  hug: { legs: 'stand', arms: 'hug', pitch: 0.1 },
};
export const FACES = ['dot', 'half', 'wow', 'happy', 'blank', 'angry', 'sad', 'sweat'];
export const HAIR = ['bald', 'short', 'bun', 'curly'];
export const HATS = ['cap', 'beanie'];
export const ITEMS = ['phone', 'book', 'bag', 'cup', 'paper'];

// joint points of a pose at time t; sit: true seats any pose (legs from 'sit')
export function joints(name, t = 0, opts = {}) {
  const { sit = false, seat = SEAT, mix = null } = opts;
  const p = POSES[name]; if (!p) throw new Error(`unknown pose "${name}"`);
  const legsName = sit || name === 'sit' ? 'sit' : p.legs;
  const out = { legs: {}, arms: {}, item: p.item || null, pitch: p.pitch || 0, tilt: p.tilt || 0 };
  for (const sx of [-1, 1]) out.legs[sx] = LEGS[legsName](sx, t, seat);
  out.lift = out.legs[1].lift;
  const sitting = legsName === 'sit';
  for (const sx of [-1, 1]) out.arms[sx] = ARMS[p.arms](sx, out.lift, t, sitting);
  // specs/023: blend the arms toward an act (or another pose's arms); mix = {from, to, w, wave}
  if (mix && mix.to) {
    const armsOf = (n) => ARMS[n] ? n : (POSES[n] ? POSES[n].arms : p.arms);
    const from = mix.from ? armsOf(mix.from) : p.arms, to = armsOf(mix.to);
    for (const sx of [-1, 1]) {
      const a = ARMS[from](sx, out.lift, t, sitting), b = ARMS[to](sx, out.lift, t, sitting);
      out.arms[sx] = { elbow: a.elbow.clone().lerp(b.elbow, mix.w), hand: a.hand.clone().lerp(b.hand, mix.w) };
      if (mix.wave && sx > 0) out.arms[sx].hand.x += 0.08 * mix.wave;
    }
  }
  out.shoulder = { [-1]: V(-0.22, out.lift + 0.48, 0), 1: V(0.22, out.lift + 0.48, 0) };
  return out;
}

// ---------- figure ----------
export function makeFigure({ hoodie = '#c0423e', strings = '#f4eef8', hair = 'bald', hairColor = '#4a2e22', hat = null, hatColor = '#2a2a3a', glasses = false, scale = 1, girl = null } = {}) {
  girl = girl ?? (hair === 'bun' || hair === 'curly');     // blush and lashes code girls (visual §9.5)
  const group = new THREE.Group(); group.scale.setScalar(scale);
  const skin = mat(SKIN, 0.6), cloth = mat(hoodie, 0.95);
  const add = (geo, m, parent = group) => { const o = new THREE.Mesh(geo, m); o.castShadow = o.receiveShadow = true; parent.add(o); return o; };
  const body = new THREE.Group(); group.add(body);
  const neck = add(new THREE.CylinderGeometry(0.04, 0.04, 0.16, 10), skin, body);
  // a short tapered hoodie (TEMPLATE.md §2): narrower than the 022 sack, wider at the chest than at the hem
  // a flat-fronted block with rounded sides, a touch narrower at the hem (v01 shot cell #20, v06 shot cell #20)
  const torso = add(new THREE.CylinderGeometry(0.205, 0.185, 0.46, 20, 1), cloth, body); torso.scale.set(1, 1, 0.62);
  const shoulders = [-1, 1].map(() => add(new THREE.SphereGeometry(0.075, 14, 10), cloth, body));
  const hem = add(new THREE.CylinderGeometry(0.19, 0.19, 0.045, 20, 1), mat(new THREE.Color(hoodie).multiplyScalar(0.85).getStyle(), 0.95), body); hem.scale.set(1, 1, 0.62);
  const hood = add(new THREE.TorusGeometry(0.1, 0.04, 10, 24), cloth, body); hood.rotation.x = Math.PI / 2 - 0.25;   // a small hood behind the neck
  const cords = [-1, 1].map(() => { const c = add(new THREE.CylinderGeometry(0.008, 0.008, 0.16, 6), mat(strings, 0.7), body); c.rotation.x = -0.15; return c; });
  const pocket = add(new THREE.BoxGeometry(0.2, 0.08, 0.03), mat(new THREE.Color(hoodie).multiplyScalar(0.82).getStyle(), 0.95), body); pocket.rotation.x = -0.12;
  // limbs: two segments each, joints, feet and hands
  const seg = (m = skin) => add(GEO.limb, m), ball = (m = skin) => add(GEO.joint, m);
  const L = {};
  // sleeves in the hoodie colour down to the wrist, white ball hands, white stick legs (visual §5.1; v06 S169)
  for (const sx of [-1, 1]) L[sx] = { thigh: seg(), shin: seg(), knee: ball(), foot: ball(), upper: seg(cloth), fore: seg(cloth), elbow: ball(cloth), hand: ball() };
  // head
  const head = new THREE.Group(); group.add(head);
  add(GEO.head, skin, head).position.y = 0.3;
  const face = new THREE.Group(); head.add(face);
  const fm = (geo, m = inkMat) => { const o = new THREE.Mesh(geo, m); face.add(o); return o; };
  const onHead = (x, y, lift = 0.006) => Math.sqrt(Math.max(0, 0.34 * 0.34 - x * x - (y - 0.3) ** 2)) + lift;   // z of the head surface
  const EY = 0.27, EX = 0.1, MY = 0.16;                       // eyes and mouth in the lower half of the sphere
  const eyes = [-1, 1].map((sx) => { const e = fm(GEO.eye); e.position.set(sx * EX, EY, onHead(sx * EX, EY, -0.004)); return e; });
  // the smug half-lid: a long thin lid stroke over the lower half of the eye (v04 shot cell #39)
  const lids = [-1, 1].map((sx) => { const l = fm(GEO.lid); l.position.set(sx * EX, EY - 0.008, onHead(sx * EX, EY, 0.005)); l.rotation.z = Math.PI * 0.1; l.scale.set(1.2, 0.35, 1); return l; });
  const halves = [-1, 1].map((sx) => { const h = fm(GEO.halfEye); h.position.set(sx * EX, EY + 0.004, onHead(sx * EX, EY, 0.003)); h.scale.set(1.15, 0.75, 1); return h; });
  const glints = [-1, 1].map((sx) => { const g = fm(GEO.glint, new THREE.MeshBasicMaterial({ color: '#ffffff' })); g.position.set(sx * EX + 0.012, EY + 0.014, onHead(sx * EX, EY, 0.009)); return g; });
  const arcs = [-1, 1].map((sx) => { const a = fm(GEO.arc); a.position.set(sx * EX, EY - 0.012, onHead(sx * EX, EY, 0.004)); return a; });
  const shut = [-1, 1].map((sx) => { const l = fm(GEO.line); l.position.set(sx * EX, EY, onHead(sx * EX, EY, 0.004)); l.scale.set(0.75, 1, 1); return l; });
  const lashes = girl ? [-1, 1].map((sx) => { const l = fm(GEO.lash); l.position.set(sx * (EX + 0.04), EY + 0.03, onHead(sx * (EX + 0.04), EY + 0.03, 0.004)); l.rotation.z = sx * 0.6; return l; }) : [];
  const brows = [-1, 1].map((sx) => { const b = fm(GEO.brow); b.position.set(sx * 0.105, 0.35, onHead(0.105, 0.35)); return b; });
  const mouth = fm(GEO.mouth); mouth.position.set(0, MY, onHead(0, MY));
  const flat = fm(GEO.line); flat.position.set(0, MY, onHead(0, MY)); flat.scale.set(0.7, 1, 1);
  const oMouth = fm(GEO.oFill, mat('#5a1424', 0.8)); oMouth.position.set(0, MY - 0.005, onHead(0, MY - 0.005, 0.003)); oMouth.scale.set(0.8, 1.05, 1);
  const dMouth = fm(GEO.dMouth); dMouth.position.set(0, MY + 0.012, onHead(0, MY, 0.003)); dMouth.scale.set(1, 0.7, 1);
  const blush = [-1, 1].map((sx) => { const b = fm(GEO.blush, mat('#f2a0b4', 0.8)); b.position.set(sx * 0.17, 0.2, onHead(0.17, 0.2, 0)); b.scale.set(1, 0.6, 0.3); return b; });
  const drop = fm(GEO.drop, mat('#9ad0f0', 0.3)); drop.position.set(0.22, 0.38, onHead(0.22, 0.38, 0.01)); drop.scale.set(0.8, 1.3, 0.5);
  // every face piece faces outward from the head's centre
  face.children.forEach((o) => { const n = o.position.clone().sub(V(0, 0.3, 0)).normalize(); o.quaternion.multiply(new THREE.Quaternion().setFromUnitVectors(V(0, 0, 1), n)); });
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
      neck.position.set(0, lift + 0.64, 0); torso.position.set(0, lift + 0.3, 0); hem.position.set(0, lift + 0.085, 0);
      shoulders.forEach((o, i) => o.position.set((i ? 1 : -1) * 0.2, lift + 0.48, 0));
      const br = opts.breath || 1; torso.scale.set(br, 1, 0.62 * br);       // specs/023: breathing (acting.js)
      hood.position.set(0, lift + 0.58, -0.07); pocket.position.set(0, lift + 0.2, 0.125);
      cords.forEach((c, i) => c.position.set((i ? 1 : -1) * 0.05, lift + 0.44, 0.13));
      for (const sx of [-1, 1]) {
        const g = j.legs[sx], a = j.arms[sx], l = L[sx], sh = j.shoulder[sx];
        limb(l.thigh, g.hip, g.knee, 0.045); place(l.knee, g.knee, 0.05); limb(l.shin, g.knee, g.ankle, 0.04);
        place(l.foot, V(g.ankle.x, g.ankle.y - 0.02, g.ankle.z + 0.05), 0.065, 0.8, 1.3);
        limb(l.upper, sh, a.elbow, 0.037); place(l.elbow, a.elbow, 0.038); limb(l.fore, a.elbow, a.hand, 0.035); place(l.hand, a.hand, 0.065);
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
    // face(name, {blink, talk}): blink closes the eyes to lines; talk opens the mouth (acting.js)
    face(name = 'dot', { blink = false, talk = false } = {}) {
      if (!FACES.includes(name)) throw new Error(`unknown face "${name}"`);
      const lid = name === 'half', happy = name === 'happy', wow = name === 'wow';
      eyes.forEach((e) => { e.visible = !blink && !happy && !lid; e.scale.set(wow ? 1.35 : name === 'blank' ? 0.8 : 1, wow ? 1.35 : 1, 0.3); });
      lids.forEach((l) => (l.visible = lid && !blink));             // the smug half-lid: a lid stroke over a half eye
      halves.forEach((h) => (h.visible = lid && !blink));
      glints.forEach((g) => (g.visible = wow && !blink));           // round eyes with a highlight when surprised (v09 strip S082)
      arcs.forEach((a) => (a.visible = happy && !blink));           // closed, upturned eyes
      shut.forEach((l) => (l.visible = !!blink));
      brows.forEach((b, i) => {
        const sx = i ? 1 : -1;
        b.visible = ['angry', 'sad', 'wow', 'sweat'].includes(name);  // brows only when the feeling needs them
        b.rotation.z = name === 'angry' ? sx * 0.5 : name === 'sad' || name === 'sweat' ? -sx * 0.4 : 0;
        b.position.y = wow ? 0.37 : 0.35;
      });
      const open = talk && name !== 'wow';
      mouth.visible = !open && ['dot', 'half', 'sad', 'sweat'].includes(name);
      dMouth.visible = !open && happy;                               // an open smile (v10 shot cell #5)
      mouth.rotation.z = name === 'sad' ? 0 : Math.PI + (lid ? 0.25 : 0);
      mouth.position.x = lid ? 0.035 : 0;
      mouth.scale.setScalar(happy ? 1.4 : 1);
      flat.visible = !open && (name === 'blank' || name === 'angry');
      oMouth.visible = wow || open;
      oMouth.scale.set(open ? 0.7 : 0.8, open ? 0.6 : 1.05, 1);
      blush.forEach((b) => (b.visible = girl));                    // blush codes girls only (visual §9.5)
      lashes.forEach((l) => (l.visible = !blink));
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
