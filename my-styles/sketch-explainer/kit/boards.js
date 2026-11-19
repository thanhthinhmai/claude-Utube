// @ts-check
// Graphics as things inside the scene (specs/028 T010; style §4, §8): whiteboard, chalkboard, mounted TV, paper,
// hand-held signs, speech and thought bubbles, chapter cards, captions and arrow labels, big money-green numbers.
// Red and green carry meaning only: loss/danger red, money/growth green (style §3). Text lives in the UI layer so
// TEXTS(t) sees it, follows the camera through view.P / view.Z, shrinks to fit its box, and is hidden by CLEAN.
import { el, box, rrect, circ, slice, segOutline, clamp01, ease, lerp, LW, INK } from './core.js';

export const MEANING = { loss: '#c0584a', danger: '#c0584a', red: '#c0584a', money: '#4f9a5e', growth: '#4f9a5e', green: '#4f9a5e', blue: '#5b7fb0', grey: '#8d9499', gold: '#c9a64a' };
const col = (/** @type {string|undefined} */ c, d = '#4f9a5e') => (c && c in MEANING ? MEANING[/** @type {keyof typeof MEANING} */ (c)] : c || d);
export const BOARD_KINDS = ['num', 'bars', 'list', 'vs', 'pie', 'line'];
export const BOARD_LOOKS = ['wb', 'chalk', 'tv', 'paper', 'screen'];

/** board frame in the world layer */
export function boardShape(/** @type {any} */ b) {
  const { x, y, w, h } = b, look = b.look || 'wb';
  if (look === 'screen' || look === 'chalk-part') return '';
  if (look === 'chalk') return `<path d="${box(x - 24, y - 24, w + 48, h + 48)}" fill="#8a5f3a" stroke="none"/>` + segOutline([[x - 24, y - 24], [x + w + 24, y - 24], [x + w + 24, y + h + 24], [x - 24, y + h + 24]], LW * .6) + `<path d="${box(x, y, w, h)}" fill="#2f4038" stroke="none"/>`;
  if (look === 'tv') return `<path d="M${x + w / 2 - 40} ${y + h + 22} L${x + w / 2 - 30} ${y + h + 60} L${x + w / 2 + 30} ${y + h + 60} L${x + w / 2 + 40} ${y + h + 22} Z" fill="#3a3d44" stroke="none"/><path d="${rrect(x - 22, y - 22, w + 44, h + 44, 18)}" fill="#1b1d22" stroke="none"/>` + segOutline([[x - 22, y - 22], [x + w + 22, y - 22], [x + w + 22, y + h + 22], [x - 22, y + h + 22]], LW * .6) + `<path d="${box(x, y, w, h)}" fill="#151a26" stroke="none"/>`;
  if (look === 'paper') return `<g transform="rotate(-2 ${x + w / 2} ${y + h / 2})"><path d="${box(x + 14, y + 16, w, h)}" fill="#000" opacity=".2" stroke="none"/><path d="${box(x, y, w, h)}" fill="#f4f1ea" stroke="none"/>${segOutline([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], LW * .5)}</g>`;
  return `<path d="M${x + 60} ${y + h} L${x + 30} ${y + h + 230} M${x + w - 60} ${y + h} L${x + w - 30} ${y + h + 230}" fill="none" stroke="#6a5a48" stroke-width="12"/>` +
    `<path d="${box(x - 14, y - 14, w + 28, h + 28)}" fill="#b9bcc2" stroke="none"/>` + segOutline([[x - 14, y - 14], [x + w + 14, y - 14], [x + w + 14, y + h + 14], [x - 14, y + h + 14]], LW * .6) + `<path d="${box(x, y, w, h)}" fill="#fbfaf6" stroke="none"/>`;
}

/** text that shrinks to fit maxW (screen pixels) */
function fitText(/** @type {Element} */ parent, /** @type {any} */ a, /** @type {string} */ s, /** @type {number} */ maxW) {
  const e = el('text', a, parent); e.textContent = s;
  try { const L = /** @type {SVGTextElement} */ (e).getComputedTextLength(); if (L > maxW && L > 0) e.setAttribute('font-size', String(parseFloat(a['font-size']) * maxW / L)); } catch (_) { /* not laid out */ }
  return e;
}

/** board content in the UI layer. view: {P(x,y) → [X,Y], Z}; lt: seconds into the shot */
export function boardText(/** @type {Element} */ UI, /** @type {any} */ view, /** @type {any} */ b, /** @type {number} */ lt) {
  const at = b.at == null ? 0.3 : b.at; if (lt < at) return;
  const Z = view.Z, P = view.P, dark = ['chalk', 'tv', 'screen', 'chalk-part'].includes(b.look || 'wb');
  const ink = dark ? '#ffffff' : '#1d2a44', sub = dark ? '#cfd6e6' : '#5b6478', k = ease(clamp01((lt - at) / 1.0));
  const txt = (/** @type {number} */ x, /** @type {number} */ y, /** @type {number} */ size, /** @type {string} */ s, c = ink, anchor = 'middle', maxW = b.w - 60) => { const [X, Y] = P(x, y); return fitText(UI, { x: X, y: Y, 'font-family': 'Hand', 'font-size': size * Z, 'text-anchor': anchor, fill: c, stroke: 'none' }, s, maxW * Z); };
  const seg = (/** @type {number[][]} */ pts, /** @type {string} */ c, /** @type {number} */ w) => { for (let i = 0; i + 1 < pts.length; i++) { const a = P(pts[i][0], pts[i][1]), bb = P(pts[i + 1][0], pts[i + 1][1]); el('path', { d: `M${a[0]} ${a[1]} L${bb[0]} ${bb[1]}`, fill: 'none', stroke: c, 'stroke-width': w * Z, 'stroke-linecap': 'round' }, UI); } };
  const cx = b.x + b.w / 2;
  if (b.title) txt(cx, b.y + 62, 42, b.title, sub);
  if (b.k === 'num') {
    let s = b.text || '';
    if (b.count) { const [a0, z0, d] = b.count; s = (b.pre || '') + (lerp(a0, z0, k)).toLocaleString('en-US', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }) + (b.post || ''); }
    const y0 = b.ty || b.y + b.h / 2 + 40;
    const e = txt(cx, y0, b.size || 120, s, col(b.col, ink)); e.setAttribute('opacity', String(clamp01((lt - at) / 0.3)));
    if (b.sub) txt(cx, y0 + 70, 40, b.sub, sub);
  } else if (b.k === 'bars') {
    const n = b.items.length, max = Math.max(...b.items.map((/** @type {any} */ i) => i[1])), base = b.y + b.h - 70, H = b.h - 240, W = (b.w - 80) / n;
    seg([[b.x + 30, base], [b.x + b.w - 30, base]], ink, 5);
    b.items.forEach((/** @type {any} */ it, /** @type {number} */ i) => {
      const [lab, v, c, t1] = it, kk = t1 == null ? k : ease(clamp01((lt - t1) / 0.8)); if (kk <= 0) return;
      const bx = b.x + 40 + i * W + W * 0.18, bw = W * 0.64, h = H * v / max * kk, top = base - h;
      const [mx, my0] = P(bx + bw / 2, base), [, my1] = P(0, top + 2);
      el('path', { d: `M${mx} ${my0} L${mx} ${my1}`, fill: 'none', stroke: col(c, '#5b7fb0'), 'stroke-width': bw * Z, 'stroke-linecap': 'butt' }, UI);
      seg([[bx, base], [bx, top], [bx + bw, top], [bx + bw, base]], INK, 5);
      txt(bx + bw / 2, top - 16, 46, (b.pre || '') + v + (b.post || ''), col(c, '#5b7fb0'), 'middle', W);
      txt(bx + bw / 2, base + 44, 32, lab, dark ? '#fff' : '#3b4252', 'middle', W);
    });
  } else if (b.k === 'line') {
    const pts = b.points || [], n = pts.length; if (n < 2) return;
    const max = Math.max(...pts), min = Math.min(...pts, 0), base = b.y + b.h - 60, H = b.h - 180;
    const xy = pts.map((/** @type {number} */ v, /** @type {number} */ i) => [b.x + 60 + i * (b.w - 120) / (n - 1), base - (v - min) / (max - min || 1) * H]);
    const m = Math.max(2, Math.ceil(n * k));
    seg(xy.slice(0, m), col(b.col, pts[n - 1] >= pts[0] ? '#4f9a5e' : '#c0584a'), 10);
  } else if (b.k === 'list') {
    b.rows.forEach((/** @type {string} */ r, /** @type {number} */ i) => {
      const t1 = at + 0.3 + i * (b.step || 0.45); if (lt < t1) return; const yy = b.y + 140 + i * (b.gap || 70);
      if (b.hi === i) { const [a1, y1] = P(b.x + 40, yy - 14), [a2] = P(b.x + b.w - 40, 0); el('path', { d: `M${a1} ${y1} L${a2} ${y1}`, stroke: '#e6c36a', 'stroke-width': 46 * Z, opacity: 0.7, fill: 'none' }, UI); }
      txt(b.x + 60, yy, 44, '• ' + r, ink, 'start');
    });
  } else if (b.k === 'vs') {
    [[b.l, b.x + b.w * 0.27], [b.r, b.x + b.w * 0.73]].forEach(([s, xx], i) => { if (lt < at + i * 0.6) return; txt(xx, b.y + b.h / 2 + 20, b.size || 86, s[0], col(s[2], ink), 'middle', b.w * .42); if (s[1]) txt(xx, b.y + b.h / 2 + 80, 36, s[1], sub, 'middle', b.w * .42); });
    txt(cx, b.y + b.h / 2 + 10, 50, 'vs', dark ? '#8a93a8' : '#9aa0ad');
  } else if (b.k === 'pie') {
    const r = Math.min(b.w, b.h) * 0.3, [PX, PY] = P(b.x + b.w * 0.3, b.y + b.h * 0.56); let a0 = -Math.PI / 2;
    el('path', { d: circ(PX, PY, r * Z), fill: dark ? '#3a4158' : '#e7e3d8', stroke: INK, 'stroke-width': 5 * Z }, UI);
    b.sl.forEach((/** @type {any} */ s, /** @type {number} */ i) => { const [lab, pct, c] = s, kk = ease(clamp01((lt - at - i * 0.5) / 0.7)); if (kk <= 0) return; const a1 = a0 + Math.PI * 2 * pct / 100 * kk;
      el('path', { d: slice(PX, PY, r * Z, a0, a1), fill: col(c, '#c9a64a'), stroke: INK, 'stroke-width': 5 * Z }, UI);
      txt(b.x + b.w * 0.56, b.y + b.h * 0.42 + i * 70, 36, lab, col(c, '#c9a64a'), 'start', b.w * 0.42); a0 = a1; });
  }
}

/** a placard held in front of the chest of a person at screen point (X, Y) */
export function signUI(/** @type {Element} */ UI, /** @type {any} */ view, /** @type {any} */ s, /** @type {number} */ X, /** @type {number} */ Y, /** @type {number} */ lt) {
  const Z = view.Z, k = clamp01((lt - (s.at ?? 0.2)) / 0.25); if (k <= 0) return;
  const w = (s.w || 360) * Z, h = (s.sub ? 170 : 130) * Z;
  const g = el('g', { transform: `translate(${X} ${Y}) scale(${0.8 + 0.2 * k}) rotate(${s.rot ?? -3})` }, UI);
  el('path', { d: box(-w / 2, -h / 2, w, h), fill: s.bg || '#fbf6e6', stroke: 'none' }, g);
  g.insertAdjacentHTML('beforeend', segOutline([[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2]], 7 * Z));
  fitText(g, { x: 0, y: (s.sub ? -4 : 22) * Z, 'font-family': 'Hand', 'font-size': (s.size || 68) * Z, 'text-anchor': 'middle', fill: col(s.col, '#1d2a44') }, s.text, w - 30 * Z);
  if (s.sub) fitText(g, { x: 0, y: 52 * Z, 'font-family': 'Hand', 'font-size': 34 * Z, 'text-anchor': 'middle', fill: '#5b6478' }, s.sub, w - 30 * Z);
}

/** speech bubble near a head at screen point (TX, TY); side +1 opens right */
export function bubbleUI(/** @type {Element} */ UI, /** @type {string} */ text, /** @type {number} */ TX, /** @type {number} */ TY, /** @type {number} */ side, /** @type {number} */ k) {
  const g = el('g', {}, UI), short = text.length <= 3;
  const tx = el('text', { 'font-family': 'Hand', 'font-size': short ? 80 : 48, fill: '#1e1a17', 'text-anchor': 'middle' }, g); tx.textContent = text;
  let L = 0; try { L = /** @type {SVGTextElement} */ (tx).getComputedTextLength(); } catch (_) { L = text.length * 24; }
  const w = Math.max(110, L + 60), h = short ? 120 : 90;
  let bx = side > 0 ? TX + 10 : TX - w - 10, by = TY - h - 60;
  bx = Math.max(40, Math.min(1880 - w, bx)); by = Math.max(30, by);
  g.setAttribute('transform', `translate(${TX} ${TY}) scale(${0.6 + 0.4 * k}) translate(${-TX} ${-TY})`);
  const tailX = Math.max(bx + 40, Math.min(bx + w - 40, TX + side * 30));
  el('path', { d: `M${tailX - 20} ${by + h - 4} L${TX} ${TY} L${tailX + 20} ${by + h - 4} Z`, fill: '#fff', stroke: INK, 'stroke-width': 6 }, g);
  el('path', { d: rrect(bx, by, w, h, 30), fill: '#fff', stroke: INK, 'stroke-width': 6 }, g);
  el('path', { d: `M${tailX - 16} ${by + h - 2} L${tailX + 16} ${by + h - 2}`, stroke: '#fff', 'stroke-width': 8 }, g);
  g.appendChild(tx); tx.setAttribute('x', String(bx + w / 2)); tx.setAttribute('y', String(by + h / 2 + (short ? 28 : 17)));
}

/** thought bubble: puffs grow into a cloud; picture is markup in a 300x200 box */
export function thinkUI(/** @type {Element} */ UI, /** @type {string} */ picture, /** @type {number} */ TX, /** @type {number} */ TY, /** @type {number} */ k) {
  const g = el('g', {}, UI), cx = TX + 220, cy = TY - 260;
  [[TX + 30, TY - 30, 14], [TX + 70, TY - 80, 22]].forEach(([x, y, r], i) => { if (k > i * 0.2) el('path', { d: circ(x, y, r), fill: '#fff', stroke: INK, 'stroke-width': 5 }, g); });
  if (k < 0.4) return;
  const s = ease(clamp01((k - 0.4) / 0.6));
  const cloud = el('g', { transform: `translate(${cx} ${cy}) scale(${s})` }, g);
  cloud.innerHTML = [[-120, 0, 90], [0, -50, 100], [120, 0, 90], [60, 60, 80], [-60, 60, 80]].map(([x, y, r]) => `<path d="${circ(x, y, r)}" fill="#fff" stroke="${INK}" stroke-width="6"/>`).join('') +
    [[-120, 0, 84], [0, -50, 94], [120, 0, 84], [60, 60, 74], [-60, 60, 74]].map(([x, y, r]) => `<path d="${circ(x, y, r)}" fill="#fff" stroke="none"/>`).join('') + `<g transform="translate(-150 -100) scale(1)">${picture || ''}</g>`;
}

/** chapter card: near-black radial ground (not pure black: tier 3), white handwritten title */
export function cardWorld() { return `<path d="${box(-120, -120, 2160, 1320)}" fill="url(#cardBg)" stroke="none"/>`; }
export function cardUI(/** @type {Element} */ UI, /** @type {any} */ c, /** @type {number} */ lt) {
  const k = clamp01((lt - 0.05) / 0.3), z = 1 + 0.025 * lt;          // the title creeps closer: a card is never frozen
  UI = el('g', { transform: `translate(960 580) scale(${z}) translate(-960 -580)` }, UI);
  const t1 = el('text', { x: 960, y: 560, 'font-family': 'Hand', 'font-size': 110, 'text-anchor': 'middle', fill: '#fff', opacity: k }, UI); t1.textContent = c.big;
  if (c.small) { const t2 = el('text', { x: 960, y: 640, 'font-family': 'Hand', 'font-size': 44, 'text-anchor': 'middle', fill: '#c9ccd2', opacity: k }, UI); t2.textContent = c.small; }
}

/** caption: white handwritten title with an ink edge, kept inside the frame */
export function captionUI(/** @type {Element} */ UI, /** @type {number} */ lt, /** @type {any[]} */ cap) {
  const [big, small, x = 360, y = 130, t0 = 0.2] = cap;
  const p = clamp01((lt - t0) / 0.35); if (p <= 0) return;
  const sc = p < 1 ? (p < 0.7 ? p / 0.7 * 1.12 : 1.12 - (p - 0.7) / 0.3 * 0.12) : 1;
  const g = el('g', { transform: `translate(${x} ${y}) scale(${sc}) rotate(-4)` }, UI);
  fitText(g, { x: 0, y: 0, 'font-family': 'Hand', 'font-size': 92, 'text-anchor': 'middle', fill: '#fff', stroke: INK, 'stroke-width': 14, 'paint-order': 'stroke' }, big, 1700);
  if (small) fitText(g, { x: 8, y: 54, 'font-family': 'Hand', 'font-size': 40, 'text-anchor': 'middle', fill: '#fff', stroke: INK, 'stroke-width': 9, 'paint-order': 'stroke' }, small, 1600);
  try { const bb = /** @type {SVGGElement} */ (g).getBBox(); const L = x - bb.width / 2 * sc, R = x + bb.width / 2 * sc; let dx = 0; if (L < 40) dx = 40 - L; else if (R > 1880) dx = 1880 - R; if (dx) g.setAttribute('transform', `translate(${x + dx} ${y}) scale(${sc}) rotate(-4)`); } catch (_) { /* */ }
}

/** floating label with a curved arrow that draws on */
export function labelUI(/** @type {Element} */ UI, /** @type {number} */ lt, /** @type {any[]} */ L) {
  const [text, sub, x, y, tx, ty, t0 = 0.4, bend = 50] = L;
  const p = clamp01((lt - t0) / 0.3); if (p <= 0) return;
  const g = el('g', {}, UI);
  fitText(g, { x, y, 'font-family': 'Hand', 'font-size': 64, 'text-anchor': 'middle', fill: '#fff', stroke: INK, 'stroke-width': 12, 'paint-order': 'stroke', transform: `rotate(-4 ${x} ${y})`, opacity: p }, text, 900);
  if (sub) fitText(g, { x: x + 6, y: y + 46, 'font-family': 'Hand', 'font-size': 36, 'text-anchor': 'middle', fill: '#fff', stroke: INK, 'stroke-width': 8, 'paint-order': 'stroke', transform: `rotate(-4 ${x} ${y})`, opacity: p }, sub, 900);
  const a = clamp01((lt - t0 - 0.15) / 0.4);
  const sx = x + (tx > x ? 60 : -60), sy = y + (sub ? 70 : 24), mx = (sx + tx) / 2 + bend, my = (sy + ty) / 2 - bend * 0.5;
  const d = `M${sx} ${sy} Q${mx} ${my} ${tx} ${ty}`;
  for (const [c, wd] of [[INK, 12], ['#fff', 5]]) {
    const pa = /** @type {SVGPathElement} */ (el('path', { d, fill: 'none', stroke: c, 'stroke-width': wd, 'stroke-linecap': 'round' }, g));
    let Lp = 400; try { Lp = pa.getTotalLength(); } catch (_) { /* */ }
    pa.setAttribute('stroke-dasharray', String(Lp)); pa.setAttribute('stroke-dashoffset', String(Lp * (1 - a)));
  }
  if (a >= 1) {
    const ang = Math.atan2(ty - my, tx - mx), h = (/** @type {number} */ s) => [tx - 26 * Math.cos(ang + s), ty - 26 * Math.sin(ang + s)], [h1, h2] = [h(0.5), h(-0.5)];
    for (const [c, wd] of [[INK, 12], ['#fff', 5]]) el('path', { d: `M${h1[0]} ${h1[1]} L${tx} ${ty} L${h2[0]} ${h2[1]}`, fill: 'none', stroke: c, 'stroke-width': wd, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, g);
  }
}
