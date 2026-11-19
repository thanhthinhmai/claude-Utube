// Daniela Amodei: caricature (about 70% likeness) for the studio's 2D films, from a press photo (specs/028).
// Approved by the user on 2026-11-19 in the Anthropic film; moved here from films/anthropic-ipo-15/cast.js.
import { bumpy, arcPts, ovalHead, circ } from '../../kit/core.js';
import { ears, rearHair, roundGlasses, rectGlasses, stubble, SHIRT_OPEN, BLAZER } from '../../kit/roles.js';


export default {skin: '#f1cfb0', skinShade: '#d8b08e', suit: '#2a2a30', suitShade: '#1b1b20', torso: BLAZER('#f4f1ea', null),
  head: ovalHead(140, 164, .6),
  hairBack: `<path d="M-170 -40 C-190 -170 -100 -222 0 -220 C100 -222 190 -170 170 -40 C176 80 190 200 176 300 L96 300 C110 200 120 100 120 20 L-120 20 C-120 100 -110 200 -96 300 L-176 300 C-190 200 -176 80 -170 -40 Z" fill="#6e4f36" stroke-width="7"/>`,
  hair: `<path d="M-150 -10 C-160 -140 -90 -206 10 -204 C110 -202 168 -130 152 -10 C140 -80 110 -130 60 -150 C20 -120 -60 -110 -100 -70 C-120 -50 -136 -30 -150 -10 Z" fill="#7a5a3e" stroke-width="7"/>
  <path d="M60 -150 C40 -180 0 -196 -40 -196 M60 -150 C90 -170 120 -150 140 -110" fill="none" stroke="#a07a56" stroke-width="7"/>`,
  hairRear: rearHair('#6e4f36', -220), brows: ['M-80 -52 Q-54 -62 -26 -54', 'M26 -54 Q54 -62 80 -52'], browW: 6, phase: 1.3};
