// Sketch Explainer proof engine: shared helpers of the studio's SVG cartoon kit (no film scenes, no real people).
// Each scene: (c) => {html, cam, chars, ui}. c = {t, lt, d, p, at(lineId), talk}.
// Filled shapes use only lines and Bézier curves (hardware Chrome here does not fill SVG arc commands).
const INK = '#16120f';
const T = (x, y, s, txt, o = {}) => `<text x="${x}" y="${y}" font-family="Hand" font-size="${s}" text-anchor="${o.a || 'middle'}" fill="${o.f || INK}" stroke="none"${o.r ? ` transform="rotate(${o.r} ${x} ${y})"` : ''}${o.op != null ? ` opacity="${o.op}"` : ''}>${txt}</text>`;
const VIG = '<rect x="-100" y="-100" width="2120" height="1280" fill="url(#vig)" stroke="none"/>';
const poly = (pts) => 'M' + pts.map(p => p.join(' ')).join(' L') + ' Z';
// pie slice as a polygon (no arcs)
const slice = (cx, cy, r, a0, a1) => { const pts = [[cx, cy]]; for (let k = 0; k <= 40; k++) { const a = a0 + (a1 - a0) * k / 40; pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); } return poly(pts); };
const op = (lt, a, f = .25) => clamp01((lt - a) / f);
const pop = (lt, a) => { const k = clamp01((lt - a) / .22); return k <= 0 ? 0 : k < 1 ? 1.25 - .25 * k : 1; };

// ---------- shared pieces ----------
const room = (back = 'url(#backLight)', floorY = 800) => `<rect x="-100" y="-100" width="2120" height="${floorY + 100}" fill="${back}" stroke="none"/>
  <path d="M-100 ${floorY} L2020 ${floorY} L2020 1180 L-100 1180 Z" fill="#5e4a3a" stroke="none"/>
  <g fill="none" stroke-width="4" opacity=".5"><path d="M-100 ${floorY + 90} L2020 ${floorY + 86}"/><path d="M-100 ${floorY + 200} L2020 ${floorY + 194}"/></g>
  <path d="M-100 ${floorY - 20} L2020 ${floorY - 20} L2020 ${floorY} L-100 ${floorY} Z" fill="#6e5a46" stroke-width="5"/><path d="M-100 ${floorY} L2020 ${floorY}" fill="none" stroke-width="7"/>`;
const desktop = (grad = 'url(#woodTop)') => `<rect x="-100" y="-100" width="2120" height="1280" fill="${grad}" stroke="none"/>
  <g fill="none" stroke="#3a2416" stroke-width="4" opacity=".45"><path d="M-100 200 q500 -30 1000 0 t1100 -10"/><path d="M-100 560 q600 30 1100 0 t1000 10"/><path d="M-100 900 q500 -20 1000 6 t1100 -6"/></g>`;
const navy = () => `<rect x="-100" y="-100" width="2120" height="1280" fill="url(#navy)" stroke="none"/><g fill="none" stroke="#3a4360" stroke-width="2" opacity=".55">${Array.from({length: 26}, (_, i) => `<path d="M${i * 80} -100 L${i * 80} 1180"/>`).join('')}${Array.from({length: 15}, (_, i) => `<path d="M-100 ${i * 80} L2020 ${i * 80}"/>`).join('')}</g>`;
const paper = (x, y, w, h, r, inner) => `<g transform="translate(${x} ${y}) rotate(${r})"><path d="${poly([[-w/2, -h/2], [w/2, -h/2], [w/2, h/2], [-w/2, h/2]])}" fill="#000" opacity=".25" stroke="none" transform="translate(14 16)"/>
  <path d="${poly([[-w/2, -h/2], [w/2, -h/2], [w/2, h/2], [-w/2, h/2]])}" fill="#f6f2e6" stroke-width="7"/>${inner}</g>`;
const lines = (x, y, n, w, gap = 34) => Array.from({length: n}, (_, i) => `<path d="M${x} ${y + i * gap} L${x + w * (0.7 + 0.3 * ((i * 37) % 10) / 10)} ${y + i * gap}" fill="none" stroke-width="4" opacity=".45"/>`).join('');
const stamp = (x, y, r, txt, k, col = '#c0392b', fs = 84) => k <= 0 ? '' : `<g transform="translate(${x} ${y}) rotate(${r}) scale(${k < 1 ? 1.8 - .8 * k : 1})"><rect x="${-txt.length * fs * .3 - 30}" y="-${fs * .8}" width="${txt.length * fs * .6 + 60}" height="${fs * 1.5}" rx="12" fill="none" stroke="${col}" stroke-width="11"/>${T(0, fs * .32, fs, txt, {f: col})}</g>`;
const chip = (x, y, s, col = '#2f6b3f', label = '') => `<g transform="translate(${x} ${y}) scale(${s})"><g stroke-width="7">${Array.from({length: 6}, (_, i) => `<path d="M${-75 + i * 30} -110 L${-75 + i * 30} -130 M${-75 + i * 30} 110 L${-75 + i * 30} 130 M-110 ${-75 + i * 30} L-130 ${-75 + i * 30} M110 ${-75 + i * 30} L130 ${-75 + i * 30}" fill="none"/>`).join('')}</g>
  <rect x="-110" y="-110" width="220" height="220" rx="16" fill="#3b3f46" stroke-width="7"/><rect x="-70" y="-70" width="140" height="140" rx="10" fill="${col}" stroke-width="6"/>
  <path d="M-50 -50 L50 -50 M-50 -20 L30 -20 M-50 10 L50 10" fill="none" stroke="#9fd1a8" stroke-width="5" opacity=".6"/>${label ? T(0, 52, 34, label, {f: '#e8f2ea'}) : ''}</g>`;
const crate = (x, y, s, tag = '') => `<g transform="translate(${x} ${y}) scale(${s})"><path d="${poly([[-80, -60], [80, -60], [80, 60], [-80, 60]])}" fill="#b98a52" stroke-width="7"/><path d="M-80 -20 L80 -20 M-80 20 L80 20" fill="none" stroke="#8a6236" stroke-width="5"/><path d="${poly([[-80, -60], [-40, -90], [120, -90], [80, -60]])}" fill="#d0a066" stroke-width="7"/><path d="${poly([[80, -60], [120, -90], [120, 30], [80, 60]])}" fill="#946b3d" stroke-width="7"/>${tag ? T(0, 14, 34, tag) : ''}</g>`;
const greyMan = (x, y, s, col = '#8d8f96', seated = false) => `<g transform="translate(${x} ${y}) scale(${s})"><path d="${BODY(seated)}" fill="${col}" stroke-width="7"/><path d="${circ(0, 0, 165)}" fill="${col}" stroke-width="7"/>${seated ? '' : '<path d="M-46 462 L-50 640 M46 462 L50 640" fill="none" stroke-width="8"/>'}</g>`;
const silhouette = (x, y, s) => `<g transform="translate(${x} ${y}) scale(${s})"><path d="M-178 -20 C-196 -150 -100 -205 0 -200 C100 -205 196 -150 178 -20 C190 60 186 130 150 175 L-150 175 C-186 130 -190 60 -178 -20 Z" fill="#2b2d33" stroke-width="7"/>
  <path d="M-112 148 Q-170 300 -190 640 L190 640 Q170 300 112 148 Q0 118 -112 148 Z" fill="#2b2d33" stroke-width="7"/><path d="${circ(0, 0, 160)}" fill="#33363d" stroke-width="7"/>${T(0, 70, 220, '?', {f: '#e9e3d6'})}</g>`;
const pin = (x, y, col = '#c0392b') => `<g transform="translate(${x} ${y})"><path d="M0 0 C-40 -50 -40 -110 0 -110 C40 -110 40 -50 0 0 Z" fill="${col}" stroke-width="6"/><path d="${circ(0, -72, 14)}" fill="#fff" stroke-width="4"/></g>`;
const _mp = document.createElementNS('http://www.w3.org/2000/svg', 'path');
const partial = (d, k) => { _mp.setAttribute('d', d); const L = _mp.getTotalLength(); let o = ''; for (let i = 0; i <= 60; i++) { const p = _mp.getPointAtLength(L * k * i / 60); o += (i ? ' L' : 'M') + p.x.toFixed(1) + ' ' + p.y.toFixed(1); } return o; };
const dashed = (d, k, col = '#fff', w = 9) => k <= 0 ? '' : `<path d="${partial(d, k)}" fill="none" stroke="${col}" stroke-width="${w}" stroke-dasharray="22 18"/>`;
const magnifier = (x, y, s) => `<g transform="translate(${x} ${y}) scale(${s}) rotate(-30)"><path d="M0 110 L0 260" fill="none" stroke="#5a3a22" stroke-width="34"/><path d="${circ(0, 0, 110)}" fill="#dfeef4" fill-opacity=".45" stroke-width="16"/></g>`;
const screenUI = (x, y, w, h, inner, title = '') => `<g transform="translate(${x} ${y})"><rect x="0" y="0" width="${w}" height="${h}" rx="18" fill="#e9e6df" stroke-width="7"/><rect x="0" y="0" width="${w}" height="64" rx="18" fill="#c9c4b8" stroke-width="7"/>
  <path d="${circ(36, 32, 10)}" fill="#e2483a" stroke-width="3"/><path d="${circ(68, 32, 10)}" fill="#e8c860" stroke-width="3"/><path d="${circ(100, 32, 10)}" fill="#4fc06e" stroke-width="3"/>${title ? T(w / 2, 44, 36, title) : ''}${inner}</g>`;

const TORSO_SUIT = (shirt, tie) => `<path d="M-46 136 L0 250 L46 136 Q0 124 -46 136 Z" fill="${shirt}" stroke-width="5"/>${tie ? `<path d="M-15 150 L15 150 L22 175 L0 196 L-22 175 Z" fill="${tie}" stroke-width="4.5"/><path d="M-14 192 L14 192 L28 330 L0 360 L-28 330 Z" fill="${tie}" stroke-width="4.5"/>` : ''}
  <path d="M-46 136 L-70 200 L-38 214 L-58 236 L0 330" fill="none" stroke-width="5"/><path d="M46 136 L70 200 L38 214 L58 236 L0 330" fill="none" stroke-width="5"/>`;
const C_GUY = (id, suit, hair = '#3a2a20') => ({id, skin: '#e2b98f', skinShade: '#c49a70', suit, suitShade: '#00000033', torso: TORSO_SUIT('#eeeae0'), phase: id.length,
  hair: `<path d="M-160 -20 C-176 -130 -100 -190 0 -188 C100 -190 176 -130 160 -20 C150 -80 100 -110 0 -108 C-100 -110 -150 -80 -160 -20 Z" fill="${hair}" stroke-width="7"/>`});
const SCENES = {};
const NAVY_T = (x, y, s, txt, col = '#fff', sw = 14) => ({x, y, s, txt, col, sw});
function texts(c, UI, t, extra) {
  const p = c.p;
  if (p.cap) caption(UI, t, c.t0 + (p.cap[4] || .2), p.cap[2] || 360, p.cap[3] || 130, p.cap[0], p.cap[1] || '');
  (p.lab || []).forEach(L => labelArrow(UI, t, c.t0 + (L[6] || .4), L[0], L[1] || '', L[2], L[3], L[4], L[5], L[7] || 50));
  if (extra) extra(UI, t);
}
const bigText = (UI, x, y, size, txt, col = '#fff', k = 1, sw = 16, rot = 0) => {
  const g = el('g', {transform: `translate(${x} ${y}) scale(${k}) rotate(${rot})`}, UI);
  el('text', {x: 0, y: 0, 'font-family': 'Hand', 'font-size': size, 'text-anchor': 'middle', fill: col, stroke: INK, 'stroke-width': sw, 'paint-order': 'stroke'}, g).textContent = txt;
  return g;
};
const fmtNum = (n, d = 0) => n.toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d});

// ---------- props (drawn things; no figures) ----------
const PROP = {};
const propAt = (name, x, y, s, arg, t) => `<g transform="translate(${x} ${y}) scale(${s})">${PROP[name](arg, t)}</g>`;
