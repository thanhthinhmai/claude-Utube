// @ts-check
// Character rig (specs/028 T005): round head with no neck (≈ 1/3 of the height), bean torso, single-stroke arms and
// legs with no hands and no feet (legs end in a point), crescent shade on one side of the head, two black oval eyes,
// one-stroke brows that carry the emotion, small mouth, usually no nose. Front, 3/4 (face slides) and back views.
// Coordinates: head centre at 0,0 (radius ≈ 165), body from y 148 to 470, feet at y ≈ 640. Evidence: style §1, §2.
import { el, circ, lerp, ease, LW, INK } from './core.js';

export const POSES = {
  rest:   { L: [-168, 392, -196, 280], R: [168, 392, 196, 280] },
  hold:   { L: [-70, 300, -180, 270],  R: [70, 300, 180, 270] },
  shrug:  { L: [-250, 140, -215, 270], R: [250, 140, 215, 270] },
  raise:  { L: [-168, 392, -196, 280], R: [285, 40, 270, 210] },
  wide:   { L: [-310, 110, -235, 175], R: [310, 110, 235, 175] },
  up:     { L: [-215, -30, -235, 170], R: [215, -30, 235, 170] },
  palm:   { L: [-168, 392, -196, 280], R: [30, 20, 215, 215] },
  pointL: { L: [-340, 170, -250, 190], R: [168, 392, 196, 280] },
  pointR: { L: [-168, 392, -196, 280], R: [340, 170, 250, 190] },
  desk:   { L: [-150, 420, -200, 300], R: [150, 420, 200, 300] },
  chin:   { L: [-168, 392, -196, 280], R: [118, 96, 236, 240] },
  hips:   { L: [-110, 330, -240, 250], R: [110, 330, 240, 250] },
  think:  { L: [-60, 260, -190, 300],  R: [60, 120, 210, 250] },
};
export const EXPRS = {
  neutral: { eye: 16, brow: 0,  tilt: 0,  mouth: 'smile' },
  happy:   { eye: 16, brow: 6,  tilt: 0,  mouth: 'smile' },
  excited: { eye: 19, brow: 14, tilt: 0,  mouth: 'grin' },
  proud:   { eye: 16, brow: 10, tilt: 0,  mouth: 'grin' },
  worried: { eye: 16, brow: 4,  tilt: 14, mouth: 'frown' },
  shocked: { eye: 25, brow: 22, tilt: 0,  mouth: 'o' },
  deadpan: { eye: 7,  brow: -5, tilt: 0,  mouth: 'flat' },
  smug:    { eye: 9,  brow: -2, tilt: -6, mouth: 'smile' },
  beam:    { eye: 14, brow: 4,  tilt: 0,  mouth: 'teeth' },
  calm:    { eye: 9,  brow: 2,  tilt: 0,  mouth: 'smirk' },
  angry:   { eye: 12, brow: -8, tilt: -16, mouth: 'frown' },
  sad:     { eye: 12, brow: 2,  tilt: 18, mouth: 'frown' },
};
const BODY = (/** @type {boolean} */ seated) => `M-112 148 Q-158 250 -150 ${seated ? 470 : 462} Q-150 ${seated ? 470 : 478} 0 ${seated ? 470 : 480} Q150 ${seated ? 470 : 478} 150 ${seated ? 470 : 462} Q158 250 112 148 Q0 118 -112 148 Z`;

/** @param {Element} parent @param {any} o role config */
export function makeChar(parent, o) {
  const id = o.id + (o.tag || ''), g = el('g', { id }, parent);
  const HEAD = o.head || circ(0, 0, 165);
  const legs = o.seated ? '' : `<path class="legL" fill="none" stroke-width="${LW}"/><path class="legR" fill="none" stroke-width="${LW}"/>`;
  g.innerHTML = `
  <clipPath id="${id}-bc"><path d="${BODY(o.seated)}"/></clipPath>
  <clipPath id="${id}-hc"><path d="${HEAD}"/></clipPath>
  <g class="rig" stroke="${INK}" stroke-linejoin="round" stroke-linecap="round">
    ${legs}
    <g class="body">
      <path d="${BODY(o.seated)}" fill="${o.suit}" stroke-width="${LW}"/>
      <g clip-path="url(#${id}-bc)" stroke="none"><path class="bodyShade" d="M60 110 Q150 230 160 490 L200 490 L200 110 Z" fill="${o.suitShade}"/></g>
      <g class="torso">${o.torso || ''}</g>
      <g class="torsoBack" style="display:none"><path d="M0 150 L0 470" fill="none" stroke-width="4" opacity=".5"/><path d="M-70 150 Q0 132 70 150" fill="none" stroke-width="5"/></g>
    </g>
    <g class="head">
      <g class="hairBack">${o.hairBack || ''}</g>
      <path d="${HEAD}" fill="${o.skin}" stroke="none"/>
      <g clip-path="url(#${id}-hc)" stroke="none"><path class="headShade" d="${HEAD}" fill="${o.skinShade}"/></g>
      <path d="${HEAD}" fill="none" stroke-width="${LW}"/>
      <g class="face">
        <g class="hairFront">${o.hair || ''}</g>
        <path class="browL" d="${(o.brows || [])[0] || 'M-72 -46 Q-50 -58 -26 -50'}" fill="none" stroke-width="${o.browW || 8}"/>
        <path class="browR" d="${(o.brows || [])[1] || 'M26 -50 Q50 -58 72 -46'}" fill="none" stroke-width="${o.browW || 8}"/>
        <g fill="#1a191a" stroke="none">
          <ellipse class="eyeL" cx="-48" cy="-6" rx="11" ry="16"/><ellipse class="eyeR" cx="48" cy="-6" rx="11" ry="16"/>
          <circle class="glL" cx="-44" cy="-12" r="3.5" fill="#fff"/><circle class="glR" cx="52" cy="-12" r="3.5" fill="#fff"/>
        </g>
        ${o.glasses ? `<g fill="none" stroke-width="6"><path d="${circ(-48, -6, 36)}" fill="#fff" fill-opacity=".12"/><path d="${circ(48, -6, 36)}" fill="#fff" fill-opacity=".12"/><path d="M-12 -8 Q0 -16 12 -8 M-84 -10 L-150 -24 M84 -10 L150 -24"/></g>` : ''}
        ${o.extraFace || ''}
        ${o.nose ? '<path class="nose" d="M-6 22 Q0 30 8 24" fill="none" stroke-width="4.5" opacity=".75"/>' : ''}
        <path class="mouthLine" fill="none" stroke-width="7"/>
        <path class="mouthOpen" fill="#5b2420" stroke-width="6"/>
        <path class="tongue" fill="#c45a50" stroke="none"/>
      </g>
      <g class="rear" style="display:none">${o.hairRear || ''}</g>
    </g>
    <path class="armL" fill="none" stroke-width="${LW}"/><path class="armR" fill="none" stroke-width="${LW}"/>
    <g class="prop"></g>
  </g>`;
  /** @type {Record<string, any>} */
  const P = {};
  for (const c of ['rig', 'body', 'head', 'face', 'rear', 'torso', 'torsoBack', 'hairBack', 'hairFront', 'headShade', 'bodyShade', 'armL', 'armR', 'legL', 'legR', 'browL', 'browR', 'eyeL', 'eyeR', 'glL', 'glR', 'mouthLine', 'mouthOpen', 'tongue', 'prop']) P[c] = g.querySelector('.' + c);
  return { g, o, P };
}
function blend(/** @type {any} */ a, /** @type {any} */ b, /** @type {number} */ k) {
  /** @type {any} */ const r = {};
  for (const s of ['L', 'R']) r[s] = a[s].map((/** @type {number} */ v, /** @type {number} */ i) => lerp(v, b[s][i], k));
  return r;
}
/** @param {any} c @param {any} st {t, x, y, s, pose, poseFrom, poseK, expr, face, look, view, walk, walkPh, talk, tilt, light, blink} */
export function setChar(c, st) {
  const P = c.P, o = c.o;
  const back = st.view === 'back';
  c.g.setAttribute('transform', `translate(${st.x} ${st.y}) scale(${st.s} ${st.s})`);
  const t = st.t, br = Math.sin(t * 2.4 + (o.phase || 0)) * 0.012;
  const w = st.walk || 0, ph = st.walkPh || 0;
  const bob = w ? -Math.abs(Math.sin(ph)) * 14 : 0;
  P.rig.setAttribute('transform', `translate(0 ${bob})`);
  P.body.setAttribute('transform', `translate(0 470) scale(1 ${1 + br}) translate(0 -470)`);
  if (P.legL) {
    // legs end in a point: no feet (style §1)
    const sw = w ? Math.sin(ph) * 48 : 0, fy = 640 - bob;
    P.legL.setAttribute('d', `M-46 462 L${-50 + sw} ${fy}`);
    P.legR.setAttribute('d', `M46 462 L${50 - sw} ${fy}`);
  }
  const f = back ? 0 : (st.face || 0);
  P.face.style.display = back ? 'none' : '';
  P.rear.style.display = back ? '' : 'none';
  P.hairBack.style.display = back ? 'none' : '';
  P.torso.style.display = back ? 'none' : '';
  P.torsoBack.style.display = back ? '' : 'none';
  P.face.setAttribute('transform', `translate(${f * 40} 0) scale(${1 - Math.abs(f) * 0.1} 1)`);
  const lx = (st.light || -1) * 36;
  P.headShade.setAttribute('d', (o.head || circ(0, 0, 165)) + ' ' + circ(lx, -22, 170));
  P.headShade.setAttribute('fill-rule', 'evenodd');
  P.bodyShade.setAttribute('transform', (st.light || -1) > 0 ? 'scale(-1 1)' : '');
  const pose = blend(POSES[st.poseFrom || st.pose] || POSES.rest, POSES[st.pose] || POSES.rest, st.poseK == null ? 1 : ease(st.poseK));
  const swingA = w ? Math.sin(ph) * 30 : 0;
  P.armL.setAttribute('d', `M-112 168 Q${pose.L[2]} ${pose.L[3]} ${pose.L[0] - swingA} ${pose.L[1] + br * 200}`);
  P.armR.setAttribute('d', `M112 168 Q${pose.R[2]} ${pose.R[3]} ${pose.R[0] + swingA} ${pose.R[1] + br * 200}`);
  const E = EXPRS[st.expr || 'neutral'] || EXPRS.neutral;
  const tilt = Math.sin(t * 1.7 + (o.phase || 0)) * 3.5 + (st.tilt || 0);
  P.head.setAttribute('transform', `translate(0 ${Math.sin(t * 2.4 + (o.phase || 0)) * 5}) rotate(${tilt} 0 120)`);
  if (back) return;
  const blink = st.blink || ((t + (o.phase || 0) * 0.7) % 3.4 < 0.12);
  const ey = blink ? 2 : E.eye, look = st.look || 0;
  for (const [e, x] of [[P.eyeL, -48], [P.eyeR, 48]]) { e.setAttribute('ry', ey); e.setAttribute('rx', E.eye > 20 ? 9 : 11); e.setAttribute('cx', x + look); }
  P.glL.setAttribute('cx', -44 + look); P.glR.setAttribute('cx', 52 + look);
  P.glL.style.display = P.glR.style.display = blink || E.eye < 10 ? 'none' : '';
  P.browL.setAttribute('transform', `translate(0 ${-E.brow}) rotate(${-E.tilt} -50 -52)`);
  P.browR.setAttribute('transform', `translate(0 ${-E.brow}) rotate(${E.tilt} 50 -52)`);
  const a = st.talk || 0;
  const set = (/** @type {string} */ line, /** @type {string} */ open, /** @type {string} */ tg) => { P.mouthLine.setAttribute('d', line || ''); P.mouthOpen.setAttribute('d', open || ''); P.tongue.setAttribute('d', tg || ''); };
  if (a > 0.06) {
    const h = 10 + a * 34, wd = 24 + a * 6;
    set('', `M${-wd} 50 Q0 46 ${wd} 50 Q${wd - 4} ${50 + h} 0 ${52 + h} Q${-wd + 4} ${50 + h} ${-wd} 50 Z`, h > 22 ? `M-13 ${44 + h} Q0 ${36 + h} 13 ${44 + h} Q8 ${50 + h} 0 ${50 + h} Q-8 ${50 + h} -13 ${44 + h} Z` : '');
    P.tongue.setAttribute('fill', '#c45a50');
    return;
  }
  const m = E.mouth;
  if (m === 'smile') set('M-30 52 Q0 74 30 52', '', '');
  else if (m === 'frown') set('M-26 68 Q0 50 26 68', '', '');
  else if (m === 'flat') set('M-22 62 L22 62', '', '');
  else if (m === 'grin') set('', 'M-42 46 Q0 54 42 46 Q34 94 0 96 Q-34 94 -42 46 Z', 'M-18 82 Q0 70 18 82 Q10 92 0 92 Q-10 92 -18 82 Z');
  else if (m === 'o') set('', 'M-16 62 Q-16 40 0 40 Q16 40 16 62 Q16 86 0 86 Q-16 86 -16 62 Z', '');
  else if (m === 'smirk') set('M-30 58 Q0 70 32 52', '', '');
  else if (m === 'teeth') set('', 'M-56 40 Q0 58 56 40 Q42 98 0 102 Q-42 98 -56 40 Z', 'M-46 48 Q0 62 46 48 L40 68 Q0 78 -40 68 Z');
  P.tongue.setAttribute('fill', m === 'teeth' ? '#f6f2e6' : '#c45a50');
}
