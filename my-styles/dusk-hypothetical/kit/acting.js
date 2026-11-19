// Acting of the Dusk Hypothetical kit (specs/023 FR-008; TEMPLATE.md §11). Pure functions of time: no three.js, no
// state between frames, so render(t) stays deterministic and node --test runs them.
//   actState(acts, lt, rise): arms target and blend, head tilt/turn/pitch, face, from a cast member's act list
//   blinkOn(seed, t, every): is the figure blinking at film time t
//   talkOn(talk, lt): is the mouth open (talk spans in scene time)
//   breath(seed, t): chest scale
import { mulberry } from './plan.js';

export const RISE = [0.25, 0.83];          // template.json → motion.rise_s (p25–p75); median 0.417
export const BLINK_S = 0.12;
const LOOK = { left: [0.55, 0], right: [-0.55, 0], up: [0, -0.32], down: [0, 0.3], camera: [0, 0] };
const ARM_ACTS = new Set(['raise-hand', 'wave', 'point', 'shrug-up', 'hands-face', 'cheer']);

export const ease = (u) => { u = Math.min(1, Math.max(0, u)); return u * u * (3 - 2 * u); };

// rise time of one act: the style's median, kept inside the measured range
export function riseOf(template) {
  const r = template && template.motion && template.motion.rise_s_p50;
  return Math.min(RISE[1], Math.max(RISE[0], r || 0.417));
}

// state of one cast member at scene time lt
export function actState(acts = [], lt = 0, rise = 0.417, base = {}) {
  const st = { arms: null, from: null, w: 1, face: base.face || null, tilt: 0, turn: 0, pitch: 0, wave: 0, swapAt: null };
  const list = [...acts].filter((a) => a[0] <= lt).sort((a, b) => a[0] - b[0]);
  let prevArms = null, lastArms = null;
  let tiltT = null, tiltOn = false, look = null, lookT = null, prevLook = [0, 0];
  for (const [t, name] of list) {
    if (ARM_ACTS.has(name) || name.startsWith('pose:')) { prevArms = lastArms; lastArms = { name, t }; }
    else if (name.startsWith('face:')) st.face = name.slice(5);
    else if (name === 'tilt-head') { tiltT = t; tiltOn = true; }
    else if (name.startsWith('look:')) { prevLook = look ? LOOK[look] : [0, 0]; look = name.slice(5); lookT = t; }
    else if (name === 'nod') { const u = (lt - t) / 0.6; if (u < 1) st.pitch += 0.25 * Math.sin(Math.PI * u); }
    else if (name === 'lean-in') st.pitch += 0.14 * ease((lt - t) / rise);
    else if (name === 'swap') st.swapAt = t;
  }
  if (lastArms) {
    st.arms = lastArms.name.startsWith('pose:') ? lastArms.name.slice(5) : lastArms.name;
    st.from = prevArms ? (prevArms.name.startsWith('pose:') ? prevArms.name.slice(5) : prevArms.name) : null;
    st.w = ease((lt - lastArms.t) / rise);
    if (st.arms === 'wave') st.wave = Math.sin((lt - lastArms.t) * Math.PI * 2 * 2.2) * ease((lt - lastArms.t) / rise);
  }
  if (tiltOn) st.tilt = 0.22 * ease((lt - tiltT) / rise);
  if (look) {
    const w = ease((lt - lookT) / rise), to = LOOK[look] || [0, 0];
    st.turn = prevLook[0] + (to[0] - prevLook[0]) * w;
    st.pitch += prevLook[1] + (to[1] - prevLook[1]) * w;
  }
  return st;
}

// blink times: intervals drawn in [every[0], every[1]] seconds from the figure's seed, over film time
export function blinkOn(seed, t, every = [2, 5]) {
  if (!every) return false;
  const r = mulberry(seed * 7919 + 13);
  let at = r() * every[1];
  while (at <= t) {
    if (t - at < BLINK_S) return true;
    at += every[0] + (every[1] - every[0]) * r();
  }
  return false;
}

// mouth flaps about 7 times a second inside talk spans
export function talkOn(talk = [], lt = 0) {
  return talk.some(([a, b]) => lt >= a && lt < b && Math.sin((lt - a) * Math.PI * 2 * 7.2) > -0.2);
}

export const breath = (seed, t) => 1 + 0.012 * Math.sin((t / 3.6) * Math.PI * 2 + (seed % 17));

// transitions (TEMPLATE.md §13): how black the frame is at scene time lt — a dip is ≈ 0.12 s of black across the cut, a
// fade goes to black and back over ≈ 0.27 s; tr = template.json → transitions
export function blackAt(scene, next, lt, tr = {}) {
  const dipH = ((tr.dip_s && tr.dip_s[0]) || 0.117) / 2, fadeH = ((tr.fade_s && tr.fade_s[1]) || 0.267) / 2;
  let black = 0;
  if ((scene.trans === 'dip' && lt < dipH) || (next && next.trans === 'dip' && scene.dur - lt < dipH)) black = 1;
  if (scene.trans === 'fade' && lt < fadeH) black = Math.max(black, 1 - lt / fadeH);
  if (next && next.trans === 'fade' && scene.dur - lt < fadeH) black = Math.max(black, 1 - (scene.dur - lt) / fadeH);
  return black;
}

// the light-streak swap (motion-depth §2.3): its strength at lt for a swap at `at`, ≈ 0.15 s long
export function streakAt(lt, at, tr = {}) {
  const half = (tr.streak_s || 0.15) / 2, d = Math.abs(lt - at);
  return d < half ? 1 - d / half : 0;
}
