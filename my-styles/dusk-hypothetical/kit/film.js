// Film kit entry (specs/022, contracts/kit-api.md): a page writes a scene table and calls film({scenes}); this
// builds the frame for any t and exports the library's page contract and specs/020's film-page contract:
// DUR, SHOTS, CARDS, CUES, TEXTS(t), render(t), READY, and reads CLEAN and SUBJECT on every frame.
import * as THREE from 'three';
import { makeStage } from './stage.js';
import { plan, sceneAt, camName, CATALOG } from './plan.js';
import { SETS } from './sets/index.js';
import * as parts from './sets/parts.js';
import { makeFigure } from './figure.js';
import { makeCrowd, lookOf } from './crowd.js';
import { place } from './camera.js';
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
  const P = plan(scenes, cueRows);
  Object.assign(window, { DUR: P.DUR, SHOTS: P.SHOTS, CARDS: P.CARDS, CUES: P.CUES });

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

  let boxes = [];
  function render(t) {
    const s = sceneAt(P.scenes, Math.max(0, Math.min(t, P.DUR)));
    const lt = Math.max(0, t - s.t0), k = Math.min(1, lt / s.dur);
    const set = getSet(s.set);
    for (const [, o] of built) o.group.visible = o === set;
    const [fn, ff] = set.fog || [8, 24]; scene.fog.near = fn; scene.fog.far = ff;   // big places see further
    stage.grade(s.mood || 'dusk', { ...(set.grade || {}), ...(s.grade || {}) });   // set default, then the scene

    // cast
    const used = [], shown = new Set(), heads = [];
    (s.cast || []).forEach((c, i) => {
      const f = c.who === 'hero' ? heroFig : extra(Number(c.who.slice(6)), c);
      const slot = castPlace(s, set, c, i, used); used.push(slot);
      f.group.visible = true; shown.add(f);
      f.group.position.set(slot.x, slot.y || 0, slot.z); f.group.rotation.y = slot.ry || 0;
      f.group.scale.setScalar(c.scale || 1);
      const pose = c.pose === 'sit' ? 'sit' : c.pose || (slot.sit ? 'sit' : 'stand');
      const j = f.pose(pose, lt, { sit: slot.sit, seat: slot.seat, turn: (c.turn || 0) * D2R, tilt: (c.tilt || 0) * D2R, nod: (c.nod || 0) * D2R, hold: c.hold });
      f.face(c.face || 'dot');
      const head = new THREE.Vector3(0, (j.lift + 1.02) * (c.scale || 1), 0).applyAxisAngle(new THREE.Vector3(0, 1, 0), slot.ry || 0).add(f.group.position);
      heads.push({ head, facing: slot.ry || 0, who: c.who });
    });
    heroFig.group.visible = shown.has(heroFig);
    for (const f of extras.values()) f.group.visible = shown.has(f);

    // camera on the subject (cast[subject] or the hero or the first cast member); empty shots frame the hero anchor
    const camOpts = typeof s.cam === 'object' ? s.cam : {};
    const subj = heads[camOpts.subject ?? -1] || heads.find((h) => h.who === 'hero') || heads[0] ||
      { head: new THREE.Vector3(set.anchors.hero.x, (set.anchors.hero.y || 0) + 1.57, set.anchors.hero.z), facing: set.anchors.hero.ry || 0 };
    const cp = place(cam, camName(s.cam), subj.head, subj.facing, camOpts, k, set.room);
    stage.focus(cp.focus, cp.aper); stage.aim(new THREE.Vector3(subj.head.x, 0, subj.head.z));
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
        boxes.push(...drawGfx(ctx, g, lt - at, A, { anchor }));
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
