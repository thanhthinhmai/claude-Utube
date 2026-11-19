// Daniela Amodei: caricature for the studio's 2D films (specs/028), from two press photos used only as a drawing
// reference: long straight dark-brown hair with a centre part, tucked behind the ears and falling past the shoulders;
// a long oval face with full cheeks; strong straight brows; a closed-lip smile; small stud earrings; a light blazer.
import { ovalHead, circ } from '../../kit/core.js';
import { rearHair, BLAZER } from '../../kit/roles.js';

const HAIR = '#4a3426', HAIR_LIGHT = '#6b4c38';
// long hair behind the head and shoulders, slightly wavy at the ends
const BACK = `<path d="M-168 -40 C-186 -170 -100 -226 0 -226 C100 -226 186 -170 168 -40 C172 70 182 170 196 250 C204 300 186 330 150 336 C130 300 128 300 112 330 C96 300 92 230 112 120 L-112 120 C-92 230 -96 300 -112 330 C-128 300 -130 300 -150 336 C-186 330 -204 300 -196 250 C-182 170 -172 70 -168 -40 Z" fill="${HAIR}" stroke-width="9"/>`;
// small ears with stud earrings, where the hair is tucked behind them
const EARS = `<path d="M-134 -30 C-160 -38 -166 0 -158 22 C-152 36 -142 38 -132 32 Z M134 -30 C160 -38 166 0 158 22 C152 36 142 38 132 32 Z" fill="#efcdb0" stroke-width="7"/>
  <path d="${circ(-152, 36, 6)} ${circ(152, 36, 6)}" fill="#d9d4c8" stroke-width="3"/>`;
// centre part: two curtains from the crown down past the temples
const FRONT = `<path d="M0 -198 C-62 -198 -120 -172 -144 -110 C-154 -80 -152 -50 -142 -26 C-130 -70 -106 -112 -64 -140 C-38 -156 -14 -172 0 -188 Z" fill="${HAIR}" stroke-width="8"/>
  <path d="M0 -198 C62 -198 120 -172 144 -110 C154 -80 152 -50 142 -26 C130 -70 106 -112 64 -140 C38 -156 14 -172 0 -188 Z" fill="${HAIR}" stroke-width="8"/>
  <path d="M-22 -184 C-62 -172 -102 -142 -126 -98 M22 -184 C62 -172 102 -142 126 -98" fill="none" stroke="${HAIR_LIGHT}" stroke-width="5"/>`;
const FACE = `<path d="M-98 44 q12 16 30 12 M98 44 q-12 16 -30 12" fill="none" stroke-width="3.5" opacity=".35"/>`;
// a light blazer over a dark top
const TORSO = BLAZER('#2a2a30', null, '#e3ddd1');

export default {
  skin: '#efcdb0', skinShade: '#d6ad8e', suit: '#e3ddd1', suitShade: '#c9c2b4', torso: TORSO,
  head: ovalHead(134, 174, 0.58), hairBack: BACK + EARS, hair: FRONT, hairRear: BACK + rearHair(HAIR, -226),
  extraFace: FACE, brows: ['M-84 -56 Q-56 -63 -26 -58', 'M26 -58 Q56 -63 84 -56'], browW: 11, phase: 1.3,
};
