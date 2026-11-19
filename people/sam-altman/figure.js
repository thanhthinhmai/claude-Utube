// Sam Altman: caricature (about 70% likeness) for the studio's 2D films, from a press photo (specs/028).
// Approved by the user on 2026-11-19 in the Anthropic film; moved here from films/anthropic-ipo-15/cast.js.
import { bumpy, arcPts, ovalHead, circ } from '../../kit/core.js';
import { ears, rearHair, roundGlasses, rectGlasses, stubble, SHIRT_OPEN, BLAZER } from '../../kit/roles.js';


export default {skin: '#efc9a6', skinShade: '#d2a57f', suit: '#2c3d66', suitShade: '#1f2c4c', torso: BLAZER('#f4f2ec', null),
  head: ovalHead(136, 166, .58), hairBack: ears(132, '#ebc3a0'),
  hair: `<path d="${bumpy([[-138, -50], [-150, -116], [-130, -170], [-92, -212], [-40, -236], [20, -238], [74, -224], [116, -192], [144, -140], [142, -60], [120, -108], [80, -126], [40, -122], [0, -132], [-40, -124], [-80, -120], [-118, -98]], 12, 0, -120)}" fill="#7d5c3f" stroke-width="7"/>
  <path d="M-60 -186 q20 -22 40 -6 M10 -200 q20 -20 40 -2 M-110 -150 q14 -20 32 -8 M80 -170 q16 -14 30 6" fill="none" stroke="#a88360" stroke-width="5"/>`,
  hairRear: rearHair('#7d5c3f', -214), brows: ['M-82 -52 Q-56 -60 -26 -52', 'M26 -52 Q56 -60 82 -52'], browW: 7, phase: 2.1};
