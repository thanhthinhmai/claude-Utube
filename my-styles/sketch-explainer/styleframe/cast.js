// Cast of the film (specs: caricature model sheet approved before scenes). Head coordinates: head ~ r165 at 0,0,
// eyes at y -6 (x ±48), brows -50, mouth 50..60; body from y 148 to 480. Cubic/quadratic curves only (no arcs on this hardware).

// a closed outline through points, each edge bulging outward from the centre by amp (curls, tufts)
const bumpy = (pts, amp, cx = 0, cy = 0) => {
  let d = `M${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length];
    const mx = (x0 + x1) / 2, my = (y0 + y1) / 2, dx = mx - cx, dy = my - cy, L = Math.hypot(dx, dy) || 1;
    d += ` Q${(mx + dx / L * amp).toFixed(1)} ${(my + dy / L * amp).toFixed(1)} ${x1} ${y1}`;
  }
  return d + ' Z';
};
// points on an ellipse from angle a0 to a1 (degrees, 0 = right, -90 = top)
const arcPts = (rx, ry, a0, a1, n, cx = 0, cy = 0) => Array.from({length: n + 1}, (_, i) => {
  const a = (a0 + (a1 - a0) * i / n) * Math.PI / 180; return [+(cx + rx * Math.cos(a)).toFixed(1), +(cy + ry * Math.sin(a)).toFixed(1)]; });
const ovalHead = (rx, ry, jaw = .62) => `M0 ${-ry} C${rx * .56} ${-ry} ${rx} ${-ry * .64} ${rx} ${-ry * .12} C${rx} ${ry * .3} ${rx * .87} ${ry * .63} ${rx * jaw + 10} ${ry * .82} C${rx * .45} ${ry * .95} ${rx * .2} ${ry} 0 ${ry} C${-rx * .2} ${ry} ${-rx * .45} ${ry * .95} ${-rx * jaw - 10} ${ry * .82} C${-rx * .87} ${ry * .63} ${-rx} ${ry * .3} ${-rx} ${-ry * .12} C${-rx} ${-ry * .64} ${-rx * .56} ${-ry} 0 ${-ry} Z`;
const ears = (x, skin) => `<path d="M${-x} -40 C${-x - 30} -50 ${-x - 38} -6 ${-x - 28} 22 C${-x - 22} 40 ${-x - 10} 44 ${-x + 2} 40 Z M${x} -40 C${x + 30} -50 ${x + 38} -6 ${x + 28} 22 C${x + 22} 40 ${x + 10} 44 ${x - 2} 40 Z" fill="${skin}" stroke-width="6"/>`;
const rearHair = (col, top = -200) => `<path d="M-150 30 C-170 -120 -100 ${top} 0 ${top - 2} C100 ${top} 170 -120 150 30 C110 80 -110 80 -150 30 Z" fill="${col}" stroke-width="7"/>`;
const rectGlasses = (col, w = 7) => `<g fill="none"><path d="M-92 -32 L-14 -32 L-16 14 Q-52 22 -88 14 Z M14 -32 L92 -32 L88 14 Q52 22 16 14 Z" fill="#fff" fill-opacity=".12" stroke="${col}" stroke-width="${w}"/><path d="M-14 -22 Q0 -30 14 -22 M-92 -24 L-146 -32 M92 -24 L146 -32" stroke="${col}" stroke-width="5"/></g>`;
const roundGlasses = (col, w = 9) => `<g fill="none"><path d="M-92 -10 C-92 -40 -62 -44 -48 -44 C-26 -44 -10 -36 -10 -8 C-10 20 -30 30 -50 30 C-74 30 -92 18 -92 -10 Z M92 -10 C92 -40 62 -44 48 -44 C26 -44 10 -36 10 -8 C10 20 30 30 50 30 C74 30 92 18 92 -10 Z" fill="#fff" fill-opacity=".12" stroke="${col}" stroke-width="${w}"/><path d="M-10 -14 Q0 -22 10 -14 M-92 -18 L-148 -30 M92 -18 L148 -30" stroke="${col}" stroke-width="6"/></g>`;
const stubble = (op = .16) => `<path d="M-128 40 C-118 110 -60 160 0 162 C60 160 118 110 128 40 C100 96 60 120 0 122 C-60 120 -100 96 -128 40 Z" fill="#3a2a22" stroke="none" opacity="${op}"/>`;
// shirts and jackets (torso layer, front view)
const SHIRT_OPEN = (shirt, tee) => `${tee ? `<path d="M-30 140 Q0 170 30 140 L24 168 Q0 184 -24 168 Z" fill="${tee}" stroke-width="4"/>` : ''}
  <path d="M-48 132 L-84 196 L-30 178 L0 214 L30 178 L84 196 L48 132" fill="${shirt}" stroke-width="5"/><path d="M0 214 L0 470" fill="none" stroke-width="4" opacity=".55"/>
  <g fill="#f5f3ee" stroke-width="2.5"><circle cx="0" cy="260" r="6"/><circle cx="0" cy="330" r="6"/><circle cx="0" cy="400" r="6"/></g>`;
const BLAZER = (shirt, tie, lapel) => `<path d="M-46 136 L0 250 L46 136 Q0 124 -46 136 Z" fill="${shirt}" stroke-width="5"/>${tie ? `<path d="M-15 150 L15 150 L22 175 L0 196 L-22 175 Z" fill="${tie}" stroke-width="4.5"/><path d="M-14 192 L14 192 L28 330 L0 360 L-28 330 Z" fill="${tie}" stroke-width="4.5"/>` : `<path d="M-46 136 L-30 180 L0 162 L30 180 L46 136" fill="${shirt}" stroke-width="4"/>`}
  <path d="M-46 136 L-70 200 L-38 214 L-58 236 L0 330" fill="${lapel || 'none'}" stroke-width="5"/><path d="M46 136 L70 200 L38 214 L58 236 L0 330" fill="${lapel || 'none'}" stroke-width="5"/>
  <g fill="#1d1b1a" stroke="none"><circle cx="-8" cy="372" r="6"/><circle cx="-8" cy="420" r="6"/></g>`;
const HOODIE = (col, dark) => `<path d="M-96 140 Q-60 196 0 200 Q60 196 96 140 Q60 120 0 120 Q-60 120 -96 140 Z" fill="${dark}" stroke-width="6"/>
  <path d="M-26 196 L-30 270 M26 196 L30 270" fill="none" stroke="#f3efe6" stroke-width="6"/><path d="M-90 360 L90 360 L76 450 L-76 450 Z" fill="${dark}" stroke-width="5"/>`;

// ---------- everyman and generic roles ----------
// Max, a small retail investor and the film's guide: messy dark hair, orange hoodie
const C_MAX = {id: 'max', skin: '#f0c9a2', skinShade: '#d4a47c', suit: '#e8833a', suitShade: '#c4672a', torso: HOODIE('#e8833a', '#d0702e'),
  hairBack: ears(160, '#ecc49c'),
  hair: `<path d="${bumpy([[-160, -30], [-170, -100], [-140, -160], [-90, -196], [-30, -212], [40, -210], [100, -190], [146, -150], [166, -90], [160, -30], [130, -90], [100, -110], [60, -96], [30, -120], [-10, -104], [-50, -122], [-90, -104], [-130, -84]], 14, 0, -110)}" fill="#3a2a20" stroke-width="7"/>`,
  hairRear: rearHair('#3a2a20', -212), phase: 4.4};
// the banker: slicked-back black hair, grey suit, red tie
const C_BANKER = {id: 'bank', skin: '#ecc6a4', skinShade: '#d0a27e', suit: '#5c6068', suitShade: '#454850', torso: BLAZER('#f1eee6', '#b8352b'),
  head: ovalHead(146, 168, .66), hairBack: ears(142, '#e8c09c'),
  hair: `<path d="M-146 -30 C-156 -140 -90 -206 0 -206 C90 -206 156 -140 146 -30 C136 -100 110 -136 60 -144 C10 -150 -50 -146 -100 -126 C-126 -110 -140 -76 -146 -30 Z" fill="#1d1b1d" stroke-width="7"/>
  <path d="M-90 -170 C-40 -190 40 -190 100 -160 M-110 -140 C-60 -166 20 -170 90 -150" fill="none" stroke="#4a4650" stroke-width="5"/>`,
  hairRear: rearHair('#1d1b1d', -206), phase: 5.1};
// the auditor: hair in a bun, round glasses, green cardigan
const C_AUDITOR = {id: 'aud', skin: '#f2d0b2', skinShade: '#d8ae8e', suit: '#4f7a5a', suitShade: '#3d6046', torso: BLAZER('#efece4', null, '#5d8a68'), glasses: true,
  head: ovalHead(142, 164, .6),
  hairBack: `<path d="${circ(0, -214, 52)}" fill="#5a3e2c" stroke-width="7"/>`,
  hair: `<path d="M-146 -20 C-156 -140 -90 -200 0 -200 C90 -200 156 -140 146 -20 C130 -100 90 -130 0 -132 C-90 -130 -130 -100 -146 -20 Z" fill="#5a3e2c" stroke-width="7"/>`,
  hairRear: rearHair('#5a3e2c', -206), phase: 5.6};
// the trader on the exchange floor: blue trading jacket with a badge
const C_TRADER = {id: 'trd', skin: '#c99872', skinShade: '#a8784f', suit: '#3b6fb6', suitShade: '#2c5794', torso: BLAZER('#f1eee6', '#e0b84a') + `<path d="M50 260 L110 260 L110 320 L50 320 Z" fill="#f6f2e6" stroke-width="4"/><path d="M60 280 L100 280 M60 298 L92 298" fill="none" stroke-width="4"/>`,
  hairBack: ears(160, '#c4926c'),
  hair: `<path d="M-160 -40 C-170 -140 -100 -196 0 -196 C100 -196 170 -140 160 -40 C150 -100 110 -120 0 -118 C-110 -120 -150 -100 -160 -40 Z" fill="#1f1a18" stroke-width="7"/>`,
  hairRear: rearHair('#1f1a18', -200), phase: 6.2};
// the critic / analyst: short bob, red blazer
const C_CRITIC = {id: 'crit', skin: '#efcdb0', skinShade: '#d4aa8a', suit: '#b8392e', suitShade: '#952a22', torso: BLAZER('#f3efe8', null),
  head: ovalHead(140, 164, .6),
  hairBack: `<path d="M-176 -30 C-190 -170 -100 -222 0 -220 C100 -222 190 -170 176 -30 C180 40 174 90 160 120 L100 120 C120 60 120 0 116 -30 L-116 -30 C-120 0 -120 60 -100 120 L-160 120 C-174 90 -180 40 -176 -30 Z" fill="#2b2220" stroke-width="7"/>`,
  hair: `<path d="M-150 0 C-160 -140 -90 -204 0 -204 C90 -204 160 -140 150 0 C140 -60 120 -100 80 -110 L-120 -90 C-136 -70 -146 -40 -150 0 Z" fill="#2b2220" stroke-width="7"/>`,
  hairRear: rearHair('#2b2220', -220), brows: ['M-80 -54 Q-54 -62 -26 -54', 'M26 -54 Q54 -62 80 -54'], browW: 6, phase: 6.8};
// a government official (generic, no real person): grey side-parted hair, dark suit, small flag pin

