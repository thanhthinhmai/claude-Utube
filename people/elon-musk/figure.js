// Elon Musk: caricature (about 70% likeness) for the studio's 2D films, from a press photo (specs/028).
// Approved by the user on 2026-11-19 in the Anthropic film; moved here from films/anthropic-ipo-15/cast.js.
import { bumpy, arcPts, ovalHead, circ } from '../../kit/core.js';
import { ears, rearHair, roundGlasses, rectGlasses, stubble, SHIRT_OPEN, BLAZER } from '../../kit/roles.js';


export default {skin: '#efc9aa', skinShade: '#d2a684', suit: '#1e1e22', suitShade: '#121215', torso: BLAZER('#f4f2ec', '#141416'),
  head: ovalHead(156, 166, .8), hairBack: ears(152, '#ebc4a2'),
  hair: `<path d="M-150 -40 C-158 -140 -96 -210 0 -212 C96 -210 158 -140 150 -40 C142 -96 128 -124 108 -134 C90 -144 70 -136 52 -150 C30 -138 10 -132 -6 -150 C-30 -138 -54 -144 -70 -150 C-90 -136 -110 -144 -124 -118 C-138 -96 -144 -70 -150 -40 Z" fill="#6b4a32" stroke-width="7"/>
  <path d="M-60 -176 C-20 -196 40 -196 90 -176 M-90 -160 C-50 -186 20 -190 70 -184" fill="none" stroke="#8f6a4c" stroke-width="6"/>`,
  hairRear: rearHair('#6b4a32', -212), brows: ['M-88 -48 Q-58 -58 -26 -50', 'M26 -50 Q58 -58 88 -48'], browW: 8, phase: 3.9};
