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

// specs/023: an act is a catalogue act, or face:<face>, pose:<pose>, look:<direction>
export function actOk(name, catalog = CATALOG) {
  if (typeof name !== 'string') return false;
  if ((catalog.acts || []).includes(name)) return true;
  const m = /^([a-z]+):(.+)$/.exec(name); if (!m) return false;
  const allowed = (catalog.act_prefixes || {})[m[1]];
  const list = typeof allowed === 'string' ? catalog[allowed] : allowed;
  return Array.isArray(list) && list.includes(m[2]);
}
const spans = (x) => Array.isArray(x) && x.every((r) => Array.isArray(r) && r.length === 2 && r[0] < r[1]);

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
      if (c.act !== undefined) {
        if (!Array.isArray(c.act)) bad('act is a list of [seconds, act]');
        for (const a of c.act) {
          if (!Array.isArray(a) || typeof a[0] !== 'number' || a[0] < 0 || a[0] >= s.dur) bad(`act time ${a && a[0]} outside the scene (0–${s.dur} s)`);
          if (!actOk(a[1], catalog)) bad(`unknown act "${a[1]}"`);
        }
      }
      if (c.talk !== undefined && !(spans(c.talk) && c.talk.every(([a, b]) => a >= 0 && b <= s.dur + 1e-9))) bad('talk is [[t0, t1], …] inside the scene');
      if (c.path !== undefined) {
        if (c.pose !== 'walk') bad('path needs pose "walk"');
        if (!(Array.isArray(c.path) && c.path.length >= 2 && c.path.every((p, k) => Array.isArray(p) && p.length === 3 && (k === 0 || p[0] > c.path[k - 1][0])))) bad('path is [[seconds, x, z], …] in time order');
      }
      if (c.swap !== undefined && !(c.swap && typeof c.swap === 'object' && (c.act || []).some((a) => a[1] === 'swap'))) bad('swap is a look {hoodie, hair, hat, glasses} with an act "swap"');
      if (c.blink !== undefined && c.blink !== false && !(c.blink && Array.isArray(c.blink.every) && c.blink.every.length === 2 && c.blink.every[0] > 0 && c.blink.every[0] <= c.blink.every[1])) bad('blink is false or {every: [a, b]} seconds');
    }
    if (s.move !== undefined && s.move !== 'auto') {
      const type = typeof s.move === 'string' ? s.move : s.move && s.move.type;
      if (!has(catalog.moves || [], type)) bad(`unknown move "${type}"`);
      if (typeof s.move === 'object' && s.move.speed !== undefined && !(s.move.speed > 0)) bad('move.speed must be > 0');
    }
    if (s.light !== undefined && ![-1, 0, 1].includes(s.light)) bad('light is -1 (key from the left), 0 (soft) or 1 (from the right)');
    if (s.frame !== undefined && s.frame !== 'auto' && !(s.frame && s.frame.x >= 0 && s.frame.x <= 1 && s.frame.y >= 0 && s.frame.y <= 1)) bad('frame is "auto" or {x, y} in 0–1');
    if (s.trans !== undefined) { if (!has(catalog.trans || [], s.trans)) bad(`unknown trans "${s.trans}"`); if (s.trans === 'fade' && ++fades > FADES_MAX) bad(`more than ${FADES_MAX} fades in the film`); }
    if (s.crowd && !(Number.isInteger(s.crowd.n) && s.crowd.n >= 0 && s.crowd.n <= CROWD_MAX)) bad(`crowd.n must be 0–${CROWD_MAX}`);
    for (const g of s.gfx || []) {
      if (!has(catalog.gfx, g.type)) bad(`unknown gfx "${g.type}"`);
      if (g.icon !== undefined && !has(catalog.icons || [], g.icon)) bad(`unknown icon "${g.icon}"`);
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

// specs/023: the camera move of a scene. 'auto' (the default) draws one from the style's measures for the scene's shot
// scale (template.json → motion.cam_by_scale), seeded by the scene id, so the same table gives the same film.
const seedOf = (id) => { let h = 5381; for (const ch of String(id)) h = (h * 33 + ch.charCodeAt(0)) | 0; return h >>> 0; };
const between = (r, lo, hi) => lo + (hi - lo) * r;
export function moveOf(scene, template = null, catalog = CATALOG) {
  const m = scene.move;
  if (m && typeof m === 'object') return { type: m.type, speed: m.speed ?? null, drift: m.drift ?? null };
  if (typeof m === 'string' && m !== 'auto') return { type: m, speed: null };
  const scale = (catalog.cams[camName(scene.cam)] || {}).scale;
  const b = template && template.motion && template.motion.cam_by_scale && template.motion.cam_by_scale[scale];
  if (!b) return { type: 'still', speed: null };
  const r = mulberry(seedOf(scene.id));
  if (r() >= b.moving) return { type: 'still', speed: null };
  if (castOf(scene).some((c) => c.pose === 'walk') && r() < 0.6) return { type: 'follow', speed: b.drift_px_s ? between(r(), ...b.drift_px_s) : 20 };
  // a push or pull also drifts a little, as the reference's dolly does (T065: motion720 counts shifts, not zoom)
  const drift = () => (b.drift_px_s ? between(r(), b.drift_px_s[0] * 0.5, b.drift_px_s[0]) : 6) * (r() < 0.5 ? -1 : 1);
  if (r() < (b.push || 0) / b.moving) return { type: 'push', speed: b.zoom_pct_s ? between(r(), ...b.zoom_pct_s) : 2, drift: drift() };
  if (r() < 0.5) return { type: 'pull', speed: b.zoom_pct_s ? between(r(), ...b.zoom_pct_s) : 2, drift: drift() };
  return { type: 'drift-h', speed: b.drift_px_s ? between(r(), ...b.drift_px_s) : 16 };
}

export function plan(scenes, cues = [], catalog = CATALOG, template = null) {
  check(scenes, catalog);
  let t = 0; const timed = [], SHOTS = [], CARDS = [], CAST = [], MOVES = [];
  for (const s of scenes) {
    const t0 = R(t), t1 = R(t + s.dur), move = moveOf(s, template, catalog);
    const acts = castOf(s).reduce((n, c) => n + (c.act || []).length, 0);
    timed.push({ ...s, t0, t1, _move: move }); SHOTS.push([t0, t1, s.set, s.id]); CARDS.push(...cardsOf(s, t0));
    CAST.push([t0, t1, s.id, castOf(s).length]); MOVES.push([t0, t1, s.id, move.type, acts]);
    t += s.dur;
  }
  const DUR = R(t);
  // cues as rows [t0, t1, text] or as the studio's cues.json objects {t0, t1, text}
  const CUES = (cues || []).map((c) => (Array.isArray(c) ? c : [c.t0, c.t1, c.text]))
    .map(([a, b, x]) => [R(a), R(b), String(x)]).filter(([a, b]) => b > a && a < DUR);
  return { DUR, SHOTS, CARDS, CUES, CAST, MOVES, scenes: timed };
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
