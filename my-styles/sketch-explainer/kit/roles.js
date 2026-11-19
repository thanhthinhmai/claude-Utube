// @ts-check
// Generic roles of the kit (specs/028 T011). Real people never live here: they come from the studio's people library
// (people/<slug>/figure.js, copied into the film by `sh bin/studio people use`). Costumes are coded by role and kept
// muted (style §3): suits in black, navy or grey with a white shirt and a coloured tie; sweaters and hoodies in muted
// reds and greens; extras have white faces, leads and real people get skin tone (style §1, visual report "Characters").
import { circ, bumpy, ovalHead } from './core.js';

export const ears = (/** @type {number} */ x, /** @type {string} */ skin) => `<path d="M${-x} -40 C${-x - 30} -50 ${-x - 38} -6 ${-x - 28} 22 C${-x - 22} 40 ${-x - 10} 44 ${-x + 2} 40 Z M${x} -40 C${x + 30} -50 ${x + 38} -6 ${x + 28} 22 C${x + 22} 40 ${x + 10} 44 ${x - 2} 40 Z" fill="${skin}" stroke-width="7"/>`;
export const rearHair = (/** @type {string} */ col, top = -200) => `<path d="M-150 30 C-170 -120 -100 ${top} 0 ${top - 2} C100 ${top} 170 -120 150 30 C110 80 -110 80 -150 30 Z" fill="${col}" stroke-width="9"/>`;
export const rectGlasses = (/** @type {string} */ col, w = 7) => `<g fill="none"><path d="M-92 -32 L-14 -32 L-16 14 Q-52 22 -88 14 Z M14 -32 L92 -32 L88 14 Q52 22 16 14 Z" fill="#fff" fill-opacity=".12" stroke="${col}" stroke-width="${w}"/><path d="M-14 -22 Q0 -30 14 -22 M-92 -24 L-146 -32 M92 -24 L146 -32" stroke="${col}" stroke-width="5"/></g>`;
export const roundGlasses = (/** @type {string} */ col, w = 9) => `<g fill="none"><path d="M-92 -10 C-92 -40 -62 -44 -48 -44 C-26 -44 -10 -36 -10 -8 C-10 20 -30 30 -50 30 C-74 30 -92 18 -92 -10 Z M92 -10 C92 -40 62 -44 48 -44 C26 -44 10 -36 10 -8 C10 20 30 30 50 30 C74 30 92 18 92 -10 Z" fill="#fff" fill-opacity=".12" stroke="${col}" stroke-width="${w}"/><path d="M-10 -14 Q0 -22 10 -14 M-92 -18 L-148 -30 M92 -18 L148 -30" stroke="${col}" stroke-width="6"/></g>`;
export const stubble = (op = 0.16) => `<path d="M-128 40 C-118 110 -60 160 0 162 C60 160 118 110 128 40 C100 96 60 120 0 122 C-60 120 -100 96 -128 40 Z" fill="#3a2a22" stroke="none" opacity="${op}"/>`;

// torso layers (front view)
export const SHIRT_OPEN = (/** @type {string} */ shirt, /** @type {string|null} */ tee) => `${tee ? `<path d="M-30 140 Q0 170 30 140 L24 168 Q0 184 -24 168 Z" fill="${tee}" stroke-width="4"/>` : ''}
  <path d="M-48 132 L-84 196 L-30 178 L0 214 L30 178 L84 196 L48 132" fill="${shirt}" stroke-width="6"/><path d="M0 214 L0 470" fill="none" stroke-width="4" opacity=".55"/>
  <g fill="#f5f3ee" stroke-width="2.5"><circle cx="0" cy="260" r="6"/><circle cx="0" cy="330" r="6"/><circle cx="0" cy="400" r="6"/></g>`;
export const BLAZER = (/** @type {string} */ shirt, /** @type {string|null} */ tie, /** @type {string|undefined} */ lapel) => `<path d="M-46 136 L0 250 L46 136 Q0 124 -46 136 Z" fill="${shirt}" stroke-width="6"/>${tie ? `<path d="M-15 150 L15 150 L22 175 L0 196 L-22 175 Z" fill="${tie}" stroke-width="5"/><path d="M-14 192 L14 192 L28 330 L0 360 L-28 330 Z" fill="${tie}" stroke-width="5"/>` : `<path d="M-46 136 L-30 180 L0 162 L30 180 L46 136" fill="${shirt}" stroke-width="5"/>`}
  <path d="M-46 136 L-70 200 L-38 214 L-58 236 L0 330" fill="${lapel || 'none'}" stroke-width="6"/><path d="M46 136 L70 200 L38 214 L58 236 L0 330" fill="${lapel || 'none'}" stroke-width="6"/>
  <g fill="#1d1b1a" stroke="none"><circle cx="-8" cy="372" r="6"/><circle cx="-8" cy="420" r="6"/></g>`;
export const HOODIE = (/** @type {string} */ dark) => `<path d="M-96 140 Q-60 196 0 200 Q60 196 96 140 Q60 120 0 120 Q-60 120 -96 140 Z" fill="${dark}" stroke-width="7"/>
  <path d="M-26 196 L-30 270 M26 196 L30 270" fill="none" stroke="#f3efe6" stroke-width="7"/><path d="M-90 360 L90 360 L76 450 L-76 450 Z" fill="${dark}" stroke-width="6"/>`;
export const SWEATER = (/** @type {string} */ dark) => `<path d="M-70 136 Q0 176 70 136" fill="none" stroke="${dark}" stroke-width="22"/><path d="M-70 136 Q0 176 70 136" fill="none" stroke-width="5"/>`;

// hair shapes (front), by name
export const HAIR = {
  short: (/** @type {string} */ c) => `<path d="M-160 -20 C-176 -130 -100 -190 0 -188 C100 -190 176 -130 160 -20 C150 -80 100 -110 0 -108 C-100 -110 -150 -80 -160 -20 Z" fill="${c}" stroke-width="9"/>`,
  messy: (/** @type {string} */ c) => `<path d="${bumpy([[-160, -30], [-170, -100], [-140, -160], [-90, -196], [-30, -212], [40, -210], [100, -190], [146, -150], [166, -90], [160, -30], [130, -90], [100, -110], [60, -96], [30, -120], [-10, -104], [-50, -122], [-90, -104], [-130, -84]], 14, 0, -110)}" fill="${c}" stroke-width="9"/>`,
  slick: (/** @type {string} */ c) => `<path d="M-146 -30 C-156 -140 -90 -206 0 -206 C90 -206 156 -140 146 -30 C136 -100 110 -136 60 -144 C10 -150 -50 -146 -100 -126 C-126 -110 -140 -76 -146 -30 Z" fill="${c}" stroke-width="9"/>`,
  bob: (/** @type {string} */ c) => `<path d="M-150 0 C-160 -140 -90 -204 0 -204 C90 -204 160 -140 150 0 C140 -60 120 -100 80 -110 L-120 -90 C-136 -70 -146 -40 -150 0 Z" fill="${c}" stroke-width="9"/>`,
  bun: (/** @type {string} */ c) => `<path d="M-146 -20 C-156 -140 -90 -200 0 -200 C90 -200 156 -140 146 -20 C130 -100 90 -130 0 -132 C-90 -130 -130 -100 -146 -20 Z" fill="${c}" stroke-width="9"/>`,
  side: (/** @type {string} */ c) => `<path d="M-148 -30 C-158 -140 -90 -208 0 -208 C90 -208 158 -140 148 -30 C140 -90 120 -120 90 -136 C40 -150 -10 -148 -50 -150 C-90 -140 -120 -110 -136 -80 C-142 -64 -146 -48 -148 -30 Z" fill="${c}" stroke-width="9"/>`,
  bald: (/** @type {string} */ c) => `<path d="M-160 -40 C-164 -80 -156 -110 -140 -130 C-146 -96 -150 -70 -150 -30 Z M160 -40 C164 -80 156 -110 140 -130 C146 -96 150 -70 150 -30 Z" fill="${c}" stroke-width="7"/>`,
  none: () => '',
};
const BACK = {
  bob: (/** @type {string} */ c) => `<path d="M-176 -30 C-190 -170 -100 -222 0 -220 C100 -222 190 -170 176 -30 C180 40 174 90 160 120 L100 120 C120 60 120 0 116 -30 L-116 -30 C-120 0 -120 60 -100 120 L-160 120 C-174 90 -180 40 -176 -30 Z" fill="${c}" stroke-width="9"/>`,
  bun: (/** @type {string} */ c) => `<path d="${circ(0, -214, 52)}" fill="${c}" stroke-width="9"/>`,
  long: (/** @type {string} */ c) => `<path d="M-170 -40 C-190 -170 -100 -222 0 -220 C100 -222 190 -170 170 -40 C176 80 190 200 176 300 L96 300 C110 200 120 100 120 20 L-120 20 C-120 100 -110 200 -96 300 L-176 300 C-190 200 -176 80 -170 -40 Z" fill="${c}" stroke-width="9"/>`,
};
const HAT = {
  cap: (/** @type {string} */ c) => `<path d="M-150 -110 C-140 -200 140 -200 150 -110 Z" fill="${c}" stroke-width="9"/><path d="M60 -116 L230 -110 L60 -96 Z" fill="${c}" stroke-width="7"/>`,
  top: (/** @type {string} */ c) => `<path d="M-110 -150 L-100 -330 L100 -330 L110 -150 Z" fill="${c}" stroke-width="9"/><path d="M-190 -150 L190 -150 L180 -126 L-180 -126 Z" fill="${c}" stroke-width="7"/>`,
  hard: (/** @type {string} */ c) => `<path d="M-160 -100 C-150 -230 150 -230 160 -100 Z" fill="${c}" stroke-width="9"/><path d="M-190 -100 L190 -100 L180 -78 L-180 -78 Z" fill="${c}" stroke-width="7"/>`,
};

/**
 * Build a role from parts.
 * @param {{id: string, skin?: string, skinShade?: string, suit: string, suitShade?: string, torso?: string, hair?: string,
 *   hairCol?: string, back?: string, hat?: string, hatCol?: string, glasses?: string|boolean, head?: string, brows?: string[],
 *   browW?: number, phase?: number, extraFace?: string, white?: boolean}} p
 */
export function role(p) {
  const white = p.white;
  const skin = white ? '#f7f7f5' : (p.skin || '#ecc6a4');
  const hairCol = p.hairCol || '#2a2422';
  const hairKey = /** @type {keyof typeof HAIR} */ (p.hair || 'short');
  const glasses = p.glasses === 'round' ? roundGlasses('#25304a') : p.glasses === 'rect' ? rectGlasses('#1d1b1a') : '';
  return {
    id: p.id, skin, skinShade: white ? '#dcdcd8' : (p.skinShade || '#cf9f7c'), suit: p.suit, suitShade: p.suitShade || '#00000026',
    torso: p.torso || BLAZER('#efece4', null), head: p.head || undefined,
    hairBack: (p.back ? BACK[/** @type {keyof typeof BACK} */ (p.back)](hairCol) : '') + (white ? '' : ears(p.head ? 144 : 160, skin)),
    hair: HAIR[hairKey](hairCol) + (p.hat ? HAT[/** @type {keyof typeof HAT} */ (p.hat)](p.hatCol || '#3a3d44') : ''),
    hairRear: rearHair(hairCol, -204), extraFace: (p.extraFace || '') + glasses, glasses: p.glasses === true,
    brows: p.brows, browW: p.browW, phase: p.phase ?? p.id.length * 0.7,
  };
}

/** the narrator / guide; costume from the film's channel profile (specs/022 `hero`), else the kit default */
export function narrator(/** @type {any} */ hero = {}) {
  const hood = hero.hoodie || '#c9773f';
  return role({ id: 'narrator', skin: '#f0c9a2', skinShade: '#d4a47c', suit: hood, suitShade: '#00000030', torso: HOODIE('#00000022'),
    hair: hero.hair && hero.hair in HAIR ? hero.hair : 'messy', hairCol: hero.hairCol || '#3a2a20',
    hat: hero.hat && hero.hat in HAT ? hero.hat : undefined, glasses: hero.glasses === 'yes' ? 'round' : undefined, phase: 4.4 });
}

export const ROLES = {
  banker:   () => role({ id: 'banker', suit: '#4f535b', suitShade: '#3e4249', torso: BLAZER('#f1eee6', '#a5443a'), head: ovalHead(146, 168, .66), hair: 'slick', hairCol: '#1d1b1d', phase: 5.1 }),
  auditor:  () => role({ id: 'auditor', skin: '#f2d0b2', skinShade: '#d8ae8e', suit: '#56705c', suitShade: '#465c4b', torso: BLAZER('#efece4', null, '#617d67'), head: ovalHead(142, 164, .6), hair: 'bun', back: 'bun', hairCol: '#5a3e2c', glasses: true, phase: 5.6 }),
  trader:   () => role({ id: 'trader', skin: '#c99872', skinShade: '#a8784f', suit: '#4a6a96', suitShade: '#3b5679', torso: BLAZER('#f1eee6', '#c9a64a') + '<path d="M50 260 L110 260 L110 320 L50 320 Z" fill="#f6f2e6" stroke-width="5"/>', hair: 'short', hairCol: '#1f1a18', phase: 6.2 }),
  critic:   () => role({ id: 'critic', skin: '#efcdb0', skinShade: '#d4aa8a', suit: '#9a463d', suitShade: '#7e3830', torso: BLAZER('#f3efe8', null), head: ovalHead(140, 164, .6), hair: 'bob', back: 'bob', hairCol: '#2b2220', brows: ['M-80 -54 Q-54 -62 -26 -54', 'M26 -54 Q54 -62 80 -54'], browW: 7, phase: 6.8 }),
  official: () => role({ id: 'official', suit: '#2b303e', suitShade: '#1f2330', torso: BLAZER('#f1eee6', '#6a2f36'), head: ovalHead(148, 168, .66), hair: 'side', hairCol: '#c9c7c3', phase: 7.3 }),
  worker:   () => role({ id: 'worker', suit: '#5f6d58', suitShade: '#4c5847', torso: SWEATER('#4c5847'), hair: 'short', hairCol: '#4a3426', phase: 2.1 }),
  doctor:   () => role({ id: 'doctor', suit: '#eceeee', suitShade: '#d2d5d6', torso: BLAZER('#a9bacb', null), hair: 'short', hairCol: '#3a2a20', glasses: 'rect', phase: 2.7 }),
  police:   () => role({ id: 'police', suit: '#2b303e', suitShade: '#1f2330', torso: BLAZER('#a9bacb', '#1f2330'), hair: 'short', hairCol: '#1f1a18', hat: 'cap', hatCol: '#2b303e', phase: 3.3 }),
  builder:  () => role({ id: 'builder', suit: '#b07a3a', suitShade: '#8f6230', torso: SWEATER('#8f6230'), hair: 'short', hairCol: '#3a2a20', hat: 'hard', hatCol: '#d9b24a', phase: 3.9 }),
};

const EXTRA_SUITS = ['#5b6670', '#6e5f52', '#55605a', '#4b5160', '#7a6a5a', '#5f5a68', '#3f4a52', '#6c7071'];
const EXTRA_HAIR = /** @type {(keyof typeof HAIR)[]} */ (['short', 'bob', 'messy', 'side', 'bun', 'slick', 'short', 'bald']);
const EXTRA_COL = ['#2a2422', '#5a3e2c', '#7a5a3e', '#1d1b1d', '#8a6a4a', '#3a2a20', '#b5a48a', '#9a9590'];
/** an anonymous extra with a white face (style §1); n picks costume and hair */
export function extra(/** @type {number} */ n) {
  const k = Math.abs(n) % 8, h = Math.abs(n * 3 + 1) % 8;
  return role({ id: 'extra' + n, white: true, suit: EXTRA_SUITS[k], torso: k % 2 ? BLAZER('#ececea', null) : SWEATER('#00000022'),
    hair: EXTRA_HAIR[h], back: EXTRA_HAIR[h] === 'bob' ? 'bob' : EXTRA_HAIR[h] === 'bun' ? 'bun' : undefined, hairCol: EXTRA_COL[(k + h) % 8], phase: n * 0.37 });
}
/** a role with changes: hair, glasses, hat, suit colour */
export function variant(/** @type {any} */ base, /** @type {any} */ ch = {}) {
  const o = Object.assign({}, base);
  if (ch.suit) o.suit = ch.suit;
  if (ch.hair && ch.hair in HAIR) o.hair = HAIR[/** @type {keyof typeof HAIR} */ (ch.hair)](ch.hairCol || '#2a2422');
  if (ch.glasses) o.extraFace = (o.extraFace || '') + (ch.glasses === 'round' ? roundGlasses('#25304a') : rectGlasses('#1d1b1a'));
  if (ch.hat && ch.hat in HAT) o.hair = (o.hair || '') + HAT[/** @type {keyof typeof HAT} */ (ch.hat)](ch.hatCol || '#3a3d44');
  return o;
}
export const ROLE_NAMES = ['narrator', ...Object.keys(ROLES)];
