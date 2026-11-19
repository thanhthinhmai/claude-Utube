// Andy Jassy: caricature (about 70% likeness) for the studio's 2D films, from a press photo (specs/028).
// Approved by the user on 2026-11-19 in the Anthropic film; moved here from films/anthropic-ipo-15/cast.js.
import { bumpy, arcPts, ovalHead, circ } from '../../kit/core.js';
import { ears, rearHair, roundGlasses, rectGlasses, stubble, SHIRT_OPEN, BLAZER } from '../../kit/roles.js';


export default {skin: '#ecc3a0', skinShade: '#cf9f7a', suit: '#283250', suitShade: '#1c2440', torso: BLAZER('#b9cdea', null),
  head: ovalHead(146, 170, .62), hairBack: ears(142, '#e8bd98'),
  hair: `<path d="M-146 -40 C-150 -110 -124 -168 -72 -196 C-30 -214 30 -214 72 -196 C124 -168 150 -110 146 -40 C138 -84 124 -112 104 -128 C96 -150 70 -164 40 -166 C10 -150 -20 -150 -50 -164 C-80 -160 -100 -146 -108 -126 C-126 -110 -138 -84 -146 -40 Z" fill="#a9a8a6" stroke-width="6"/>
  <path d="M-40 -186 C0 -200 40 -198 70 -186" fill="none" stroke="#d4d3d0" stroke-width="7"/><path d="M-60 -110 q14 -5 28 0 t28 0 t28 0 t28 0" fill="none" stroke-width="3" opacity=".35"/>`,
  hairRear: rearHair('#a9a8a6', -212), brows: ['M-84 -50 Q-56 -58 -26 -50', 'M26 -50 Q56 -58 84 -50'], browW: 6, phase: 2.7};
