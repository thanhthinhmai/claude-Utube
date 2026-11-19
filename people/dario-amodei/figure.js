// Dario Amodei: caricature (about 70% likeness) for the studio's 2D films, from a press photo (specs/028).
// Approved by the user on 2026-11-19 in the Anthropic film; moved here from films/anthropic-ipo-15/cast.js.
import { bumpy, arcPts, ovalHead, circ } from '../../kit/core.js';
import { ears, rearHair, roundGlasses, rectGlasses, stubble, SHIRT_OPEN, BLAZER } from '../../kit/roles.js';

const DARIO_HAIR = `<path d="${bumpy([[-150, -40], ...arcPts(168, 196, 196, 344, 13, 0, -40).slice(1), [150, -40], [138, -86], [104, -118], [60, -128], [20, -150], [-24, -150], [-66, -128], [-108, -118], [-140, -86]], 16, 0, -60)}" fill="#3b2a20" stroke-width="7"/>
  <g fill="none" stroke="#6b4c38" stroke-width="5"><path d="M-110 -176 q12 -16 26 -2 M-50 -206 q14 -16 28 -2 M20 -212 q14 -16 28 -2 M84 -188 q14 -14 26 2 M-136 -128 q10 -14 22 -2 M120 -132 q12 -14 22 0 M-12 -180 q12 -14 24 0"/></g>`;
export default {skin: '#efcaa8', skinShade: '#d3a781', suit: '#5b7fc0', suitShade: '#46679f', torso: SHIRT_OPEN('#6b8fd0', '#f1efe9'),
  head: ovalHead(152, 168, .64), hairBack: ears(146, '#ebc4a0'), hair: DARIO_HAIR, hairRear: rearHair('#3b2a20', -214),
  extraFace: stubble(.13) + roundGlasses('#25304a', 10), brows: ['M-86 -54 Q-58 -64 -26 -56', 'M26 -56 Q58 -64 86 -54'], browW: 8, phase: .4};
