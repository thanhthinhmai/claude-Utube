// @ts-check
// Sets of the kit (specs/028 T009): parts and sets made of parts. Sets are line-drawn with thinner lines and greyer,
// lower-contrast fills than the characters, one-point rooms, flat day skies, navy nights, purple-to-orange sunsets
// (style §2, §3; visual report "Backgrounds / sets"). About 24 sets per 3 minutes: a set is a list of parts, and a
// scene may build its own with set: 'custom:<name>' from the same parts (FR-005, FR-006).
// Each set gives {html (behind the cast), fg (in front of the cast), floor (feet line), seat? (desk slot)}.
import { circ, oval, box, poly, segOutline, rrect, rng, LW, INK } from '../core.js';

export const PAL = {
  ink: INK, wall: '#cfd2d1', wall2: '#b7bbbb', wallWarm: '#cdc4b4', wallCool: '#b9c3cc', floor: '#6b5a48', floor2: '#5b4030',
  slate: '#a9bacb', navy: '#2b303e', navy2: '#353b4c', sky: '#b9dbe5', skyline: '#93b6c3', skylineFar: '#a9c7d1', grass: '#7d8f62',
  road: '#4d505a', pave: '#c9cbc9', paper: '#f1efe9', metal: '#8d9499', dark: '#23262e', stage: '#26262d', glass: '#c3dbe3',
};
const L2 = LW * 0.5;   // set detail lines: about half the character weight (style §2)
const S = (/** @type {number} */ w = L2) => `stroke="${INK}" stroke-width="${w}" stroke-linejoin="round" stroke-linecap="round"`;

// ---------- parts: (ctx, params) => markup ----------
/** @type {Record<string, (ctx: any, p?: any) => string>} */
export const PARTS = {
  backdrop: (c, p = {}) => `<path d="${box(-120, -120, 2160, 1320)}" fill="${p.col || PAL.wall}" stroke="none"/>`,
  wall: (c, p = {}) => `<path d="${box(-120, -120, 2160, (p.to || 780) + 120)}" fill="${p.col || PAL.wall}" stroke="none"/>` +
    `<path d="${box(-120, (p.to || 780) - 26, 2160, 26)}" fill="${p.trim || PAL.wall2}" stroke="none"/>` + segOutline([[-120, (p.to || 780) - 26], [2040, (p.to || 780) - 26]], L2, INK, false),
  floor: (c, p = {}) => { const y = p.y || 780, col = p.col || PAL.floor; let o = `<path d="${box(-120, y, 2160, 1320 - y)}" fill="${col}" stroke="none"/>` + segOutline([[-120, y], [2040, y]], LW * .6, INK, false);
    if (p.planks !== false) for (let k = 1; k < 5; k++) { const yy = y + k * k * 18; o += `<path d="M-120 ${yy} L2040 ${yy}" fill="none" ${S(3)} opacity=".35"/>`; }
    return o; },
  shade: (c, p = {}) => `<path d="M${p.x || 1500} -120 Q${(p.x || 1500) - 300} 300 ${(p.x || 1500) - 180} ${p.to || 780} L2040 ${p.to || 780} L2040 -120 Z" fill="#000" opacity="${p.op || .08}" stroke="none"/>`,
  window: (c, p = {}) => { const x = p.x ?? 1380, y = p.y ?? 160, w = p.w || 360, h = p.h || 300, night = p.night;
    let o = `<path d="${box(x, y, w, h)}" fill="${night ? PAL.navy : PAL.sky}" stroke="none"/>`;
    const r = rng('win' + x); for (let i = 0; i < 6; i++) { const bw = w / 6, bh = h * (.3 + r() * .5); o += `<path d="${box(x + i * bw + 4, y + h - bh, bw - 8, bh)}" fill="${night ? '#3a4158' : PAL.skyline}" stroke="none"/>`;
      if (night) for (let k = 0; k < 3; k++) o += `<path d="${box(x + i * bw + 12 + k * 10, y + h - bh + 16 + k * 22, 6, 9)}" fill="#e6c36a" stroke="none"/>`; }
    return o + segOutline([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], LW * .6) + `<path d="M${x + w / 2} ${y} L${x + w / 2} ${y + h} M${x} ${y + h / 2} L${x + w} ${y + h / 2}" fill="none" ${S()}/>`; },
  shelf: (c, p = {}) => { const x = p.x ?? 140, y = p.y ?? 300; let o = `<path d="${box(x, y, 260, 460)}" fill="#6e5440" stroke="none"/>` + segOutline([[x, y], [x + 260, y], [x + 260, y + 460], [x, y + 460]], L2);
    const cols = ['#7a5048', '#5c6b58', '#55657a', '#8a7a58', '#6b5a6b'], r = rng('shelf' + x);
    for (let k = 0; k < 4; k++) { const yy = y + 20 + k * 110; o += `<path d="M${x} ${yy + 96} L${x + 260} ${yy + 96}" fill="none" ${S()}/>`; let xx = x + 12;
      while (xx < x + 236) { const bw = 14 + r() * 14, bh = 60 + r() * 30; o += `<path d="${box(xx, yy + 96 - bh, bw, bh)}" fill="${cols[(r() * 5) | 0]}" ${S(2)}/>`; xx += bw + 3; } }
    return o; },
  clock: (c, p = {}) => `<path d="${circ(p.x ?? 1000, p.y ?? 200, 56)}" fill="${PAL.paper}" ${S(LW * .5)}/><path d="M${p.x ?? 1000} ${p.y ?? 200} L${p.x ?? 1000} ${(p.y ?? 200) - 34} M${p.x ?? 1000} ${p.y ?? 200} L${(p.x ?? 1000) + 24} ${(p.y ?? 200) + 10}" fill="none" ${S(5)}/>`,
  picture: (c, p = {}) => `<path d="${box(p.x ?? 700, p.y ?? 220, 180, 130)}" fill="#a9b39a" ${S()}/><path d="M${(p.x ?? 700) + 20} ${(p.y ?? 220) + 110} L${(p.x ?? 700) + 80} ${(p.y ?? 220) + 50} L${(p.x ?? 700) + 120} ${(p.y ?? 220) + 90} L${(p.x ?? 700) + 160} ${(p.y ?? 220) + 60}" fill="none" ${S(3)}/>`,
  door: (c, p = {}) => `<path d="${box(p.x ?? 1700, p.y ?? 380, 200, 400)}" fill="#7a6250" ${S()}/><path d="${circ((p.x ?? 1700) + 168, (p.y ?? 380) + 210, 9)}" fill="#c9b46a" ${S(2)}/>`,
  plant: (c, p = {}) => { const x = p.x ?? 260, y = p.y ?? 680; return `<g transform="translate(${x} ${y}) scale(${p.s || 1})"><path d="M-50 0 L50 0 L40 90 L-40 90 Z" fill="#8a6a54" ${S()}/><path d="${circ(0, -60, 70)}" fill="#5f7a58" ${S()}/><path d="${circ(-40, -20, 46)}" fill="#6a8562" ${S()}/><path d="${circ(44, -26, 44)}" fill="#6a8562" ${S()}/></g>`; },
  lamp: (c, p = {}) => { const x = p.x ?? 520, y = p.y ?? 660; return `<path d="M${x} ${y} L${x + 30} ${y - 120} L${x + 90} ${y - 150}" fill="none" ${S(6)}/><path d="M${x + 60} ${y - 170} L${x + 140} ${y - 150} L${x + 110} ${y - 110} Z" fill="#3a3d44" ${S()}/><path d="M${x + 125} ${y - 130} L${x + 260} ${y + 30} L${x + 40} ${y + 30} Z" fill="#f5e6a8" opacity=".18" stroke="none"/>`; },
  desk: (c, p = {}) => { const x = p.x ?? 520, w = p.w || 880, y = p.y ?? 690; return `<path d="${poly([[x, y + 60], [x + w, y + 60], [x + w - 40, y], [x + 40, y]])}" fill="#7b5f48" stroke="none"/>` + segOutline([[x, y + 60], [x + w, y + 60], [x + w - 40, y], [x + 40, y]], L2) +
    `<path d="${box(x, y + 60, w, 300)}" fill="#64503e" stroke="none"/>` + segOutline([[x, y + 60], [x + w, y + 60], [x + w, y + 360], [x, y + 360]], L2) + `<path d="M${x + w / 2} ${y + 60} L${x + w / 2} ${y + 360}" fill="none" ${S(3)} opacity=".5"/>`; },
  monitor: (c, p = {}) => { const x = p.x ?? 1100, y = p.y ?? 560; return `<path d="${box(x, y, 200, 130)}" fill="${PAL.dark}" ${S()}/><path d="${box(x + 12, y + 12, 176, 106)}" fill="#5f7d8f" stroke="none"/><path d="M${x + 100} ${y + 130} L${x + 100} ${y + 150} M${x + 60} ${y + 152} L${x + 140} ${y + 152}" fill="none" ${S(6)}/>`; },
  table: (c, p = {}) => { const y = p.y ?? 790; return `<path d="${poly([[120, y], [1800, y], [1880, y + 100], [40, y + 100]])}" fill="#7b5f48" stroke="none"/>` + segOutline([[120, y], [1800, y], [1880, y + 100], [40, y + 100]], LW * .6) + `<path d="${box(40, y + 100, 1840, 420)}" fill="#5f4836" stroke="none"/>` + segOutline([[40, y + 100], [1880, y + 100]], LW * .6, INK, false); },
  newsdesk: (c, p = {}) => `<path d="M140 760 L1000 760 L1040 1200 L100 1200 Z" fill="#b9c0cc" stroke="none"/>` + segOutline([[140, 760], [1000, 760], [1040, 1200]], LW * .6, INK, false) + segOutline([[100, 1200], [140, 760]], LW * .6, INK, false) + `<path d="M140 760 L1000 760 L1004 800 L136 800 Z" fill="#dfe4ea" stroke="none"/>`,
  screen: (c, p = {}) => { const x = p.x ?? 1080, y = p.y ?? 110, w = p.w || 680, h = p.h || 420; return `<path d="${rrect(x - 16, y - 16, w + 32, h + 32, 16)}" fill="#1b1d22" ${S(LW * .6)}/><path d="${box(x, y, w, h)}" fill="#151a26" stroke="none"/>`; },
  podium: (c, p = {}) => { const x = p.x ?? 960, y = p.y ?? 700; return `<path d="${poly([[x - 120, y], [x + 120, y], [x + 100, y + 320], [x - 100, y + 320]])}" fill="#6e5440" stroke="none"/>` + segOutline([[x - 120, y], [x + 120, y], [x + 100, y + 320], [x - 100, y + 320]], LW * .6) + `<path d="M${x - 30} ${y} L${x - 50} ${y - 70} M${x + 30} ${y} L${x + 50} ${y - 70}" fill="none" ${S(5)}/>`; },
  sky: (c, p = {}) => { const k = p.kind || 'day'; if (k === 'night') return `<path d="${box(-120, -120, 2160, 1320)}" fill="${PAL.navy}" stroke="none"/>` + Array.from({ length: 30 }, (_, i) => { const r = rng('st' + i); return `<path d="${circ(r() * 1920, r() * 500, 3)}" fill="#e8e4d0" stroke="none"/>`; }).join('') + `<path d="${circ(1580, 180, 56)}" fill="#efe8c8" ${S()}/>`;
    if (k === 'sunset') return `<path d="${box(-120, -120, 2160, 1320)}" fill="url(#skSunset)" stroke="none"/>`;
    return `<path d="${box(-120, -120, 2160, 1320)}" fill="${PAL.sky}" stroke="none"/>` + [[300, 150], [1400, 110]].map(([x, y]) => `<path d="M${x} ${y} q30 -50 80 -20 q40 -40 90 0 q50 0 40 40 L${x - 20} ${y + 20} q-30 -20 20 -20 Z" fill="#f4f6f6" ${S(4)}/>`).join(''); },
  skyline: (c, p = {}) => { const y = p.y ?? 620, col = p.col || PAL.skyline, r = rng('sky' + (p.seed || 1)); let o = '', x = -120;
    while (x < 2040) { const w = 120 + r() * 160, h = 160 + r() * 340; o += `<path d="${box(x, y - h, w, h + 400)}" fill="${col}" stroke="none"/>`; x += w + 6; } return o; },
  ground: (c, p = {}) => `<path d="${box(-120, p.y ?? 760, 2160, 600)}" fill="${p.col || PAL.grass}" stroke="none"/>` + segOutline([[-120, p.y ?? 760], [2040, p.y ?? 760]], L2, INK, false),
  road: (c, p = {}) => { const y = p.y ?? 820; return `<path d="M-120 ${y} L2040 ${y} L2040 1200 L-120 1200 Z" fill="${PAL.road}" stroke="none"/>` + segOutline([[-120, y], [2040, y]], LW * .6, INK, false) + `<path d="M-120 ${y + 150} L2040 ${y + 150}" fill="none" stroke="#c9c6b8" stroke-width="8" stroke-dasharray="60 50"/>`; },
  pave: (c, p = {}) => { const y = p.y ?? 900; return `<path d="M-120 ${y} L2040 ${y} L2040 1200 L-120 1200 Z" fill="${PAL.pave}" stroke="none"/>` + segOutline([[-120, y], [2040, y]], LW * .6, INK, false); },
  tower: (c, p = {}) => { const x = p.x ?? 960, w = p.w || 520, h = p.h || 560, base = p.base ?? 820, col = p.col || '#8b97a8'; let o = `<path d="${box(x - w / 2, base - h, w, h)}" fill="${col}" stroke="none"/>` + segOutline([[x - w / 2, base], [x - w / 2, base - h], [x + w / 2, base - h], [x + w / 2, base]], LW * .6, INK, false);
    for (let yy = base - h + 40; yy < base - 80; yy += 70) for (let xx = x - w / 2 + 30; xx < x + w / 2 - 40; xx += 64) o += `<path d="${box(xx, yy, 36, 44)}" fill="${p.night ? '#e6c36a' : PAL.glass}" ${S(2.5)}${p.night && ((xx + yy) % 3) ? ' opacity=".35"' : ''}/>`;
    return o + `<path d="${box(x - 60, base - 110, 120, 110)}" fill="#5d6470" ${S()}/>`; },
  capitol: (c, p = {}) => `<g transform="translate(960 600)"><path d="M-520 260 L-520 40 L520 40 L520 260 Z" fill="#e8e5dc" stroke="none"/>${segOutline([[-520, 260], [-520, 40], [520, 40], [520, 260]], LW * .6, INK, false)}<path d="M-560 40 L0 -60 L560 40 Z" fill="#dcd8cc" ${S()}/>
    <path d="M-170 -60 C-170 -230 170 -230 170 -60 Z" fill="#e8e5dc" ${S()}/><path d="M-10 -210 L-10 -270 L10 -270 L10 -210 Z" fill="#e8e5dc" ${S(4)}/><g fill="none" ${S(5)}>${Array.from({ length: 13 }, (_, i) => `<path d="M${-480 + i * 80} 70 L${-480 + i * 80} 250"/>`).join('')}</g></g>`,
  factory: (c, p = {}) => `<path d="M300 820 L300 520 L560 400 L560 520 L820 400 L820 520 L1080 400 L1080 820 Z" fill="#8a8580" stroke="none"/>${segOutline([[300, 820], [300, 520], [560, 400], [560, 520], [820, 400], [820, 520], [1080, 400], [1080, 820]], LW * .6, INK, false)}
    <path d="${box(1180, 240, 90, 580)}" fill="#7a6a62" ${S()}/><path d="${box(1330, 320, 80, 500)}" fill="#7a6a62" ${S()}/><path d="${circ(1240, 200, 50)} ${circ(1290, 150, 40)} ${circ(1370, 270, 44)}" fill="#c9cbcb" opacity=".8" ${S(4)}/>`,
  racks: (c, p = {}) => Array.from({ length: p.n || 7 }, (_, i) => { const x = 220 + i * 240; let o = `<path d="${box(x, 200, 180, 600)}" fill="#2c3038" stroke="none"/>` + segOutline([[x, 200], [x + 180, 200], [x + 180, 800], [x, 800]], L2);
    for (let k = 0; k < 9; k++) o += `<path d="M${x + 16} ${236 + k * 62} L${x + 164} ${236 + k * 62}" fill="none" stroke="#5c6470" stroke-width="10"/><path d="${circ(x + 150, 236 + k * 62, 5)}" fill="${(i + k) % 3 ? '#6ab07a' : '#d9b24a'}" stroke="none"/>`; return o; }).join(''),
  vault: (c, p = {}) => { const x = p.x ?? 960, y = p.y ?? 480; return `<path d="${rrect(x - 230, y - 230, 460, 460, 30)}" fill="#7d858c" ${S(LW * .6)}/><path d="${circ(x, y, 150)}" fill="#6a7178" ${S()}/><path d="${circ(x, y, 44)}" fill="#8d959c" ${S()}/>` + [0, 1, 2, 3].map(k => { const a = k * Math.PI / 2 + .4; return `<path d="M${x + Math.cos(a) * 44} ${y + Math.sin(a) * 44} L${x + Math.cos(a) * 130} ${y + Math.sin(a) * 130}" fill="none" ${S(10)}/>`; }).join(''); },
  stall: (c, p = {}) => { const x = p.x ?? 860, y = p.y ?? 560; let o = `<path d="M${x - 300} ${y - 260} L${x + 300} ${y - 260} L${x + 340} ${y - 180} L${x - 340} ${y - 180} Z" fill="#e7d9b0" ${S()}/>`;
    for (let i = 0; i < 6; i++) o += `<path d="M${x - 300 + i * 100} ${y - 260} L${x - 250 + i * 100} ${y - 260} L${x - 210 + i * 100} ${y - 180} L${x - 260 + i * 100} ${y - 180} Z" fill="#b8513f" stroke="none"/>`;
    return o + `<path d="M${x - 280} ${y - 180} L${x - 280} ${y + 200} M${x + 280} ${y - 180} L${x + 280} ${y + 200}" fill="none" ${S(10)}/><path d="${box(x - 320, y + 40, 640, 160)}" fill="#d9c08a" ${S()}/>`; },
  map: (c, p = {}) => `<path d="${box(-120, -120, 2160, 1320)}" fill="#9fbccc" stroke="none"/><path d="${'M300 300 C420 200 640 260 760 220 C900 180 1080 260 1200 240 C1380 210 1560 300 1620 420 C1680 560 1560 700 1420 760 C1240 840 1040 800 880 860 C700 920 520 860 420 760 C300 640 220 420 300 300 Z'}" fill="#b9c79a" ${S()}/>`,
  spot: (c, p = {}) => `<path d="${box(-120, -120, 2160, 1320)}" fill="${PAL.stage}" stroke="none"/><path d="M${(p.x ?? 960) - 120} -120 L${(p.x ?? 960) + 120} -120 L${(p.x ?? 960) + 420} 980 L${(p.x ?? 960) - 420} 980 Z" fill="#f4ecd0" opacity=".14" stroke="none"/><path d="${oval(p.x ?? 960, 980, 440, 70)}" fill="#f4ecd0" opacity=".12" stroke="none"/>`,
  stagefloor: (c, p = {}) => `<path d="M-120 860 L2040 860 L2040 1200 L-120 1200 Z" fill="#3a3038" stroke="none"/>` + segOutline([[-120, 860], [2040, 860]], LW * .6, INK, false),
  audience: (c, p = {}) => Array.from({ length: 13 }, (_, i) => `<path d="${circ(i * 160 - 20, 1120 + (i % 2) * 20, 78)}" fill="#15151a" stroke="none"/>`).join(''),
  ticker: (c, p = {}) => { const x = -((c.lt * 120) % 900); return `<path d="${box(-120, 70, 2160, 150)}" fill="#101318" stroke="none"/>` + segOutline([[-120, 220], [2040, 220]], L2, INK, false) + Array.from({ length: 14 }, (_, i) => `<path d="M${x + i * 220} 170 l40 -40 l40 20 l40 -50" fill="none" stroke="${i % 3 ? '#6ab07a' : '#c0584a'}" stroke-width="10"/>`).join(''); },
  deskrow: (c, p = {}) => `<g fill="#1d2438">${Array.from({ length: 6 }, (_, i) => `<path d="${rrect(i * 340 - 40, 300, 300, 200, 10)}" ${S(L2)}/>`).join('')}</g>` + Array.from({ length: 6 }, (_, i) => `<path d="M${i * 340} 460 L${i * 340 + 60} 420 L${i * 340 + 120} 440 L${i * 340 + 200} 360 L${i * 340 + 240} 380" fill="none" stroke="#6ab07a" stroke-width="7"/>`).join(''),
  couch: (c, p = {}) => { const x = p.x ?? 1400, y = p.y ?? 600; return `<path d="${rrect(x - 260, y, 520, 200, 30)}" fill="#7d6b5e" ${S()}/><path d="${rrect(x - 240, y + 90, 480, 110, 20)}" fill="#8e7b6c" ${S()}/>`; },
  bench: (c, p = {}) => `<path d="${box(p.x ?? 1300, p.y ?? 760, 360, 30)}" fill="#7b5f48" ${S()}/><path d="M${(p.x ?? 1300) + 30} ${(p.y ?? 760) + 30} L${(p.x ?? 1300) + 30} ${(p.y ?? 760) + 110} M${(p.x ?? 1300) + 330} ${(p.y ?? 760) + 30} L${(p.x ?? 1300) + 330} ${(p.y ?? 760) + 110}" fill="none" ${S(8)}/>`,
  tree: (c, p = {}) => { const x = p.x ?? 300, y = p.y ?? 760; return `<path d="M${x} ${y} L${x} ${y - 200}" fill="none" ${S(18)}/><path d="${circ(x, y - 280, 120)}" fill="#6f8a5c" ${S()}/><path d="${circ(x - 80, y - 220, 80)}" fill="#7d9868" ${S()}/>`; },
  crates: (c, p = {}) => Array.from({ length: 10 }, (_, i) => { const x = 220 + (i % 5) * 170, y = 640 - Math.floor(i / 5) * 140; return `<path d="${box(x, y, 150, 130)}" fill="#a8885e" ${S()}/><path d="M${x} ${y} L${x + 150} ${y + 130} M${x + 150} ${y} L${x} ${y + 130}" fill="none" ${S(3)} opacity=".6"/>`; }).join(''),
  benchlab: (c, p = {}) => `<path d="${box(200, 680, 1520, 40)}" fill="#e2e4e4" ${S()}/><path d="${box(200, 720, 1520, 300)}" fill="#9aa6ad" ${S()}/>` + [420, 620, 1300].map(x => `<path d="M${x} 680 L${x - 20} 600 L${x + 20} 600 Z" fill="#b9d8c6" ${S(4)}/>`).join(''),
  chalkboard: (c, p = {}) => `<path d="${box(240, 150, 980, 520)}" fill="#2f4038" stroke="none"/>` + segOutline([[216, 126], [1244, 126], [1244, 694], [216, 694]], LW * .6) + `<path d="${box(230, 694, 1000, 22)}" fill="#6e4a2c" ${S()}/>`,
  silhouettes: (c, p = {}) => `<path d="${circ(160, 1080, 210)}" fill="#1b1c20" stroke="none"/><path d="${circ(1790, 1100, 190)}" fill="#1b1c20" stroke="none"/>`,
  rail: (c, p = {}) => `<path d="M-120 960 L2040 960" fill="none" stroke="#5b6070" stroke-width="18"/>` + Array.from({ length: 12 }, (_, i) => `<path d="M${i * 180} 960 L${i * 180} 1200" fill="none" stroke="#5b6070" stroke-width="12"/>`).join(''),
};

// ---------- sets: lists of parts; floor = feet line for standing people ----------
/** @type {Record<string, {parts: any[], fg?: any[], floor: number, seat?: boolean}>} */
export const SETS = {
  'office':          { parts: [['wall', { col: PAL.wallWarm }], ['shade', { x: 1500 }], ['window', { x: 760, y: 140, w: 420, h: 300 }], ['shelf', { x: 1560, y: 300 }], ['picture', { x: 330, y: 230 }], ['floor', { col: PAL.floor2 }], ['plant', { x: 220, y: 680 }]], fg: [['desk', {}], ['monitor', { x: 1120, y: 560 }], ['lamp', { x: 560, y: 690 }]], floor: 1010, seat: true },
  'meeting':         { parts: [['wall', { to: 760 }], ['window', { x: 1380, y: 160 }], ['clock', { x: 500, y: 220 }], ['floor', { y: 760 }]], fg: [['table', {}]], floor: 900 },
  'whiteboard-room': { parts: [['wall', { to: 780 }], ['shade', { x: 1700, op: .06 }], ['floor', {}], ['plant', { x: 1780, y: 690 }]], floor: 960, seat: false },
  'chalk-room':      { parts: [['wall', { col: '#b9ad94', to: 780 }], ['clock', { x: 1660, y: 300 }], ['floor', {}], ['chalkboard', {}]], floor: 960 },
  'tv-room':         { parts: [['wall', { col: '#d3cdc2', to: 780 }], ['window', { x: 1500, y: 180, w: 280, h: 240 }], ['floor', {}]], fg: [], floor: 960 },
  'newsroom':        { parts: [['backdrop', { col: '#2c3550' }], ['screen', {}]], fg: [['newsdesk', {}]], floor: 880 },
  'stage':           { parts: [['backdrop', { col: PAL.stage }], ['screen', { x: 420, y: 60, w: 1080, h: 560 }], ['stagefloor', {}]], fg: [['audience', {}]], floor: 900 },
  'trading-floor':   { parts: [['backdrop', { col: '#2b3550' }], ['ticker', {}], ['deskrow', {}], ['floor', { y: 780, col: '#3a3f52', planks: false }]], fg: [['rail', {}]], floor: 980 },
  'street-day':      { parts: [['sky', {}], ['skyline', { y: 640, col: PAL.skylineFar, seed: 2 }], ['tower', { x: 960, w: 640, h: 560, base: 900 }], ['pave', { y: 900 }]], floor: 1000 },
  'street-night':    { parts: [['sky', { kind: 'night' }], ['skyline', { y: 660, col: '#2f354a', seed: 3 }], ['tower', { x: 960, w: 600, h: 520, base: 900, col: '#3d4458', night: true }], ['pave', { y: 900 }]], floor: 1000 },
  'government':      { parts: [['sky', { kind: 'sunset' }], ['capitol', {}], ['ground', { y: 860 }]], floor: 1000 },
  'hq':              { parts: [['sky', {}], ['skyline', { y: 700, col: PAL.skylineFar, seed: 4 }], ['tower', { x: 960, w: 760, h: 620, base: 900, col: '#9aa4b0' }], ['tree', { x: 260, y: 900 }], ['tree', { x: 1680, y: 900 }], ['pave', { y: 900 }]], floor: 1040 },
  'factory':         { parts: [['sky', {}], ['factory', {}], ['ground', { y: 820, col: '#8a8f82' }]], floor: 1000 },
  'data-center':     { parts: [['wall', { col: '#20232b', trim: '#2c3038', to: 860 }], ['racks', {}], ['floor', { y: 860, col: '#3a3f4a', planks: false }]], floor: 1010 },
  'vault-room':      { parts: [['wall', { col: '#bfc3c4', to: 800 }], ['vault', { x: 960, y: 450 }], ['floor', { y: 800, col: '#5e5a56' }]], floor: 1000 },
  'hearing-room':    { parts: [['wall', { col: '#b8a888', to: 760 }], ['podium', { x: 960, y: 420 }], ['floor', { y: 760 }]], fg: [['table', { y: 820 }]], floor: 900 },
  'living-room':     { parts: [['wall', { col: '#cfc4b0' }], ['window', { x: 320, y: 180, w: 320, h: 280 }], ['picture', { x: 1000, y: 230 }], ['couch', { x: 1400, y: 600 }], ['floor', {}], ['plant', { x: 1800, y: 690 }]], floor: 980 },
  'market-stall':    { parts: [['sky', {}], ['ground', { y: 660 }], ['stall', {}]], floor: 1000 },
  'map':             { parts: [['map', {}]], floor: 1040 },
  'spotlight':       { parts: [['spot', {}]], floor: 980 },
  'sky':             { parts: [['sky', {}], ['ground', { y: 900 }]], floor: 1040 },
  'sunset-city':     { parts: [['sky', { kind: 'sunset' }], ['skyline', { y: 760, col: '#6a5f7a', seed: 5 }], ['pave', { y: 900 }]], floor: 1000 },
  'classroom':       { parts: [['wall', { col: '#c9c2a8', to: 780 }], ['chalkboard', {}], ['window', { x: 1440, y: 180, w: 320, h: 260 }], ['floor', {}]], floor: 980 },
  'lab':             { parts: [['wall', { col: PAL.wallCool, to: 760 }], ['window', { x: 1460, y: 160, w: 300, h: 240 }], ['floor', { y: 760, col: '#8a9095', planks: false }]], fg: [['benchlab', {}]], floor: 900 },
  'warehouse':       { parts: [['wall', { col: '#a9a39a', to: 800 }], ['crates', {}], ['floor', { y: 800, col: '#6a655e', planks: false }]], floor: 1000 },
  'park':            { parts: [['sky', {}], ['skyline', { y: 640, col: PAL.skylineFar, seed: 6 }], ['ground', { y: 720 }], ['tree', { x: 300, y: 760 }], ['tree', { x: 1650, y: 760 }], ['bench', { x: 1300, y: 760 }]], floor: 1000 },
  'night-sky':       { parts: [['sky', { kind: 'night' }], ['skyline', { y: 760, col: '#252a3c', seed: 7 }], ['pave', { y: 900 }]], floor: 1000 },
  'dark':            { parts: [['backdrop', { col: '#2b303e' }]], floor: 1000 },
  'ots-office':      { parts: [['wall', { col: PAL.wallWarm }], ['window', { x: 700, y: 140, w: 420, h: 300 }], ['floor', { col: PAL.floor2 }]], fg: [['silhouettes', {}]], floor: 1010 },
};
export const SET_NAMES = Object.keys(SETS);
export const PART_NAMES = Object.keys(PARTS);

/** shared gradients the sets use */
export const DEFS = `<linearGradient id="skSunset" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a4a6e"/><stop offset=".55" stop-color="#8f6f86"/><stop offset="1" stop-color="#d39a76"/></linearGradient>`;

/**
 * Build a set by name, or from a list of parts (custom:).
 * @param {string|any[]} set @param {any} ctx {lt} @param {any} [custom] {parts, fg, floor}
 * @returns {{html: string, fg: string, floor: number, seat: boolean}}
 */
export function buildSet(set, ctx, custom) {
  const def = custom || (Array.isArray(set) ? { parts: set, floor: 1000 } : SETS[set]);
  if (!def) return { html: PARTS.backdrop(ctx, { col: '#7a2a2a' }), fg: '', floor: 1000, seat: false };
  const run = (/** @type {any[]} */ list) => (list || []).map(([n, p]) => (PARTS[n] ? PARTS[n](ctx, p || {}) : '')).join('');
  return { html: run(def.parts), fg: run(def.fg || []), floor: def.floor || 1000, seat: !!def.seat };
}
