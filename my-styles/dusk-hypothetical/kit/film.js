// Film kit entry (specs/022, contracts/kit-api.md): a page writes a scene table and calls film({scenes}); this
// builds the frame for any t and exports the library's page contract and specs/020's film-page contract:
// DUR, SHOTS, CARDS, CUES, TEXTS(t), render(t), READY, and reads CLEAN and SUBJECT on every frame.
import * as THREE from 'three';
import { makeStage } from './stage.js';
import { plan, sceneAt, camName, CATALOG, mulberry, parseAct } from './plan.js';
import { SETS } from './sets/index.js';
import * as parts from './sets/parts.js';
import { makeFigure, makeItem, joints, itemAt } from './figure.js';
import { actState, blinkOn, talkOn, breath, riseOf, blackAt, streakAt, throwPath, RELEASE } from './acting.js';
import { makeCrowd, lookOf } from './crowd.js';
import { place, frameX, CAMS, otsPair } from './camera.js';
const CAMS_TARGET = Object.fromEntries(Object.entries(CAMS).map(([k, v]) => [k, v.target]));
import { drawGfx, drawCue, area, SERIF, SANS } from './graphics.js';

export { plan, CATALOG };
const D2R = Math.PI / 180;
const SET_CACHE = 4;                     // sets kept built at once (least recently used goes)

async function readJSON(url) {
  try { const r = await fetch(url); return r.ok ? await r.json() : null; } catch { return null; }
}

export async function film({ scenes, cues = './cues.json', hero, custom = {}, size } = {}) {
  // hero costume: the film's channel snapshot (channel attach), else the kit default (FR-015)
  if (!hero) {
    const snap = await readJSON('./channel.json');
    hero = snap && snap.film && snap.film.hero;
    if (!hero) console.warn('[kit] no hero in ./channel.json: using the kit default; set it with "channel set <channel> hero …"');
  }
  hero = { ...CATALOG.hero_default, ...(hero || {}) };
  const cueRows = typeof cues === 'string' ? (await readJSON(cues)) || [] : cues || [];
  // the style's measures (specs/023): copied into the film's kit by "kit use"; beside the kit in my-styles
  const template = (await readJSON(new URL('./template.json', import.meta.url))) || (await readJSON(new URL('../template.json', import.meta.url)));
  // specs/027: what the plan needs to know of each set (outdoors, room): the kit's sets export `info`; a film's custom
  // set says it on its builder function (custom.busstop.outdoor = true), else it counts as indoors, with a warning
  const info = {};
  for (const [n, m] of Object.entries(SETS)) if (m.info) info[n] = m.info;
  for (const [n, fn] of Object.entries(custom)) {
    if (fn.outdoor === undefined) console.warn(`[kit] custom set "${n}" does not say outdoor: true/false; counted as indoors`);
    info[`custom:${n}`] = { outdoor: !!fn.outdoor, room: fn.room };
  }
  const P = plan(scenes, cueRows, CATALOG, template, info);
  for (const n of P.NOTES) console.warn('[kit]', n);
  const RISE = riseOf(template);
  Object.assign(window, { DUR: P.DUR, SHOTS: P.SHOTS, CARDS: P.CARDS, CUES: P.CUES, CAST: P.CAST, MOVES: P.MOVES, CRAFT: P.CRAFT });

  const stage = makeStage(size || [innerWidth, innerHeight]);
  const A = { ...area(stage.W, stage.H), under: stage.ctx };
  const { scene, cam, octx: ctx } = stage;

  // ---------- sets (built on demand, a few kept) ----------
  const built = new Map();
  function getSet(name) {
    if (built.has(name)) { const s = built.get(name); built.delete(name); built.set(name, s); return s; }
    const maker = name.startsWith('custom:') ? custom[name.slice(7)] : SETS[name] && SETS[name].build;
    if (!maker) throw new Error(`set "${name}" has no builder (custom sets go in film({custom: {name: fn}}))`);
    const s = maker({ THREE, parts }); s.group.visible = false; scene.add(s.group); built.set(name, s);
    while (built.size > SET_CACHE) {
      const [old, o] = built.entries().next().value; built.delete(old); scene.remove(o.group);
      o.group.traverse((m) => { if (m.geometry) m.geometry.dispose(); });
    }
    return s;
  }

  // ---------- figures: the hero, extras by seed, a soft foreground shoulder ----------
  const heroFig = makeFigure({ hoodie: hero.hoodie, strings: hero.strings, hair: hero.hair, hat: hero.hat, glasses: hero.glasses });
  scene.add(heroFig.group);
  const extras = new Map();
  // an extra's look comes from its seed; the scene may override hoodie, hair, hat, glasses
  const extra = (seed, c = {}) => {
    const over = {}; for (const k of ['hoodie', 'hair', 'hat', 'glasses']) if (c[k] != null) over[k] = c[k];
    const key = `${seed}|${JSON.stringify(over)}`;
    if (!extras.has(key)) { const f = makeFigure({ ...lookOf(seed, 0), ...over }); scene.add(f.group); extras.set(key, f); }
    return extras.get(key);
  };
  const shoulder = makeFigure({ hoodie: '#5a4a9a', hair: 'short', hairColor: '#1c1420' }); scene.add(shoulder.group);
  const crowds = new Map();
  const endFigs = new Map();                 // the closing card's cast (specs/023)
  const swaps = new Map();                   // people after a state swap, by their new look
  const swapFig = (c) => {
    const base = c.who === 'hero' ? { hoodie: hero.hoodie, strings: hero.strings, hair: hero.hair, hat: hero.hat, glasses: hero.glasses }
      : { ...lookOf(Number(c.who.slice(6)), 0), ...Object.fromEntries(['hoodie', 'hair', 'hat', 'glasses'].filter((k) => c[k] != null).map((k) => [k, c[k]])) };
    const look = { ...base, ...c.swap }, key = `${c.who}|${JSON.stringify(look)}`;
    if (!swaps.has(key)) { const f = makeFigure(look); scene.add(f.group); swaps.set(key, f); }
    return swaps.get(key);
  };

  function castPlace(s, set, c, i, used) {
    const a = set.anchors; let slot;
    if (c.at) slot = { x: c.at[0], y: c.at[2] ?? 0, z: c.at[1], ry: (c.ry ?? 0) * D2R, sit: c.pose === 'sit' || !!c.sit };
    else if (c.who === 'hero') {
      const sit = c.pose === 'sit' || c.sit;
      const h = sit && a.heroSeat ? a.heroSeat : a.hero;
      slot = { x: h.x, y: h.y || 0, z: h.z, ry: h.ry || 0, sit: !!sit, seat: h.seat };
    } else {
      const free = (a.extras || []).filter((e) => !used.some((u) => Math.hypot(u.x - e.x, u.z - e.z) < 0.3));
      slot = free[0] || { x: (i % 2 ? 1 : -1) * (1 + i * 0.6), y: 0, z: -1 - i * 0.4, ry: 0 };
      slot = { ...slot, sit: c.pose === 'sit' || !!c.sit || !!slot.sit };
    }
    if (c.ry != null && !c.at) slot = { ...slot, ry: c.ry * D2R };
    if (c.dx || c.dz) slot = { ...slot, x: slot.x + (c.dx || 0), z: slot.z + (c.dz || 0) };
    return slot;
  }

  // ---------- specs/027: who holds what, and thrown items ----------
  const KINDS = CATALOG.act_kinds || {};
  const pa = (a) => { const p = parseAct(a[1]); return p && !p.prefix ? { t: a[0], ...p, spec: KINDS[p.base] || {} } : null; };
  const actsOf = (c) => (c.act || []).map(pa).filter(Boolean);
  // the item cast[i] holds at lt: undefined keeps the pose's own item; null is empty hands
  function heldAt(cast, i, lt) {
    const ev = [];
    for (const a of actsOf(cast[i])) {
      const item = a.item ?? a.spec.item;
      if (a.base === 'give') ev.push([a.t, item], [a.t + a.spec.dur / 2, null]);
      else if (a.base === 'throw') ev.push([a.t, item], [a.t + RELEASE, null]);
      else if (a.base === 'carry') ev.push([a.t, item]);
    }
    cast.forEach((o, k) => { if (k !== i) for (const a of actsOf(o)) if (a.who === i) {
      if (a.base === 'give') ev.push([a.t + a.spec.dur / 2, a.item ?? a.spec.item]);
      if (a.base === 'throw') ev.push([a.t + RELEASE + 0.7, a.item ?? a.spec.item]);   // caught at the end of the flight
    } });
    let item = cast[i].item;
    for (const [t, it] of ev.sort((x, y) => x[0] - y[0])) if (t <= lt) item = it;
    return item;
  }
  // a pair act aimed at cast[i] makes it answer: take for give, the same high five
  function incoming(cast, i, lt) {
    let best = null;
    cast.forEach((o, k) => { if (k !== i) for (const a of actsOf(o)) if (a.who === i && (a.base === 'give' || a.base === 'high-five') && a.t <= lt && lt - a.t <= a.spec.dur + 0.35)
      if (!best || a.t > best.t) best = { name: a.base === 'give' ? 'take' : 'high-five', local: lt - a.t, t: a.t }; });
    return best;
  }
  const flying = new Map();                  // thrown items, one per throw
  const worldOf = (f, j, item, hand) => { f.group.updateMatrixWorld(true); return f.group.localToWorld(itemAt(j, item, hand)); };

  let boxes = [];
  function render(t) {
    const s = sceneAt(P.scenes, Math.max(0, Math.min(t, P.DUR)));
    const lt = Math.max(0, t - s.t0), k = Math.min(1, lt / s.dur);
    const set = getSet(s.set);
    for (const [, o] of built) o.group.visible = o === set;
    const [fn, ff] = set.fog || [8, 24]; scene.fog.near = fn; scene.fog.far = ff;   // big places see further
    stage.grade(s.mood || 'dusk', { ...(set.grade || {}), ...(s.grade || {}) });   // set default, then the scene
    if (s.mood === 'alarm') {                // the alarm light pulses red about once a second (v02 strip S097; TEMPLATE.md §10)
      const pulse = 0.7 + 0.3 * Math.sin(t * Math.PI * 2 * 1.1);
      stage.lights.front.intensity *= pulse; stage.lights.rim.intensity *= pulse; stage.lights.hemi.intensity *= 0.85 + 0.15 * pulse;
    }

    // cast
    for (const fl of flying.values()) fl.g.visible = false;
    const used = [], shown = new Set(), heads = [], streaks = [];
    (s.cast || []).forEach((c, i) => {
      // a state swap (act 'swap', specs/023): from its time on the person wears cast[].swap; a light streak covers the change
      const swapAt = ((c.act || []).find((a) => a[1] === 'swap') || [])[0];
      const swapped = swapAt != null && c.swap && lt >= swapAt;
      const f = swapped ? swapFig(c) : c.who === 'hero' ? heroFig : extra(Number(c.who.slice(6)), c);
      if (swapAt != null) streaks.push({ at: swapAt, fig: f });
      const slot = castPlace(s, set, c, i, used); used.push(slot);
      f.group.visible = true; shown.add(f);
      f.group.position.set(slot.x, slot.y || 0, slot.z); f.group.rotation.y = slot.ry || 0;
      f.group.scale.setScalar(c.scale || 1);
      const pose = c.pose === 'sit' ? 'sit' : c.pose || (slot.sit ? 'sit' : 'stand');
      // walking along a path (specs/023): position from the path at lt, facing the way it goes
      if (c.path) {
        const P0 = c.path, k2 = P0.findIndex((q) => q[0] > lt);
        const [a, b] = k2 <= 0 ? (k2 === 0 ? [P0[0], P0[0]] : [P0.at(-2), P0.at(-1)]) : [P0[k2 - 1], P0[k2]];
        const u = b[0] > a[0] ? Math.min(1, Math.max(0, (lt - a[0]) / (b[0] - a[0]))) : 1;
        f.group.position.set(a[1] + (b[1] - a[1]) * u, slot.y || 0, a[2] + (b[2] - a[2]) * u);
        if (b[1] !== a[1] || b[2] !== a[2]) f.group.rotation.y = Math.atan2(b[1] - a[1], b[2] - a[2]);
        slot.x = f.group.position.x; slot.z = f.group.position.z; slot.ry = f.group.rotation.y;
      }
      // acting (specs/023, acting.js): act list, blinking, breathing, talking under the person's bubbles
      const seed = c.who === 'hero' ? 1 : Number(c.who.slice(6)) + 2;
      const st = actState(c.act || [], lt, RISE, { face: c.face });
      const talk = c.talk || (s.gfx || []).filter((g) => g.type === 'bubble' && g.who === i)
        .map((g) => [g.at ?? 0, Math.min((g.at ?? 0) + 1.2, g.until ?? s.dur)]);
      // specs/027: a body or pair act (own, or answering a partner's) replaces the pose while it plays
      const body = st.body || incoming(s.cast, i, lt);
      const held = heldAt(s.cast, i, lt);
      const j = f.pose(body ? body.name : pose, body ? body.local : lt, { sit: slot.sit && !(body && ['run', 'jump', 'fall', 'push', 'carry'].includes(body.name)), seat: slot.seat, turn: (c.turn || 0) * D2R + st.turn, tilt: (c.tilt || 0) * D2R + st.tilt,
        nod: (c.nod || 0) * D2R + st.pitch, hold: held !== undefined ? held : c.hold, hand: c.hand, breath: breath(seed, t),
        mix: st.arms && !body ? { from: st.from, to: st.arms, w: st.w, wave: st.wave }
          : (!body && held && (pose === 'stand' || pose === 'sit') ? { to: 'hold', w: 1 } : null) });
      if (j.hop) f.group.position.y += j.hop * (c.scale || 1);
      // thrown items fly on their own from the hand at the release to the partner's hands or 4 m ahead on the ground
      for (const a of actsOf(c)) {
        if (a.base !== 'throw') continue;
        const key = `${s.id}|${i}|${a.t}`, item = a.item ?? a.spec.item;
        if (!flying.has(key)) { const g = makeItem(item); scene.add(g); flying.set(key, { g }); }
        const fl = flying.get(key);
        const from = worldOf(f, joints('throw', RELEASE), item, 'right');
        let to;
        if (a.who != null && s.cast[a.who]) {
          const ps = castPlace(s, set, s.cast[a.who], a.who, []);
          to = new THREE.Vector3(ps.x, (ps.y || 0) + 0.95, ps.z);
        } else {
          const fy = f.group.rotation.y; to = new THREE.Vector3(f.group.position.x + Math.sin(fy) * 4, 0.12, f.group.position.z + Math.cos(fy) * 4);
        }
        const fp = throwPath(lt, a.t, from.toArray(), to.toArray());
        fl.g.visible = fp.state === 'air' || (fp.state === 'ground' && a.who == null);
        fl.g.position.fromArray(fp.p); fl.g.rotation.set(lt * 6, lt * 4, 0);
      }
      const hand = worldOf(f, j, held || c.hold || j.item || 'ball', c.hand);
      f.face(st.face || c.face || 'dot', { blink: c.blink !== false && blinkOn(seed, t, (c.blink && c.blink.every) || [2, 5]), talk: talkOn(talk, lt) });
      const head = new THREE.Vector3(0, (j.lift + 1.02) * (c.scale || 1), 0).applyAxisAngle(new THREE.Vector3(0, 1, 0), slot.ry || 0).add(f.group.position);
      heads.push({ head, facing: slot.ry || 0, who: c.who, hand });
    });
    heroFig.group.visible = shown.has(heroFig);
    for (const f of extras.values()) f.group.visible = shown.has(f);
    for (const f of swaps.values()) f.group.visible = shown.has(f);

    // camera on the subject (cast[subject] or the hero or the first cast member); empty shots frame the hero anchor
    const camOpts = typeof s.cam === 'object' ? s.cam : {};
    const subj = heads[camOpts.subject ?? -1] || heads.find((h) => h.who === 'hero') || heads[0] ||
      { head: new THREE.Vector3(set.anchors.hero.x, (set.anchors.hero.y || 0) + 1.57, set.anchors.hero.z), facing: set.anchors.hero.ry || 0 };
    // specs/023: the scene's camera move, where the subject sits, and the side the light comes from, all seeded by the scene
    const rand = mulberry([...s.id].reduce((h, ch) => (h * 33 + ch.charCodeAt(0)) | 0, 7) >>> 0);
    const scale = (CATALOG.cams[camName(s.cam)] || {}).scale;
    const fx = frameX(s.frame, scale, template, rand);
    const raking = (template && template.light && template.light.raking) ?? 0.55;
    const lightSide = s.light ?? (rand() < raking ? (rand() < 0.5 ? -1 : 1) : 0);
    // specs/027: the hands camera frames the subject's hands and item instead of the head
    const target = (CAMS_TARGET[camName(s.cam)] === 'hands' && subj.hand) ? subj.hand : subj.head;
    // specs/027: over the shoulder of a real partner when the shot has two or more people
    // only when the subject faces the partner (within 70°): side by side, a real shoulder would show the back of a head
    const near = camName(s.cam) === 'ots' && heads.length >= 2
      ? heads.filter((h) => h !== subj).sort((a, b) => a.head.distanceTo(subj.head) - b.head.distanceTo(subj.head))[0] : null;
    const faces = (h, o) => { const d = o.head.clone().sub(h.head); d.y = 0; return d.lengthSq() > 1e-6 && (Math.sin(h.facing) * d.x + Math.cos(h.facing) * d.z) / d.length() > Math.cos(70 * D2R); };
    const partner = near && faces(subj, near) ? near : null;
    const cp = partner ? otsPair(cam, subj.head, partner.head, camOpts.side ?? 1, set.room, { facing: subj.facing })
      : place(cam, camName(s.cam), target, subj.facing, { ...camOpts, move: s._move, lt, dur: s.dur, fx }, k, set.room);
    stage.focus(cp.focus, cp.aper); stage.aim(new THREE.Vector3(subj.head.x, 0, subj.head.z), lightSide);
    // closing card (TEMPLATE.md §9): the episode's cast as real figures in a row along the bottom of the picture,
    // facing the camera, popping in one by one, each with a small act; the card's 2D parts draw over them
    const end = (s.gfx || []).find((g) => g.type === 'end-choice' && lt >= (g.at ?? 0));
    for (const f of endFigs.values()) f.group.visible = false;
    let endFocus = 0;
    const stool = set.group.getObjectByName('stool'); if (stool) stool.visible = !end;
    if (end) {
      const list = end.cast || ['#d9b23a', '#3f9a9a', '#c0423e', '#7a5cc0', '#4f8f4a', '#d9608c'];
      // each figure stands on the floor where the view through the bottom of the picture meets it, a third of the picture high
      const onFloor = (nx) => {
        const p = new THREE.Vector3(nx, -0.46, 0.5).unproject(cam), dir = p.sub(cam.position).normalize();   // feet above the subtitle band
        if (dir.y > -0.02) return null;
        return cam.position.clone().addScaledVector(dir, -cam.position.y / dir.y);
      };
      list.forEach((look, i) => {
        const key = typeof look === 'string' ? look : JSON.stringify(look);
        if (!endFigs.has(key)) { const f = makeFigure(typeof look === 'string' ? { hoodie: look } : look); scene.add(f.group); endFigs.set(key, f); }
        const f = endFigs.get(key), born = (end.at ?? 0) + 0.25 + i * 0.12, u = Math.min(1, Math.max(0, (lt - born) / 0.18));
        if (u <= 0) return;
        const nx = list.length > 1 ? -0.62 + (1.24 * i) / (list.length - 1) : 0;
        const p0 = onFloor(nx); if (!p0) return;
        const dist = p0.distanceTo(cam.position), vis = 2 * dist * Math.tan(THREE.MathUtils.degToRad(cam.fov) / 2);
        f.group.visible = true; f.group.position.copy(p0); f.group.position.y += 0.15 * (1 - u) * (1 - u);
        f.group.rotation.y = Math.atan2(cam.position.x - p0.x, cam.position.z - p0.z); f.group.scale.setScalar((0.24 * vis) / 1.95);
        endFocus = dist;
        const act = ['wave', 'cheer', 'raise-hand', 'shrug-up', 'point', 'hands-face'][i % 6];
        const st = actState([[born + 0.2, act]], lt, RISE);
        f.pose('stand', lt, { mix: st.arms ? { to: st.arms, w: st.w, wave: st.wave } : null, breath: breath(i + 40, t) });
        f.face(['happy', 'dot', 'wow', 'half'][i % 4], { blink: blinkOn(i + 40, t) });
      });
    }
    if (endFocus) stage.focus(endFocus, 2.5);           // the closing card's figures are sharp
    // over the shoulder: the hero is the soft shoulder in front when the hero is in the shot but not its subject
    const heroFront = cp.shoulder && subj.who !== 'hero' && heroFig.group.visible;
    shoulder.group.visible = !!cp.shoulder && !heroFront;
    if (cp.shoulder) {
      const f = heroFront ? heroFig : shoulder;
      f.group.position.set(cp.shoulder.x, cp.shoulder.y - 1.6, cp.shoulder.z); f.group.rotation.y = cp.shoulderFacing;
      if (!heroFront) f.pose('stand');
    }

    // crowd (slots already taken by the cast are left out)
    for (const [, cr] of crowds) cr.group.visible = false;
    // window.SUBJECT (specs/023): the motion check reads the cast only; crowds stay frozen in the style and are left out
    if (s.crowd && s.crowd.n > 0 && !window.SUBJECT) {
      const key = `${s.id}|${s.set}|${s.crowd.n}|${s.crowd.seed ?? 1}`;
      let cr = crowds.get(key);
      if (!cr) {
        const ca = set.anchors.crowd || {};
        const slots = ca.slots && ca.slots.filter((e) => !used.some((u) => Math.hypot(u.x - e.x, u.z - e.z) < 0.45) && Math.hypot(e.x - subj.head.x, e.z - subj.head.z) > 0.8);
        cr = makeCrowd({ n: s.crowd.n, slots, area: s.crowd.area || ca.area, seed: s.crowd.seed ?? 1 });
        scene.add(cr.group); crowds.set(key, cr);
        if (crowds.size > 6) { const [old, o] = crowds.entries().next().value; crowds.delete(old); scene.remove(o.group); }
      }
      cr.group.visible = true; cr.update(cam, lt);
    }

    stage.draw();
    // fades to black (at most two per film, closing an act)
    if (s.fade) {
      const f = s.fade === 'out' ? Math.min(1, Math.max(0, (lt - (s.dur - 0.6)) / 0.6)) : Math.max(0, 1 - lt / 0.6);
      if (f > 0) { ctx.fillStyle = `rgba(0,0,0,${f})`; ctx.fillRect(0, 0, stage.W, stage.H); }
    }
    // transitions into and out of this scene (specs/023, TEMPLATE.md §13): a dip is ≈ 0.12 s of black across the cut,
    // a fade goes to black and back over ≈ 0.27 s; the lengths come from template.json → transitions
    const TR = (template && template.transitions) || {};
    const black = blackAt(s, P.scenes[P.scenes.indexOf(s) + 1], lt, TR);
    if (black > 0) { stage.ctx.fillStyle = `rgba(0,0,0,${black})`; stage.ctx.fillRect(0, 0, stage.W, stage.H); }
    // the light-streak swap: a bright horizontal smear over the person for ≈ 0.15 s around the change (motion-depth §2.3)
    for (const st of streaks) {
      const a = streakAt(lt, st.at, TR); if (a <= 0) continue;
      const box = new THREE.Box3().setFromObject(st.fig.group), lo = box.min.clone().project(cam), hi = box.max.clone().project(cam);
      const y0 = (1 - Math.max(lo.y, hi.y)) / 2 * stage.H, y1 = (1 - Math.min(lo.y, hi.y)) / 2 * stage.H;
      const gr = stage.ctx.createLinearGradient(0, y0, 0, y1);
      gr.addColorStop(0, 'rgba(255,240,230,0)'); gr.addColorStop(0.5, `rgba(255,245,235,${0.95 * a})`); gr.addColorStop(1, 'rgba(255,240,230,0)');
      stage.ctx.fillStyle = gr; stage.ctx.fillRect(0, y0, stage.W, y1 - y0);
    }
    // graphics and subtitles, unless the tools ask for a clean frame (thumbnails)
    boxes = [];
    if (!window.CLEAN) {
      for (const g of s.gfx || []) {
        const at = g.at ?? 0, until = g.until ?? s.dur;
        if (lt < at || lt >= until) continue;
        let anchor;
        if (g.type === 'bubble' && g.who != null && heads[g.who]) {
          const v = heads[g.who].head.clone().add(new THREE.Vector3(0, 0.45, 0)).project(cam);
          anchor = [(v.x + 1) / 2 * stage.W + 40 * A.u * (g.left ? -1 : 1), Math.max(A.y0 + 90 * A.u, (1 - v.y) / 2 * stage.H)];
        }
        boxes.push(...drawGfx(ctx, g, lt - at, A, { anchor, cast3d: true }));
      }
      const cue = P.CUES.find(([a, b]) => t >= a && t < b);
      if (cue) drawCue(ctx, cue[2], A);          // subtitles are declared in CUES, not in TEXTS (tier 2 checks other text against them)
    }
  }

  window.render = render;
  window.TEXTS = () => boxes;
  window.KIT = { stage, plan: P, getSet, heroFig };
  await Promise.all([document.fonts.load(`40px ${SERIF}`), document.fonts.load(`40px ${SANS}`)]).catch(() => {});
  await document.fonts.ready;
  // build every set the film uses once, so the first frame of each shot is not slower than the rest
  for (const name of new Set(P.scenes.map((s) => s.set)).values()) if (built.size < SET_CACHE) getSet(name);
  render(0);
  window.READY = true;
  return window.KIT;
}
