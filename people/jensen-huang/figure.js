// Jensen Huang: caricature (about 70% likeness) for the studio's 2D films, drawn in six rounds from a press photo:
// 3/7 side part, low sweep, visible ears, thin semi-rimless glasses, centre-zip leather jacket (specs/028).
// Approved by the user on 2026-11-19 in the Nvidia film; moved here from films/jensen-out/scenes.js.

const HEAD_J = `M0 -172 C83 -172 148 -110 148 -20 C148 50 129 108 96 140 C67 162 31 170 0 170 C-31 170 -67 162 -96 140 C-129 108 -148 50 -148 -20 C-148 -110 -83 -172 0 -172 Z`;
const EARS_J = `<path d="M-140 -40 C-170 -50 -178 -6 -168 22 C-162 40 -150 44 -138 40 Z M140 -40 C170 -50 178 -6 168 22 C162 40 150 44 138 40 Z" fill="#e3b88f" stroke-width="6"/>`;
// 3/7 side part on the viewer's left: the small side combed down to the left temple, the large side swept as a low
// wave across to the right and down over the right temple
const HAIR_J = `<path d="M-64 -192 C-100 -184 -128 -164 -140 -132 C-148 -108 -150 -84 -146 -58 C-136 -88 -122 -110 -104 -124 C-88 -136 -72 -146 -58 -150 Z" fill="#cbccd1" stroke-width="6"/>
  <path d="M-58 -150 C-20 -160 40 -158 84 -140 C108 -130 126 -112 136 -88 C142 -74 144 -62 146 -50 C158 -90 160 -140 140 -176 C118 -208 70 -220 20 -214 C-20 -210 -50 -200 -64 -192 Z" fill="#d2d3d7" stroke-width="7"/>
  <path d="M-54 -158 C-18 -168 40 -166 82 -148 C104 -138 120 -122 130 -100" fill="none" stroke="#a0a1a7" stroke-width="10"/>
  <path d="M-46 -172 C0 -190 70 -194 120 -168 M-34 -188 C20 -206 92 -204 142 -168 M40 -156 C80 -156 114 -136 136 -104 M-84 -172 C-112 -160 -130 -136 -140 -108" fill="none" stroke="#8e8f95" stroke-width="4.5"/>
  <path d="M-40 -198 C10 -214 80 -210 126 -186" fill="none" stroke="#f3f3f5" stroke-width="11" opacity=".95"/>
  <path d="M-58 -150 L-64 -191" fill="none" stroke="#e6bd93" stroke-width="5"/>`;
const REAR_J = `<path d="M-150 30 C-170 -120 -100 -212 0 -214 C100 -212 170 -120 150 30 C130 70 90 84 50 76 C20 88 -20 88 -50 76 C-90 84 -130 70 -150 30 Z" fill="#c4c5ca" stroke-width="7"/>
  <path d="M-100 -170 Q0 -240 100 -170 M-60 -70 Q0 -120 60 -70" fill="none" stroke="#8a8b91" stroke-width="5"/>`;
const GLASSES_J = `<g fill="none"><path d="M-90 -28 L-16 -28 L-18 10 Q-52 18 -86 10 Z M16 -28 L90 -28 L86 10 Q52 18 18 10 Z" fill="#fff" fill-opacity=".12" stroke-width="3.5"/>
  <path d="M-90 -28 L-16 -28 M16 -28 L90 -28" stroke-width="7"/><path d="M-16 -22 Q0 -28 16 -22 M-90 -24 L-146 -32 M90 -24 L146 -32" stroke-width="4"/></g>`;
const FACE_J = '<path d="M-44 -96 q11 -5 22 0 t22 0 t22 0 t22 0" fill="none" stroke-width="3" opacity=".4"/>' +
  '<path d="M-82 40 q-8 20 4 38 M82 40 q8 20 -4 38" fill="none" stroke-width="3.5" opacity=".45"/>' + GLASSES_J;
const TORSO_J = `<path d="M-30 150 L30 150 L26 480 L-26 480 Z" fill="#111113" stroke="none"/><path d="M-40 140 Q0 162 40 140" fill="none" stroke-width="5"/>
  <path d="M-52 132 L-104 150 L-74 232 L-30 182 Z" fill="#303036" stroke-width="6"/><path d="M52 132 L104 150 L74 232 L30 182 Z" fill="#303036" stroke-width="6"/>
  <path d="M-30 182 L-26 478 M30 182 L26 478" fill="none" stroke="#c9ccd2" stroke-width="5"/><path d="M-30 182 L-26 478 M30 182 L26 478" fill="none" stroke-width="2" stroke-dasharray="5 6"/>
  <path d="M-124 250 Q-108 330 -128 430" fill="none" stroke="#5e5e68" stroke-width="10" opacity=".75"/><path d="M110 270 Q124 350 112 440" fill="none" stroke="#4c4c56" stroke-width="8" opacity=".65"/>
  <path d="M-100 180 Q-60 170 -40 200" fill="none" stroke="#6a6a74" stroke-width="6" opacity=".6"/>`;
export default {skin: '#e6bd93', skinShade: '#c99a6e', suit: '#25252a', suitShade: '#141417', torso: TORSO_J, head: HEAD_J,
  hairBack: EARS_J, hair: HAIR_J, hairRear: REAR_J, extraFace: FACE_J, brows: ['M-88 -50 Q-56 -60 -24 -50', 'M24 -50 Q56 -60 88 -50'], browW: 9, phase: 0};
