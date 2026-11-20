// Proof page of the Sketch Explainer style: one new medium shot (not a reference scene).
// White-faced extras, muted greys and olives, flat sky with a lighter skyline, large floor ellipses, slow push.
const WHITE = (id, suit, hair, hairShape) => ({id, skin: '#f7f7f5', skinShade: '#dcdcd8', suit, suitShade: '#00000026', torso: TORSO_SUIT('#e9e9e4'), phase: id.length * .7,
  hair: hairShape || `<path d="M-160 -20 C-176 -130 -100 -190 0 -188 C100 -190 176 -130 160 -20 C150 -80 100 -110 0 -108 C-100 -110 -150 -80 -160 -20 Z" fill="${hair}" stroke-width="7"/>`,
  hairRear: rearHair(hair, -200)});
const _K = CASTK;
CASTK = () => Object.assign(_K(), {
  w1: WHITE('w1', '#5f6f5a', '#6b4a32'),
  w2: WHITE('w2', '#4e5a66', '#2a2422', `<path d="M-150 -10 C-160 -140 -90 -204 0 -204 C90 -204 160 -140 150 -10 C140 -60 120 -100 80 -110 L-120 -90 C-136 -70 -146 -40 -150 -10 Z" fill="#2a2422" stroke-width="7"/>`),
  w3: WHITE('w3', '#6a5a4a', '#8a6a4a')});
SETS.curb = (c) => ({floor: 1000, html: `<rect x="-100" y="-100" width="2120" height="1280" fill="#acdce8" stroke="none"/>
  <path d="M-100 260 L-100 120 L140 120 L140 60 L330 60 L330 150 L560 150 L560 90 L700 90 L700 170 L980 170 L980 40 L1150 40 L1150 130 L1400 130 L1400 70 L1600 70 L1600 160 L2020 160 L2020 260 Z" fill="#5fabbb" stroke="none"/>
  <path d="M-100 250 L2020 250 L2020 520 L-100 520 Z" fill="#6f8a4e" stroke="none"/>
  <path d="M-100 360 C500 330 1300 340 2020 470 L2020 1180 L-100 1180 Z" fill="#474a55" stroke-width="7"/>
  <path d="M-100 760 C300 790 900 900 1500 1180 L-100 1180 Z" fill="#d3d5d3" stroke-width="7"/>
  <g fill="none" stroke="#9fb27e" stroke-width="4" opacity=".7"><path d="M120 300 l6 -14 M420 290 l4 -12 M1500 320 l6 -14 M1760 340 l4 -12"/></g>`});
PROP.truck = () => `<g><path d="M-330 -260 L230 -260 L230 120 L-330 120 Z" fill="#ececea" stroke-width="8"/><path d="M230 -160 L360 -160 L420 -40 L420 120 L230 120 Z" fill="#e2e2df" stroke-width="8"/>
  <path d="M260 -140 L345 -140 L390 -50 L260 -50 Z" fill="#bfe2ea" stroke-width="6"/><path d="M-280 -210 L120 -210 L120 -60 L-280 -60 Z" fill="#3c3f47" stroke-width="7"/>
  <path d="M-300 -60 L140 -60 L170 -20 L-330 -20 Z" fill="#b8513f" stroke-width="6"/><path d="M-250 -150 L40 -150" fill="none" stroke="#f5d34a" stroke-width="10"/>
  <path d="${circ(-200, 130, 62)}" fill="#2a2b30" stroke-width="7"/><path d="${circ(300, 130, 62)}" fill="#2a2b30" stroke-width="7"/><path d="${circ(-200, 130, 24)} ${circ(300, 130, 24)}" fill="#9a9ca3" stroke-width="5"/></g>`;
