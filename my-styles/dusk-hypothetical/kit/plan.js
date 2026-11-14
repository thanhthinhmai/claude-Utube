// Pure part of the film kit (specs/022 R2): scene table → DUR, SHOTS, CARDS, CUES, with every name checked against
// catalog.json. No three.js here, so node --test runs it. film.js uses it in the page.
import CATALOG from './catalog.json' with { type: 'json' };

export { CATALOG };
export const DUR_MIN = 1.1, DUR_MAX = 6;          // specs/020 rhythm rule: shots outside 1.1–6 s
export const CROWD_MAX = 5000, FADES_MAX = 2;
export const GRADE_LIMITS = { exposure: [0.6, 1.0], saturation: [0.85, 1.15] };
const GFX_TEXT = new Set(['counter', 'menu', 'diagram', 'bubble', 'stat', 'title', 'chapter', 'end-choice']);
const R = (x) => Math.round(x * 1000) / 1000;

export const camName = (cam) => (typeof cam === 'string' ? cam : cam && cam.name);
const castOf = (s) => s.cast || [];

// Throws Error("<scene id>: <reason>") on the first problem.
export function check(scenes, catalog = CATALOG) {
  if (!Array.isArray(scenes) || !scenes.length) throw new Error('scenes: at least one scene');
  const ids = new Set(); let fades = 0;
  const has = (list, x) => (Array.isArray(list) ? list.includes(x) : Object.hasOwn(list, x));
  scenes.forEach((s, i) => {
    const id = s && s.id;
    const bad = (why) => { throw new Error(`${id || '#' + (i + 1)}: ${why}`); };
    if (!id || typeof id !== 'string') bad('missing id');
    if (ids.has(id)) bad('duplicate id'); ids.add(id);
    if (!(typeof s.dur === 'number' && s.dur >= DUR_MIN && s.dur <= DUR_MAX)) bad(`dur ${s.dur} outside ${DUR_MIN}–${DUR_MAX} s`);
    if (!s.set || !(has(catalog.sets, s.set) || /^custom:[a-z0-9-]+$/.test(s.set))) bad(`unknown set "${s.set}"`);
    if (!has(catalog.cams, camName(s.cam))) bad(`unknown cam "${camName(s.cam)}"`);
    if (s.mood && !has(catalog.moods, s.mood)) bad(`unknown mood "${s.mood}"`);
    if (s.grade) {
      const { exposure, saturation } = s.grade;
      if (exposure != null && !(exposure >= GRADE_LIMITS.exposure[0] && exposure <= GRADE_LIMITS.exposure[1])) bad(`grade.exposure ${exposure} outside 0.6–1.0`);
      if (saturation != null && !(saturation >= GRADE_LIMITS.saturation[0] && saturation <= GRADE_LIMITS.saturation[1])) bad(`grade.saturation ${saturation} outside 0.85–1.15`);
    }
    for (const c of castOf(s)) {
      if (!(c.who === 'hero' || /^extra:\d+$/.test(c.who || ''))) bad(`unknown cast "${c.who}" (hero or extra:<seed>)`);
      if (c.pose && !has(catalog.poses, c.pose)) bad(`unknown pose "${c.pose}"`);
      if (c.face && !has(catalog.faces, c.face)) bad(`unknown face "${c.face}"`);
      if (c.hair && !has(catalog.hair, c.hair)) bad(`unknown hair "${c.hair}"`);
      if (c.hat && !has(catalog.hats, c.hat)) bad(`unknown hat "${c.hat}"`);
    }
    if (s.crowd && !(Number.isInteger(s.crowd.n) && s.crowd.n >= 0 && s.crowd.n <= CROWD_MAX)) bad(`crowd.n must be 0–${CROWD_MAX}`);
    for (const g of s.gfx || []) {
      if (!has(catalog.gfx, g.type)) bad(`unknown gfx "${g.type}"`);
      const at = g.at ?? 0, until = g.until ?? s.dur;
      if (!(at >= 0 && until <= s.dur + 1e-9 && at < until)) bad(`gfx "${g.type}" outside the scene (${at}–${until} s of ${s.dur} s)`);
      for (const t of textsOf(g)) if (t !== t.toUpperCase()) bad(`gfx "${g.type}" text must be caps: "${t}"`);
    }
    if (s.fade) { if (!['in', 'out'].includes(s.fade)) bad('fade is "in" or "out"'); if (++fades > FADES_MAX) bad(`more than ${FADES_MAX} fades in the film`); }
  });
}

// every caption a graphic puts on screen (bubbles are speech: caps rule does not apply to them)
export function textsOf(g) {
  if (g.type === 'bubble') return [];
  const out = [];
  for (const k of ['text', 'title', 'sub', 'label']) if (typeof g[k] === 'string' && g[k]) out.push(g[k]);
  for (const k of ['items', 'options']) if (Array.isArray(g[k])) for (const x of g[k]) if (typeof x === 'string') out.push(x);
  return out;
}
const captionOf = (g) => {
  if (g.type === 'counter') return [g.prefix || '', String(g.to ?? g.text ?? ''), g.suffix || ''].join('').trim() || null;
  const parts = g.type === 'bubble' ? [g.text] : textsOf(g);
  const s = parts.filter(Boolean).join(' · ');
  return s || null;
};

// CARDS rows of one scene that starts at t0: [t0, t1, id, text]
export function cardsOf(scene, t0) {
  const out = [];
  (scene.gfx || []).forEach((g, i) => {
    if (!GFX_TEXT.has(g.type)) return;
    const text = captionOf(g); if (!text) return;
    out.push([R(t0 + (g.at ?? 0)), R(t0 + (g.until ?? scene.dur)), g.id || `${scene.id}.${g.type}${i ? '.' + i : ''}`, text]);
  });
  return out;
}

export function plan(scenes, cues = [], catalog = CATALOG) {
  check(scenes, catalog);
  let t = 0; const timed = [], SHOTS = [], CARDS = [];
  for (const s of scenes) {
    const t0 = R(t), t1 = R(t + s.dur);
    timed.push({ ...s, t0, t1 }); SHOTS.push([t0, t1, s.set, s.id]); CARDS.push(...cardsOf(s, t0)); t += s.dur;
  }
  const DUR = R(t);
  const CUES = (cues || []).map(([a, b, x]) => [R(a), R(b), String(x)]).filter(([a, b]) => b > a && a < DUR);
  return { DUR, SHOTS, CARDS, CUES, scenes: timed };
}

// the scene on screen at time t (binary search; the last scene owns t = DUR)
export function sceneAt(timed, t) {
  let lo = 0, hi = timed.length - 1;
  if (t <= 0) return timed[0];
  if (t >= timed[hi].t0) return timed[hi];
  while (lo < hi) { const m = (lo + hi + 1) >> 1; if (timed[m].t0 <= t) lo = m; else hi = m - 1; }
  return timed[lo];
}

// seeded random numbers (same as the library's mulberry32), so kit modules need no import from /core
export function mulberry(seed) {
  return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}
