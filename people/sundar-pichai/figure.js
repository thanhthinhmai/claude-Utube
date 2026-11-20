// Sundar Pichai: caricature (about 70% likeness) for the studio's 2D films, from a press photo (specs/028).
// Approved by the user on 2026-11-19 in the Anthropic film; moved here from films/anthropic-ipo-15/cast.js.
import { bumpy, arcPts, ovalHead, circ } from '../../kit/core.js';
import { ears, rearHair, roundGlasses, rectGlasses, stubble, SHIRT_OPEN, BLAZER } from '../../kit/roles.js';

const SUNDAR_BEARD = `<path d="M-128 30 C-124 110 -70 164 0 166 C70 164 124 110 128 30 C112 60 96 70 80 72 C60 96 30 102 0 100 C-30 102 -60 96 -80 72 C-96 70 -112 60 -128 30 Z" fill="#b6b0a8" stroke-width="5"/>
  <path d="M-46 44 Q-20 32 0 38 Q20 32 46 44 Q30 48 0 48 Q-30 48 -46 44 Z" fill="#8f8a84" stroke-width="3"/>
  <path d="M-90 110 q8 8 16 4 M70 112 q10 6 18 -2 M-30 140 q10 8 20 2 M20 142 q10 6 18 -2" fill="none" stroke="#e6e2dc" stroke-width="3"/>`;
export default {skin: '#b98a62', skinShade: '#9c7048', suit: '#22252c', suitShade: '#16181d', torso: BLAZER('#f4f2ec', '#3d6fb0'),
  head: ovalHead(138, 170, .6), hairBack: ears(134, '#b48560'),
  hair: `<path d="M-138 -40 C-146 -130 -100 -200 0 -204 C100 -200 146 -130 138 -40 C130 -90 116 -116 96 -130 C60 -150 20 -138 -10 -148 C-50 -146 -90 -140 -110 -118 C-124 -100 -132 -74 -138 -40 Z" fill="#2c2826" stroke-width="7"/>
  <path d="M-138 -40 C-136 -70 -130 -96 -116 -114 M138 -40 C136 -70 130 -96 116 -114" fill="none" stroke="#9a9590" stroke-width="10"/>`,
  hairRear: rearHair('#2c2826', -204), extraFace: SUNDAR_BEARD + rectGlasses('#1d1b1a', 8),
  brows: ['M-84 -52 Q-56 -62 -26 -52', 'M26 -52 Q56 -62 84 -52'], browW: 8, phase: 3.3};
