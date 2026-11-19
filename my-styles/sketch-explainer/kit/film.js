// @ts-check
// Film page of the Sketch Explainer kit (specs/028 T007, T012; contracts/kit-api.md).
// The page writes only a scene table and calls film({scenes}). This module draws sets, people, boards, signs,
// bubbles, cards and captions, runs the camera and the acting schedule, and fills the library's page contract:
// DUR, SHOTS, CARDS, TEXTS, CUES, render(t), READY, CLEAN; plus KIT_ERRORS, PEOPLE, BUBBLES for tier 1.
import { el, box, oval, circ, clamp01, lerp, INK } from './core.js';
import { makeChar, setChar, POSES, EXPRS } from './rig.js';
import { ROLES, ROLE_NAMES, narrator, extra } from './roles.js';
import { SETS, SET_NAMES, PART_NAMES, buildSet, DEFS } from './sets/index.js';
import { boardShape, boardText, signUI, bubbleUI, thinkUI, cardWorld, cardUI, captionUI, labelUI, BOARD_KINDS, BOARD_LOOKS } from './boards.js';
import { PROP_NAMES, propAt } from './props.js';
import { camFor, camAt, SIZES, MOVES } from './camera.js';
import { schedule, stateAt } from './acting.js';

export const CATALOG = {
  sets: SET_NAMES, parts: PART_NAMES, roles: ROLE_NAMES, poses: Object.keys(POSES), exprs: Object.keys(EXPRS),
  props: PROP_NAMES, boards: BOARD_KINDS, looks: BOARD_LOOKS, cams: SIZES, moves: MOVES, trans: ['cut', 'dissolve'],
};
/** gestures each base pose cycles through (pose-to-pose acting) */
export const GEST = { rest: ['rest', 'palm', 'rest', 'hips'], palm: ['palm', 'rest', 'raise', 'wide'], pointL: ['pointL', 'palm', 'pointL', 'hips'], pointR: ['pointR', 'palm', 'pointR', 'raise'],
  raise: ['raise', 'palm', 'rest'], up: ['up', 'raise', 'wide'], shrug: ['shrug', 'rest', 'palm'], chin: ['chin', 'rest', 'think'], wide: ['wide', 'palm', 'hips'], hips: ['hips', 'palm', 'rest'], think: ['think', 'chin', 'rest'], desk: ['desk'], hold: ['hold'] };
export const EXPR_ALT = { neutral: ['neutral', 'happy'], happy: ['happy', 'excited'], excited: ['excited', 'happy'], worried: ['worried', 'shocked'], shocked: ['shocked', 'worried'],
  deadpan: ['deadpan', 'smug'], smug: ['smug', 'happy'], proud: ['proud', 'beam'], beam: ['beam', 'happy'], calm: ['calm', 'happy'], angry: ['angry', 'deadpan'], sad: ['sad', 'worried'] };
const SYMBOLS = /^[!?$…♪.\s]{1,3}$/;

// ---------- names (pure) ----------
function lev(/** @type {string} */ a, /** @type {string} */ b) {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++) d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return d[a.length][b.length];
}
export function nearest(/** @type {string} */ name, /** @type {string[]} */ list) {
  let best = '', bd = 1e9; for (const x of list) { const v = lev(String(name), x); if (v < bd) { bd = v; best = x; } } return best;
}
/**
 * Check one scene against the catalogue. people: slugs the film has copied in.
 * @returns {{shot: string, kind: string, name: string, hint: string}[]}
 */
export function checkScene(/** @type {any} */ sc, cat = CATALOG, /** @type {string[]} */ people = [], /** @type {Record<string, any>} */ custom = {}) {
  /** @type {{shot: string, kind: string, name: string, hint: string}[]} */ const out = [];
  const bad = (/** @type {string} */ kind, /** @type {any} */ name, /** @type {string[]} */ list) => out.push({ shot: sc.id, kind, name: String(name), hint: list && list.length ? nearest(String(name), list) : '' });
  if (!sc.id) out.push({ shot: '?', kind: 'bad_value', name: 'id', hint: 'S001' });
  if (!(sc.dur > 0)) bad('bad_value', 'dur', []);
  if (!sc.card) {
    const set = sc.set;
    if (typeof set === 'string' && set.startsWith('custom:')) { if (!custom[set.slice(7)] && !Array.isArray(sc.custom)) bad('unknown_set', set, Object.keys(custom).map(k => 'custom:' + k)); else for (const [p] of (sc.custom || custom[set.slice(7)].parts || [])) if (!cat.parts.includes(p)) bad('unknown_part', p, cat.parts); }
    else if (!cat.sets.includes(set)) bad('unknown_set', set, cat.sets);
  }
  for (const c of sc.cast || []) {
    const w = String(c.who || '');
    if (w.startsWith('person:')) { if (!people.includes(w.slice(7))) bad('unknown_person', w, people.map(p => 'person:' + p)); }
    else if (!/^extra:\d+$/.test(w) && !cat.roles.includes(w)) bad('unknown_role', w, cat.roles);
    if (c.pose && !cat.poses.includes(c.pose)) bad('unknown_pose', c.pose, cat.poses);
    if (c.expr && !cat.exprs.includes(c.expr)) bad('unknown_expr', c.expr, cat.exprs);
  }
  for (const p of [...(sc.props || []), ...(sc.propsF || [])]) if (!cat.props.includes(p[0])) bad('unknown_prop', p[0], cat.props);
  if (sc.board) { if (!cat.boards.includes(sc.board.k)) bad('unknown_board', sc.board.k, cat.boards); if (sc.board.look && !cat.looks.includes(sc.board.look)) bad('unknown_look', sc.board.look, cat.looks); }
  if (sc.cam && sc.cam.size && !cat.cams.includes(sc.cam.size)) bad('unknown_cam', sc.cam.size, cat.cams);
  if (sc.cam && sc.cam.move && sc.cam.move !== 'auto' && !cat.moves.includes(sc.cam.move)) bad('unknown_move', sc.cam.move, cat.moves);
  if (sc.trans && !cat.trans.includes(sc.trans)) bad('unknown_trans', sc.trans, cat.trans);
  const n = (sc.cast || []).length;
  for (const b of sc.bub || []) if (!(b[0] >= 0 && b[0] < n)) bad('bad_value', 'bub who ' + b[0], []);
  if (sc.sign && !(sc.sign.who >= 0 && sc.sign.who < n)) bad('bad_value', 'sign who', []);
  return out;
}

// ---------- the page ----------
/** board look from the set when the scene does not say */
const LOOK_OF = { 'chalk-room': 'chalk-part', 'classroom': 'chalk-part', 'tv-room': 'tv', 'newsroom': 'screen', 'stage': 'screen', 'lab': 'tv' };
const BOARD_AT = { 'chalk-room': { x: 240, y: 150, w: 980, h: 520 }, 'classroom': { x: 240, y: 150, w: 980, h: 520 }, 'newsroom': { x: 1080, y: 110, w: 680, h: 420 }, 'stage': { x: 420, y: 60, w: 1080, h: 560 } };

const crowdMan = (/** @type {number} */ x, /** @type {number} */ y, /** @type {number} */ s, col = '#8d9499') =>
  `<g transform="translate(${x} ${y}) scale(${s})"><path d="M-112 148 Q-158 250 -150 462 Q-150 478 0 480 Q150 478 150 462 Q158 250 112 148 Q0 118 -112 148 Z" fill="${col}" stroke="${INK}" stroke-width="9"/><path d="${circ(0, 0, 165)}" fill="${col}" stroke="${INK}" stroke-width="9"/></g>`;

async function json(/** @type {string} */ url) { try { const r = await fetch(url); return r.ok ? await r.json() : null; } catch (_) { return null; } }

/**
 * @param {{scenes: any[], cues?: string|any[], hero?: any, custom?: Record<string, any>}} opts
 */
export async function film(opts) {
  const w = /** @type {any} */ (window);
  const scenes = opts.scenes || [], custom = opts.custom || {};
  // channel hero, people, cues
  const ch = await json('./channel.json');
  const hero = opts.hero || (ch && ch.film && ch.film.hero) || (ch && ch.hero) || {};
  const idx = (await json('./people/index.json')) || { people: [] };
  /** @type {Record<string, any>} */ const people = {};
  for (const p of idx.people || []) { try { const m = await import(`../people/${p.slug}/figure.js`); people[p.slug] = Object.assign({ id: p.slug }, m.default || m.figure); } catch (_) { /* reported by KIT_ERRORS */ } }
  w.PEOPLE = (idx.people || []).map((/** @type {any} */ p) => ({ slug: p.slug, hash: p.hash }));
  let cues = Array.isArray(opts.cues) ? opts.cues : await json(typeof opts.cues === 'string' ? opts.cues : './cues.json');
  w.CUES = Array.isArray(cues) ? cues : (cues && cues.cues) || null;

  // timeline
  let t = 0;
  const S = scenes.map((/** @type {any} */ sc, /** @type {number} */ i) => { const o = { sc, i, t0: t, t1: t + sc.dur }; t += sc.dur; return o; });
  w.DUR = +t.toFixed(3);
  w.SHOTS = S.map(o => [o.t0, o.t1, o.sc.card ? 'card' : String(o.sc.set), o.sc.id]);
  w.KIT_ERRORS = scenes.flatMap((/** @type {any} */ sc) => checkScene(sc, CATALOG, Object.keys(people), custom));
  const errShots = new Set(w.KIT_ERRORS.map((/** @type {any} */ e) => e.shot));

  // per scene: geometry, camera, events
  let prevMove = null;
  for (const o of S) {
    const sc = o.sc;
    const def = sc.card ? null : (String(sc.set).startsWith('custom:') ? { parts: sc.custom || (custom[String(sc.set).slice(7)] || {}).parts || [], fg: (custom[String(sc.set).slice(7)] || {}).fg, floor: sc.floor || (custom[String(sc.set).slice(7)] || {}).floor || 1000 } : SETS[sc.set]);
    const floor = sc.floor || (def && def.floor) || 1000;
    o.def = def; o.floor = floor;
    o.cast = (sc.cast || []).map((/** @type {any} */ c) => { const s = c.s || 0.6; return Object.assign({}, c, { s, y0: c.y != null ? c.y : (c.seat ? 380 : floor - 640 * s) }); });
    const look = (sc.board && sc.board.look) || LOOK_OF[/** @type {keyof typeof LOOK_OF} */ (sc.set)] || 'wb';
    o.board = sc.board ? Object.assign({ x: 240, y: 150, w: 980, h: 520 }, BOARD_AT[/** @type {keyof typeof BOARD_AT} */ (sc.set)] || {}, sc.board, { look }) : null;
    const fi = sc.cam && sc.cam.on != null ? sc.cam.on : 0, f = o.cast[fi];
    o.cam = camFor(sc, prevMove, f ? { x: f.x, y: f.y0, s: f.s } : null, o.board);
    prevMove = o.cam.move;
    o.events = schedule(Object.assign({}, sc, { cast: o.cast, board: o.board }));
  }

  // cards and bubbles for the tiers
  /** @type {any[]} */ const cards = [], bubbles = [];
  for (const o of S) {
    const sc = o.sc, id = sc.id;
    const add = (/** @type {number} */ a, /** @type {string} */ s) => { if (s) cards.push([+(o.t0 + a).toFixed(3), +o.t1.toFixed(3), id, s]); };
    if (sc.card) add(0.05, sc.card.big + (sc.card.small ? ' ' + sc.card.small : ''));
    if (o.board) { const b = o.board, a = b.at ?? 0.3; add(a, [b.title, b.text, b.sub, ...(b.rows || []), ...((b.items || []).map((/** @type {any} */ i) => i[0]))].filter(Boolean).join(' · ')); }
    if (sc.sign) add(sc.sign.at ?? 0.2, sc.sign.text + (sc.sign.sub ? ' ' + sc.sign.sub : ''));
    if (sc.cap) add(sc.cap[4] ?? 0.2, sc.cap[0] + (sc.cap[1] ? ' ' + sc.cap[1] : ''));
    for (const L of sc.lab || []) add(L[6] ?? 0.4, L[0] + (L[1] ? ' ' + L[1] : ''));
    for (const b of sc.bub || []) { const who = (sc.cast || [])[b[0]] || {}; bubbles.push([+(o.t0 + (b[2] ?? 0.3)).toFixed(3), +o.t1.toFixed(3), id, String(who.who), b[1], String(who.who).startsWith('person:')]); if (!SYMBOLS.test(b[1])) add(b[2] ?? 0.3, b[1]); }
  }
  w.CARDS = cards; w.BUBBLES = bubbles;
  w.SCENE_INFO = S.map(o => ({ id: o.sc.id, set: o.sc.card ? 'card' : String(o.sc.set), size: o.sc.card ? 'card' : o.cam.size, move: o.sc.card ? 'still' : o.cam.move, dur: o.sc.dur, events: o.sc.card ? 0 : o.events.length }));

  // DOM
  document.body.style.margin = '0'; document.body.style.background = '#000'; document.body.style.overflow = 'hidden';
  const style = document.createElement('style');
  style.textContent = `@font-face{font-family:Hand;src:url(${new URL('./Kalam-Bold.ttf', import.meta.url)})} html,body{width:100%;height:100%} svg{display:block}`;
  document.head.appendChild(style);
  const root = /** @type {SVGSVGElement} */ (el('svg', { id: 'root', width: '100%', height: '100%', viewBox: '0 0 1920 1080', preserveAspectRatio: 'xMidYMid meet' }, document.body));
  root.innerHTML = `<defs>${DEFS}<radialGradient id="cardBg" cx=".5" cy=".5" r=".75"><stop offset="0" stop-color="#3a3a42"/><stop offset="1" stop-color="#24242a"/></radialGradient>
    <radialGradient id="vig" cx=".5" cy=".46" r=".78"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#14100c" stop-opacity=".3"/></radialGradient></defs>
    <g id="worldA"></g><g id="worldB"></g><g id="ui"></g>`;
  const WA = /** @type {SVGGElement} */ (root.querySelector('#worldA')), WB = /** @type {SVGGElement} */ (root.querySelector('#worldB')), UI = /** @type {SVGGElement} */ (root.querySelector('#ui'));
  let cur = '';

  /** draw scene o at local time lt into group G; returns the view (for the UI) */
  function draw(/** @type {any} */ o, /** @type {number} */ lt, /** @type {SVGGElement} */ G) {
    const sc = o.sc, tt = o.t0 + lt;
    if (sc.card) { G.setAttribute('transform', ''); G.innerHTML = cardWorld(); return { P: (/** @type {number} */ x, /** @type {number} */ y) => [x, y], Z: 1 }; }
    const cam = camAt(o.cam, lt, sc.dur);
    G.setAttribute('transform', `translate(960 540) scale(${cam.z}) translate(${-cam.cx} ${-cam.cy})`);
    if (errShots.has(sc.id)) { G.setAttribute('transform', ''); G.innerHTML = `<path d="${box(0, 0, 1920, 1080)}" fill="#5a2020"/>`; return { P: (/** @type {number} */ x, /** @type {number} */ y) => [x, y], Z: 1 }; }
    const set = o.def ? buildSet(sc.set, { lt }, o.def) : { html: '', fg: '', floor: 1000 };
    const shadows = o.cast.filter((/** @type {any} */ c) => !c.seat).map((/** @type {any} */ c) => `<path d="${oval(c.x, c.y0 + 650 * c.s, 150 * c.s, 26 * c.s)}" fill="#000" opacity=".18" stroke="none"/>`).join('');
    const crowd = (sc.crowd || []).map((/** @type {any[]} */ q) => crowdMan(q[0], q[1], q[2], q[3])).join('');
    const props = (sc.props || []).map((/** @type {any[]} */ p) => propAt(p[0], p[1], p[2], p[3], p[4], lt)).join('');
    const propsF = (sc.propsF || []).map((/** @type {any[]} */ p) => propAt(p[0], p[1], p[2], p[3], p[4], lt)).join('');
    G.innerHTML = set.html + (o.board ? boardShape(o.board) : '') + props + crowd + shadows + '<g class="cast" stroke-linejoin="round" stroke-linecap="round"></g>' + set.fg + propsF +
      (sc.vig === 0 ? '' : `<path d="${box(-120, -120, 2160, 1320)}" fill="url(#vig)" stroke="none"/>`);
    const castG = /** @type {Element} */ (G.querySelector('.cast'));
    o.cast.forEach((/** @type {any} */ c, /** @type {number} */ i) => {
      const w0 = String(c.who);
      const cfg = w0 === 'narrator' ? narrator(hero) : w0.startsWith('extra:') ? extra(+w0.slice(6)) : w0.startsWith('person:') ? people[w0.slice(7)] : ROLES[/** @type {keyof typeof ROLES} */ (w0)] ? ROLES[/** @type {keyof typeof ROLES} */ (w0)]() : null;
      if (!cfg) return;
      let x = c.x, walk = 0, ph = 0;
      if (c.walk) { const [x0, x1, a = 0, b = sc.dur] = c.walk, u = clamp01((lt - a) / (b - a)); x = lerp(x0, x1, u); walk = u > 0 && u < 1 ? 1 : 0; ph = lt * 9; }
      else if (o.board && c.pose === 'pointL' && !c.still && lt < 0.8) { x = lerp(c.x + 160, c.x, lt / 0.8); walk = 1; ph = lt * 9; }   // a presenter steps in
      const hop = c.hop != null && lt > c.hop && lt < c.hop + 1.5 ? -Math.abs(Math.sin((lt - c.hop) * 6.3)) * 26 : 0;
      const g = GEST[/** @type {keyof typeof GEST} */ (c.pose || 'rest')] || GEST.rest, xa = EXPR_ALT[/** @type {keyof typeof EXPR_ALT} */ (c.expr || 'neutral')] || EXPR_ALT.neutral;
      const st = c.still || c.p2 ? { pose: c.p2 && lt >= (c.at || 0) ? c.p2 : (c.pose || 'rest'), poseFrom: c.p2 && lt >= (c.at || 0) ? (c.pose || 'rest') : undefined, poseK: c.p2 ? clamp01((lt - (c.at || 0)) / 0.35) : 1, expr: c.e2 && lt >= (c.at || 0) ? c.e2 : (c.expr || 'neutral'), blink: false }
        : stateAt(o.events, i, lt, { pose: c.pose || 'rest', expr: c.expr || 'neutral' }, g, xa);
      const talk = c.talk && lt >= c.talk[0] && lt <= c.talk[1] ? 0.35 + 0.3 * Math.sin(lt * 15) + 0.2 * Math.sin(lt * 23) : 0;
      const ch = makeChar(castG, Object.assign({}, cfg, { tag: '_' + i, seated: !!c.seat }));
      setChar(ch, { t: tt, x: c.seat ? (c.x ?? 960) : x, y: c.y0 + hop, s: c.seat ? (c.s || 0.8) : c.s, view: c.view, pose: c.seat ? 'desk' : st.pose, poseFrom: st.poseFrom, poseK: st.poseK,
        expr: st.expr, blink: st.blink, face: (c.face || 0) + (c.still ? 0 : 0.1 * Math.sin(lt * 0.9 + i * 1.7)), look: (c.look || 0) + (c.still ? 0 : 4 * Math.sin(lt * 0.6 + i)), talk, walk, walkPh: ph, tilt: c.tilt || 0 });
    });
    return { P: (/** @type {number} */ x, /** @type {number} */ y) => [(x - cam.cx) * cam.z + 960, (y - cam.cy) * cam.z + 540], Z: cam.z, cam };
  }

  function drawUI(/** @type {any} */ o, /** @type {number} */ lt, /** @type {any} */ view) {
    while (UI.firstChild) UI.removeChild(UI.firstChild);
    if (w.CLEAN) return;
    const sc = o.sc;
    if (sc.card) { cardUI(UI, sc.card, lt); return; }
    if (errShots.has(sc.id)) { const e = w.KIT_ERRORS.find((/** @type {any} */ x) => x.shot === sc.id); const tx = el('text', { x: 960, y: 540, 'font-family': 'Hand', 'font-size': 60, 'text-anchor': 'middle', fill: '#fff' }, UI); tx.textContent = `${sc.id}: ${e.kind} ${e.name}${e.hint ? ' → ' + e.hint : ''}`; return; }
    if (o.board) boardText(UI, view, o.board, lt);
    const head = (/** @type {any} */ c) => { const x = c.walk ? lerp(c.walk[0], c.walk[1], clamp01((lt - (c.walk[2] || 0)) / ((c.walk[3] || sc.dur) - (c.walk[2] || 0)))) : c.x; return { x, y: c.y0, s: c.s }; };
    if (sc.sign) { const c = o.cast[sc.sign.who]; if (c) { const h = head(c), [X, Y] = view.P(h.x, h.y + 250 * h.s); signUI(UI, view, sc.sign, X, Y, lt); } }
    for (const b of sc.bub || []) { const c = o.cast[b[0]]; if (!c || lt < (b[2] ?? 0.3)) continue; const h = head(c), side = h.x > 1200 ? -1 : 1, [X, Y] = view.P(h.x + side * 110 * h.s, h.y - 150 * h.s); bubbleUI(UI, b[1], X, Y, side, clamp01((lt - (b[2] ?? 0.3)) / 0.18)); }
    if (sc.think) { const c = o.cast[sc.think.who]; if (c) { const h = head(c), [X, Y] = view.P(h.x + 120 * h.s, h.y - 160 * h.s); thinkUI(UI, sc.think.picture || '', X, Y, clamp01((lt - (sc.think.at ?? 0.4)) / 0.8)); } }
    if (sc.cap) captionUI(UI, lt, sc.cap);
    for (const L of sc.lab || []) labelUI(UI, lt, L);
  }

  w.render = function (/** @type {number} */ time) {
    const o = S.find(x => time >= x.t0 && time < x.t1) || S[S.length - 1];
    if (!o) return;
    const lt = time - o.t0;
    let view;
    if (o.sc.trans === 'dissolve' && o.i > 0 && lt < 0.5) {
      const p = S[o.i - 1];
      draw(p, p.sc.dur - 0.001, WA); view = draw(o, lt, WB); WB.setAttribute('opacity', String(lt / 0.5)); WA.style.display = '';
    } else { WA.style.display = 'none'; WA.innerHTML = ''; view = draw(o, lt, WB); WB.setAttribute('opacity', '1'); }
    drawUI(o, lt, view);
    cur = o.sc.id;
  };
  w.TEXTS = function (/** @type {number} */ time) {
    w.render(time);
    return [...UI.querySelectorAll('text')].filter(e => (e.textContent || '').trim()).map((e, i) => { const r = e.getBoundingClientRect(); return { id: `${cur}-${i}`, text: e.textContent, x0: r.left, y0: r.top, x1: r.right, y1: r.bottom }; });
  };
  w.render(0);
  await document.fonts.load('40px Hand');
  await document.fonts.ready;
  w.READY = true;
}
