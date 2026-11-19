// Character scenes of the Sketch Explainer kit (the story is acted by the cast; numbers live on boards,
// signs and screens inside the scene). One template, `act`, driven by params:
//   set     background: room wb stage meet floor gov studio night navy
//   cast    [{w, x, s, pose, p2, at, expr, e2, face, look, talk:[a,b], walk:[x0,x1,a,b], view, y, seat, hop}]
//   board   {k: num|bars|list|vs|pie, x, y, w, h, at, ...}  whiteboard or screen with sourced numbers only
//   sign    {i, text, sub, col}   a placard held by cast i (pose 'hold')
//   bub     [[i, text, at]]       speech bubbles: words only for Max and the generic roles; real people get symbols
//   props   [[name, x, y, s, arg]] behind the cast, propsF in front; crowd [[x, y, s, col]] grey extras
//   cap, lab as in scenes2; cam {cx, cy, z, z1}
// Real people never say invented words: their bubbles hold '!', '?', '$' or an icon.
let CASTK = () => ({max: C_MAX, bank: C_BANKER, aud: C_AUDITOR, trd: C_TRADER, crit: C_CRITIC,
  guy1: C_GUY('g1', '#7a8a5a'), guy2: C_GUY('g2', '#8a5a3a', '#1d1b1a'), guy3: C_GUY('g3', '#6b4a6b', '#6e4f36')});

// rounded rectangle with cubic corners (hardware Chrome here does not fill rx corners, which are arcs)
const rrect = (x, y, w, h, r) => { const k = r * .45; return `M${x + r} ${y} L${x + w - r} ${y} C${x + w - k} ${y} ${x + w} ${y + k} ${x + w} ${y + r} L${x + w} ${y + h - r} C${x + w} ${y + h - k} ${x + w - k} ${y + h} ${x + w - r} ${y + h} L${x + r} ${y + h} C${x + k} ${y + h} ${x} ${y + h - k} ${x} ${y + h - r} L${x} ${y + r} C${x} ${y + k} ${x + k} ${y} ${x + r} ${y} Z`; };
const SKY = (top = 'url(#dusk)', h = 1180) => `<rect x="-100" y="-100" width="2120" height="${h}" fill="${top}" stroke="none"/>`;
const buildingsBack = (col = '#5d5878') => `<g fill="${col}" stroke="none"><rect x="-100" y="420" width="260" height="500"/><rect x="180" y="300" width="200" height="620"/><rect x="420" y="460" width="180" height="460"/>
  <rect x="1320" y="360" width="220" height="560"/><rect x="1560" y="250" width="180" height="670"/><rect x="1760" y="440" width="260" height="480"/></g>`;
const windowsOn = (x, y, w, h) => { let o = ''; for (let yy = y + 30; yy < y + h - 40; yy += 70) for (let xx = x + 24; xx < x + w - 40; xx += 56) o += `<rect x="${xx}" y="${yy}" width="30" height="40"/>`; return `<g fill="#f5c56d" stroke="none" opacity=".75">${o}</g>`; };
const floorBand = (y, col = '#5e4a3a') => `<path d="M-100 ${y} L2020 ${y} L2020 1180 L-100 1180 Z" fill="${col}" stroke="none"/><path d="M-100 ${y} L2020 ${y}" fill="none" stroke-width="7"/>`;
const winRoom = () => `<g transform="translate(1380 160)"><rect x="0" y="0" width="360" height="300" fill="#a9c8d6" stroke-width="8"/><path d="M180 0 L180 300 M0 150 L360 150" fill="none" stroke-width="7"/>
  <g fill="#7f93a8" stroke="none"><rect x="20" y="170" width="70" height="128"/><rect x="100" y="120" width="60" height="178"/><rect x="200" y="190" width="70" height="108"/><rect x="280" y="150" width="60" height="148"/></g></g>`;
const plant = (x, y) => `<g transform="translate(${x} ${y})"><path d="M-50 0 L50 0 L40 90 L-40 90 Z" fill="#b5653a" stroke-width="6"/><path d="${circ(0, -60, 70)}" fill="#4f7a4a" stroke-width="6"/><path d="${circ(-40, -20, 46)}" fill="#5e8c56" stroke-width="6"/><path d="${circ(44, -26, 44)}" fill="#5e8c56" stroke-width="6"/></g>`;
const ticker = (lt) => { const items = 'ANT  NASDAQ  ·  ANT  ·  NASDAQ  ·  ANT  ·  '.repeat(3); const x = -((lt * 120) % 900);
  return `<rect x="-100" y="70" width="2120" height="150" fill="#101318" stroke-width="7"/><g><text x="${x}" y="170" font-family="Hand" font-size="80" fill="#4fc06e" stroke="none">${items}</text></g>`; };

const SETS = {
  room: (c) => ({html: room('url(#backLight)', 760) + winRoom() + plant(260, 670), floor: 940}),
  wb: (c) => ({html: room('url(#backLight)', 780) + plant(1780, 690), floor: 960}),
  chalk: (c) => ({html: room('#b9a888', 780) + `<g transform="translate(1660 300)"><path d="${circ(0, 0, 70)}" fill="#f6f2e6" stroke-width="7"/><path d="M0 0 L0 -44 M0 0 L30 14" fill="none" stroke-width="6"/></g>` + `<path d="M1500 780 L1500 560 L1860 560 L1860 780" fill="#7b593f" stroke-width="7"/>`, floor: 960, look: 'chalk'}),
  tv: (c) => ({html: room('#d8d1c4', 780) + winRoom().replace('translate(1380 160)', 'translate(1460 180) scale(.8)') + `<path d="M1500 780 L1520 640 L1860 640 L1880 780 Z" fill="#5f6b7a" stroke-width="7"/><path d="M1490 640 L1890 640 L1890 600 L1490 600 Z" fill="#748194" stroke-width="7"/>`, floor: 960, look: 'tv'}),
  stage: (c) => ({html: `<rect x="-100" y="-100" width="2120" height="1280" fill="#23232b" stroke="none"/><path d="M200 -100 L520 860 L1400 860 L1720 -100 Z" fill="#fff" opacity=".05" stroke="none"/>
    <path d="${rrect(420, 60, 1080, 560, 16)}" fill="#151820" stroke-width="8"/><path d="M-100 860 L2020 860 L2020 1180 L-100 1180 Z" fill="#3a3038" stroke-width="7"/><path d="M-100 880 L2020 880" fill="none" stroke="#5a4a50" stroke-width="10"/>`,
    fg: Array.from({length: 13}, (_, i) => `<path d="${circ(i * 160 - 20, 1120 + (i % 2) * 20, 78)}" fill="#15151a" stroke="none"/>`).join(''), floor: 900}),
  meet: (c) => ({floorFix: 1, html: room('url(#backLight)', 760) + winRoom(),
    fg: `<path d="M120 760 L1800 760 L1880 860 L40 860 Z" fill="#7b593f" stroke-width="8"/><path d="M40 860 L1880 860 L1880 1180 L40 1180 Z" fill="#5f432f" stroke-width="8"/><path d="M200 790 L1700 790" fill="none" stroke="#9a7656" stroke-width="10" opacity=".6"/>`, floor: 890}),
  floor: (c) => ({html: `<rect x="-100" y="-100" width="2120" height="1280" fill="#2b3550" stroke="none"/>` + ticker(c.lt) +
    `<g fill="#1d2438" stroke-width="5">${Array.from({length: 6}, (_, i) => `<path d="${rrect((i * 340 - 40), 300, 300, 200, 10)}"/>`).join('')}</g>
    <g fill="#4fc06e" stroke="none" opacity=".7">${Array.from({length: 6}, (_, i) => `<path d="M${i * 340} 460 L${i * 340 + 60} 420 L${i * 340 + 120} 440 L${i * 340 + 200} 360 L${i * 340 + 240} 380" fill="none" stroke="#4fc06e" stroke-width="7"/>`).join('')}</g>` + floorBand(780, '#3a3f52'), floor: 980}),
  gov: (c) => ({html: SKY() + `<g transform="translate(960 600)"><path d="M-520 260 L-520 40 L520 40 L520 260 Z" fill="#f2efe6" stroke-width="7"/><path d="M-560 40 L0 -60 L560 40 Z" fill="#e6e1d4" stroke-width="7"/>
    <path d="M-170 -60 C-170 -230 170 -230 170 -60 Z" fill="#f2efe6" stroke-width="7"/><path d="M-10 -210 L-10 -270 L10 -270 L10 -210 Z" fill="#f2efe6" stroke-width="5"/>
    <g fill="none" stroke-width="6">${Array.from({length: 13}, (_, i) => `<path d="M${-480 + i * 80} 70 L${-480 + i * 80} 250"/>`).join('')}</g></g>` + floorBand(860, '#8fb07a'), floor: 1000}),
  studio: (c) => ({html: `<rect x="-100" y="-100" width="2120" height="1280" fill="#2c3550" stroke="none"/><path d="${rrect(1080, 110, 680, 420, 14)}" fill="#151820" stroke-width="8"/>${T(1420, 200, 60, 'NEWS', {f: '#f5c56d'})}
    <g fill="none" stroke="#3a4668" stroke-width="3">${Array.from({length: 12}, (_, i) => `<path d="M${i * 180 - 100} -100 L${i * 180 + 200} 1180"/>`).join('')}</g>`,
    fg: `<path d="M140 780 L1000 780 L1040 1180 L100 1180 Z" fill="#c9cfdc" stroke-width="8"/><path d="M140 780 L1000 780 L1004 820 L136 820 Z" fill="#e6ebf3" stroke-width="6"/>`, floor: 880}),
  night: (c) => ({html: SKY('#1b1f33') + `<path d="${circ(1600, 200, 60)}" fill="#f6efc6" stroke-width="6"/>` + buildingsBack('#2a2f48') + floorBand(900, '#3a3d4e'), floor: 1000}),
  navy: (c) => ({html: navy(), floor: 1000}),
  // the background of an older template (its own texts and characters kept), with the cast added
};

// ---------- whiteboard / screen content (UI layer, follows the camera) ----------
function boardShape(b, dark, look) {
  const {x, y, w, h} = b;
  if (look === 'chalk') return `<path d="M${x - 24} ${y - 24} L${x + w + 24} ${y - 24} L${x + w + 24} ${y + h + 24} L${x - 24} ${y + h + 24} Z" fill="#8a5f3a" stroke-width="7"/><path d="M${x} ${y} L${x + w} ${y} L${x + w} ${y + h} L${x} ${y + h} Z" fill="#2f4038" stroke-width="5"/>
    <path d="M${x + 40} ${y + h - 30} q120 -14 240 6" fill="none" stroke="#fff" stroke-width="5" opacity=".12"/><path d="M${x - 10} ${y + h + 24} L${x + w + 10} ${y + h + 24} L${x + w + 10} ${y + h + 44} L${x - 10} ${y + h + 44} Z" fill="#6e4a2c" stroke-width="5"/>`;
  if (look === 'tv') return `<path d="M${x + w / 2 - 40} ${y + h} L${x + w / 2 - 30} ${y + h + 40} L${x + w / 2 + 30} ${y + h + 40} L${x + w / 2 + 40} ${y + h} Z" fill="#3a3d44" stroke-width="5"/><path d="${rrect(x - 22, y - 22, w + 44, h + 44, 18)}" fill="#1b1d22" stroke-width="8"/><path d="M${x} ${y} L${x + w} ${y} L${x + w} ${y + h} L${x} ${y + h} Z" fill="#151a26" stroke="none"/>`;
  return dark ? `<path d="${rrect((x), (y), (w), (h), 14)}" fill="#151820" stroke-width="8"/>`
    : `<path d="M${x + 60} ${y + h} L${x + 30} ${y + h + 230} M${x + w - 60} ${y + h} L${x + w - 30} ${y + h + 230}" fill="none" stroke="#6a5a48" stroke-width="12"/>
      <path d="${rrect((x - 14), (y - 14), (w + 28), (h + 28), 10)}" fill="#b9bcc2" stroke-width="7"/><rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#fbfaf6" stroke-width="5"/>`;
}
function boardUI(UI, c, b, dark) {
  const Z = CAM.zz, P = (x, y) => W2S(x, y), at = b.at == null ? .3 : b.at; if (c.lt < at) return;
  const k = ease(clamp01((c.lt - at) / 1.0)), ink = dark ? '#ffffff' : '#1d2a44';
  const txt = (x, y, size, s, col, anchor = 'middle', sw = 0) => { const [X, Y] = P(x, y); const e = el('text', {x: X, y: Y, 'font-family': 'Hand', 'font-size': size * Z, 'text-anchor': anchor, fill: col || ink, stroke: sw ? INK : 'none', 'stroke-width': sw * Z, 'paint-order': 'stroke'}, UI); e.textContent = s; return e; };
  const seg = (pts, col, w) => { for (let i = 0; i + 1 < pts.length; i++) { const [a, bb] = [P(...pts[i]), P(...pts[i + 1])]; el('path', {d: `M${a[0]} ${a[1]} L${bb[0]} ${bb[1]}`, fill: 'none', stroke: col, 'stroke-width': w * Z, 'stroke-linecap': 'round'}, UI); } };
  const cx = b.x + b.w / 2;
  if (b.title) txt(cx, b.y + 62, 42, b.title, dark ? '#cfd6e6' : '#5b6478');
  if (b.k === 'num') {
    let s = b.text; if (b.count) { const [a, z, d] = b.count; s = (b.pre || '') + fmtNum(lerp(a, z, k), d || 0) + (b.post || ''); }
    const e = txt(cx, b.ty || b.y + b.h / 2 + 40, b.size || 120, s, b.col || ink); e.setAttribute('opacity', clamp01((c.lt - at) / .3));
    if (b.sub) txt(cx, (b.ty || b.y + b.h / 2 + 40) + 70, 40, b.sub, dark ? '#cfd6e6' : '#5b6478');
  } else if (b.k === 'bars') {
    const n = b.items.length, max = Math.max(...b.items.map(i => i[1])), base = b.y + b.h - 70, H = b.h - 240, W = (b.w - 80) / n;
    seg([[b.x + 30, base], [b.x + b.w - 30, base]], ink, 5);
    b.items.forEach(([lab, v, col, t1], i) => { const kk = t1 == null ? k : ease(clamp01((c.lt - t1) / .8)); if (kk <= 0) return;
      const bx = b.x + 40 + i * W + W * .18, bw = W * .64, h = H * v / max * kk, top = base - h;
      const [mx, my0] = P(bx + bw / 2, base), [, my1] = P(0, top + 2);
      el('path', {d: `M${mx} ${my0} L${mx} ${my1}`, fill: 'none', stroke: col || '#4fc06e', 'stroke-width': bw * Z, 'stroke-linecap': 'butt'}, UI);
      seg([[bx, base], [bx, top], [bx + bw, top], [bx + bw, base]], INK, 5);
      txt(bx + bw / 2, top - 16, 46, (b.pre || '') + v + (b.post || ''), col || '#2c8a4a', 'middle', dark ? 8 : 0);
      txt(bx + bw / 2, base + 44, 32, lab, dark ? '#fff' : '#3b4252'); });
  } else if (b.k === 'list') {
    b.rows.forEach((r, i) => { const t1 = at + .3 + i * (b.step || .45); if (c.lt < t1) return; const yy = b.y + 140 + i * (b.gap || 70);
      if (b.hi === i) { const [a1, y1] = P(b.x + 40, yy - 14), [a2] = P(b.x + b.w - 40, 0); el('path', {d: `M${a1} ${y1} L${a2} ${y1}`, stroke: '#f5d34a', 'stroke-width': 46 * Z, opacity: .7, fill: 'none'}, UI); }
      txt(b.x + 60, yy, 44, '• ' + r, ink, 'start'); });
  } else if (b.k === 'vs') {
    [[b.l, b.x + b.w * .27], [b.r, b.x + b.w * .73]].forEach(([s, xx], i) => { if (c.lt < at + i * .6) return; txt(xx, b.y + b.h / 2 + 20, b.size || 86, s[0], s[2] || ink); if (s[1]) txt(xx, b.y + b.h / 2 + 80, 36, s[1], dark ? '#cfd6e6' : '#5b6478'); });
    txt(cx, b.y + b.h / 2 + 10, 50, 'vs', dark ? '#8a93a8' : '#9aa0ad');
  } else if (b.k === 'pie') {
    const r = Math.min(b.w, b.h) * .3, pc = [b.x + b.w * .32, b.y + b.h * .55]; let a0 = -Math.PI / 2;
    const [PX, PY] = P(...pc);
    el('path', {d: circ(PX, PY, r * Z), fill: dark ? '#3a4158' : '#e7e3d8', stroke: INK, 'stroke-width': 5 * Z}, UI);
    b.sl.forEach(([lab, pct, col], i) => { const kk = ease(clamp01((c.lt - at - i * .5) / .7)); if (kk <= 0) return; const a1 = a0 + Math.PI * 2 * pct / 100 * kk;
      el('path', {d: slice(PX, PY, r * Z, a0, a1), fill: col, stroke: INK, 'stroke-width': 5 * Z}, UI);
      txt(b.x + b.w * .56, b.y + b.h * .42 + i * 70, 36, lab, col, 'start', dark ? 8 : 0); a0 = a1; });
  }
}
// a placard held in front of the chest
function signUI(UI, c, s, ch) {
  const Z = CAM.zz, k = clamp01((c.lt - (s.at || .2)) / .25); if (k <= 0) return;
  const [X, Y] = W2S(ch.x, ch.y + 250 * ch.s), w = (s.w || 360) * Z, h = (s.sub ? 170 : 130) * Z;
  const g = el('g', {transform: `translate(${X} ${Y}) scale(${.8 + .2 * k}) rotate(${s.rot || -3})`}, UI);
  el('path', {d: `M${-w / 2} ${-h / 2} L${w / 2} ${-h / 2} L${w / 2} ${h / 2} L${-w / 2} ${h / 2} Z`, fill: s.bg || '#fbf6e6', stroke: INK, 'stroke-width': 7 * Z}, g);
  el('text', {x: 0, y: (s.sub ? -4 : 22) * Z, 'font-family': 'Hand', 'font-size': Math.min(s.size || 68, ((s.w || 360) - 40) / (.48 * s.text.length)) * Z, 'text-anchor': 'middle', fill: s.col || '#1d2a44'}, g).textContent = s.text;
  if (s.sub) el('text', {x: 0, y: 52 * Z, 'font-family': 'Hand', 'font-size': 34 * Z, 'text-anchor': 'middle', fill: '#5b6478'}, g).textContent = s.sub;
}
// a speech bubble that pops in
function bubUI(UI, c, b, ch) {
  const [i, text, at] = b; if (c.lt < (at || .3)) return; const k = clamp01((c.lt - (at || .3)) / .18), Z = CAM.zz;
  const side = ch.x > 1200 ? -1 : 1;
  const [TX, TY] = W2S(ch.x + side * 110 * ch.s, ch.y - 150 * ch.s);
  const g = el('g', {}, UI);
  const tx = el('text', {'font-family': 'Hand', 'font-size': (text.length <= 2 ? 80 : 48), fill: '#1e1a17'}, g); tx.textContent = text;
  const w = Math.max(110, tx.getComputedTextLength() + 60), h = text.length <= 2 ? 120 : 90;
  let bx = side > 0 ? TX + 10 : TX - w - 10, by = TY - h - 60;
  bx = Math.max(40, Math.min(1880 - w, bx)); by = Math.max(30, by);
  g.setAttribute('transform', `translate(${TX} ${TY}) scale(${.6 + .4 * k}) translate(${-TX} ${-TY})`);
  const tailX = Math.max(bx + 40, Math.min(bx + w - 40, TX + side * 30));
  el('path', {d: `M${tailX - 20} ${by + h - 4} L${TX} ${TY} L${tailX + 20} ${by + h - 4} Z`, fill: '#fff', stroke: INK, 'stroke-width': 6}, g);
  el('path', {d: rrect(bx, by, w, h, 30), fill: '#fff', stroke: INK, 'stroke-width': 6}, g);
  el('path', {d: `M${tailX - 16} ${by + h - 2} L${tailX + 16} ${by + h - 2}`, stroke: '#fff', 'stroke-width': 8}, g);
  g.appendChild(tx); tx.setAttribute('x', bx + w / 2); tx.setAttribute('text-anchor', 'middle'); tx.setAttribute('y', by + h / 2 + (text.length <= 2 ? 28 : 17));
}

Object.assign(SCENES, {
  act: (c) => {
    const p = c.p, S = SETS[p.set || 'room'](c), K = CASTK(), L = c.lt;
    const cast = (p.cast || []).map(q => {
      const s = q.s || .6; let x = q.x;
      let walk = 0, ph = 0;
      if (q.walk) { const [x0, x1, a = 0, b = c.d] = q.walk, u = clamp01((L - a) / (b - a)); x = lerp(x0, x1, ease(u)); walk = u > 0 && u < 1 ? 1 : 0; ph = L * 9; }
      const h0 = q.hop || 0, hl = L - h0, hop = q.hop != null && hl > 0 && hl < 1.5 ? -Math.abs(Math.sin(hl * 6.3)) * 26 : 0;
      const y0 = q.y != null ? q.y : S.floor - 640 * s, y = y0 + hop;
      // a presenter beside a board steps in at the start
      if (!q.walk && !q.still && p.board && q.pose === 'pointL' && L < .8) { x = lerp(q.x + 160, q.x, ease(L / .8)); walk = 1; ph = L * 9; }
      return Object.assign({}, q, {x, y, y0, s, walk, ph});
    });
    const shadows = cast.filter(q => !q.seat && q.y + 640 * q.s < 1100).map(q => `<ellipse cx="${q.x}" cy="${q.y + 650 * q.s}" rx="${150 * q.s}" ry="${26 * q.s}" fill="#000" opacity=".18" stroke="none"/>`).join('');
    const dark = p.set === 'stage' || p.set === 'studio' || p.set === 'navy' || S.look === 'chalk' || S.look === 'tv' || p.board && p.board.dark;
    const board = p.board ? (p.board.screen ? '' : boardShape(p.board, dark, S.look)) : '';
    const html = S.html + (p.props || []).map(a => propAt(a[0], a[1], a[2], a[3], a[4], L)).join('') + board + (p.crowd || []).map(([x, y, s, col]) => greyMan(x, y, s, col || '#8d8f96')).join('') + shadows + '<g class="cast"></g>' + (S.fg || '') + (p.propsF || []).map(a => propAt(a[0], a[1], a[2], a[3], a[4], L)).join('') + (p.vig === 0 ? '' : VIG);
    const GEST = {rest: ['rest', 'palm', 'rest', 'chin'], palm: ['palm', 'rest', 'raise', 'palm', 'wide'], pointL: ['pointL', 'pointL', 'palm', 'pointL', 'raise'],
      pointR: ['pointR', 'pointR', 'palm', 'pointR'], raise: ['raise', 'palm', 'raise', 'rest'], up: ['up', 'raise', 'up', 'wide'], shrug: ['shrug', 'rest', 'shrug', 'palm'], chin: ['chin', 'chin', 'rest', 'chin'], wide: ['wide', 'palm', 'wide']};
    const gesture = (q, i) => { const g = q.gest || GEST[q.pose || 'rest']; if (!g || q.still || q.p2 || q.pose === 'hold' || q.seat || q.walk || q.view === 'back') return null;
      const per = q.per || 2.1, off = i * .73 + (q.x % 97) / 97, u = (L + off) / per, n = Math.floor(u), k = clamp01((u - n) * per / .45);
      return {pose: g[n % g.length], poseFrom: g[(n + g.length - 1) % g.length], poseK: k}; };
    const chars = cast.map((q, i) => {
      const cfg = K[q.w]; const u = q.at != null ? clamp01((L - q.at) / .35) : 1;
      const talk = q.talk && L >= q.talk[0] && L <= q.talk[1] ? .35 + .3 * Math.sin(L * 15) + .2 * Math.sin(L * 23) : 0;
      return [q.seat ? '.seat' : '.cast', cfg, {x: q.seat ? 850 : q.x, y: q.seat ? 335 : q.y, s: q.seat ? .95 : q.s, view: q.view,
        pose: q.p2 && L >= (q.at || 0) ? q.p2 : (q.pose || 'rest'), poseFrom: q.p2 && L >= (q.at || 0) ? (q.pose || 'rest') : undefined, poseK: q.p2 ? u : 1,
        expr: q.e2 && L >= (q.at || 0) ? q.e2 : (q.expr || 'neutral'), face: (q.face || 0) + (q.still ? 0 : .12 * Math.sin(L * .9 + i * 1.7)), look: (q.look || 0) + (q.still ? 0 : 5 * Math.sin(L * .6 + i)), talk, walk: q.walk ? cast.find(z => z === q) && q.walk : 0, walkPh: q.ph, tilt: q.tilt || 0}];
    });
    chars.forEach((ch, i) => { ch[2].walk = cast[i].walk; const g = gesture(cast[i], i); if (g) Object.assign(ch[2], g); });
    let close = null; if (p.close) { const q = cast[p.close - 1], z = p.cz || 1.7; close = {cx: Math.max(960 / z, Math.min(1920 - 960 / z, q.x)), cy: Math.max(540 / z, Math.min(1080 - 540 / z, q.y0 + 120 * q.s)), z, z1: z + .12}; }
    return {cam: p.cam || close || S.cam || {cx: 960, cy: 540, z: 1.0, z1: 1.05}, html, chars: (S.chars || []).concat(chars),
      ui: (UI, t) => { if (p.board) boardUI(UI, c, p.board, dark); if (p.sign) signUI(UI, c, p.sign, cast[p.sign.i]);
        (p.bub || []).forEach(b => bubUI(UI, c, b, cast[b[0]])); if (S.ui) S.ui(UI, t); if (!S.ui || p.cap || p.lab) texts(c, UI, t); }};
  },
});
