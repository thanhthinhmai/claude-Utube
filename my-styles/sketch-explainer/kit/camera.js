// @ts-check
// Camera of the kit (specs/028 T017, research R5). Pure: no DOM. Evidence (my-styles/sketch-explainer/EVIDENCE.md):
// per shot push 33%, pull 23%, still 22% (mostly inserts), follow 10–20%, drift 2%; push median 3.3 %/s, pull 8.6 %/s
// (reveal), constant speed with no ease-in; neighbouring shots alternate push and pull; scale mix medium 47%, wide 19%,
// very wide 14%, close 11%, extreme close 3%; change scale on ~2/3 of cuts, never more than 4 shots at one scale.
// The proof frame passed with a linear move, a small drift and a hold at the end of the shot; on a whole film the
// hold is 20% so that locked shots plus holds stay inside the measured still_ratio (0.10–0.44).

export const DEFAULTS = { push: 3.3, pull: 8.6, pullCap: 0.3, hold: 0.2, drift: 60, follow: 110, mix: { push: 0.33, pull: 0.23, still: 0.22, follow: 0.2, drift: 0.02 } };
export const SIZES = ['ecu', 'cu', 'med', 'wide', 'huge', 'insert', 'ots'];
export const MOVES = ['push', 'pull', 'still', 'follow', 'drift'];
/** share of the frame height a head fills, by shot size (head diameter = 330 × s world units) */
const HEAD_SHARE = { ecu: 0.62, cu: 0.45, med: 0.24, ots: 0.24, wide: 0.12 };

function hash01(/** @type {string} */ s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return ((h >>> 0) % 100000) / 100000; }

/** pick a move for a scene: explicit, else still for inserts, else by the measured mix, alternating push and pull */
export function pickMove(/** @type {any} */ scene, /** @type {string|null} */ prev) {
  const want = scene.cam && scene.cam.move;
  if (want && want !== 'auto') return want;
  const size = (scene.cam && scene.cam.size) || 'med';
  if (size === 'insert' || scene.card) return 'still';
  const m = DEFAULTS.mix, u = hash01(String(scene.id) + ':move');
  let pick = u < m.push ? 'push' : u < m.push + m.pull ? 'pull' : u < m.push + m.pull + m.still ? 'still' : u < 1 - m.drift ? 'follow' : 'drift';
  if (pick === prev && (pick === 'push' || pick === 'pull')) pick = pick === 'push' ? 'pull' : 'push';
  return pick;
}

/**
 * Framing and move for one scene.
 * @param {any} scene {id, dur, cam?, card?}
 * @param {string|null} prevMove
 * @param {{x: number, y: number, s: number}|null} focus main person (world), y = head centre
 * @param {{x: number, y: number, w: number, h: number}|null} board
 */
export function camFor(scene, prevMove, focus, board) {
  const c = scene.cam || {};
  const size = c.size || (focus ? 'med' : board ? 'insert' : 'huge');
  const move = pickMove(scene, prevMove);
  let cx = 960, cy = 540, z = 1;
  if (c.cx != null) { cx = c.cx; cy = c.cy ?? 540; z = c.z ?? 1; }
  else if (size === 'insert' && board) { z = Math.min(1920 / (board.w * 1.2), 1080 / (board.h * 1.3)); cx = board.x + board.w / 2; cy = board.y + board.h / 2 + 20; }
  else if (focus && size in HEAD_SHARE) {
    z = HEAD_SHARE[/** @type {keyof typeof HEAD_SHARE} */ (size)] * 1080 / (330 * focus.s);
    cx = focus.x; cy = focus.y + (size === 'ecu' ? 0 : size === 'cu' ? 60 : size === 'wide' ? 300 : 160) * focus.s;
    if (board && (size === 'med' || size === 'wide')) {
      // a person beside a board: frame both (board and the person from head to waist)
      const x0 = Math.min(board.x, focus.x - 260 * focus.s), x1 = Math.max(board.x + board.w, focus.x + 260 * focus.s);
      const y0 = Math.min(board.y, focus.y - 220 * focus.s), y1 = Math.max(board.y + board.h, focus.y + 330 * focus.s);
      z = Math.min(z, 1920 / ((x1 - x0) * 1.12), 1080 / ((y1 - y0) * 1.15));
      cx = (x0 + x1) / 2; cy = (y0 + y1) / 2;
    }
  }
  z = Math.max(1, Math.min(4, z));
  const d = scene.dur || 3, hold = c.hold ?? DEFAULTS.hold, run = d * (1 - hold);
  const dir = hash01(String(scene.id) + ':dir') < 0.5 ? -1 : 1;
  let z0 = z, z1 = z, cx1 = cx, cy1 = cy;
  if (move === 'push') { z1 = z * (1 + DEFAULTS.push / 100 * run); cx1 = cx + dir * DEFAULTS.drift * run / z; cy1 = cy - DEFAULTS.drift * 0.25 * run / z; }
  else if (move === 'pull') { z0 = z * (1 + Math.min(DEFAULTS.pullCap, DEFAULTS.pull / 100 * run)); z1 = z; cx1 = cx + dir * DEFAULTS.drift * run / z; }
  else if (move === 'follow') { cx1 = cx + dir * DEFAULTS.follow * run / z; }
  else if (move === 'drift') { cx1 = cx + dir * DEFAULTS.drift * 0.6 * run / z; cy1 = cy + DEFAULTS.drift * 0.3 * run / z; }
  return { size, move, cx, cy, z: z0, cx1, cy1, z1, hold };
}

/** keep the view inside the drawn world (0..1920 × 0..1080) */
export function clampView(/** @type {number} */ cx, /** @type {number} */ cy, /** @type {number} */ z) {
  const hw = 960 / z, hh = 540 / z;
  return [Math.max(hw, Math.min(1920 - hw, cx)), Math.max(hh, Math.min(1080 - hh, cy))];
}

/** camera at lt seconds into a shot of d seconds: constant speed, then held for the last `hold` share */
export function camAt(/** @type {any} */ cam, /** @type {number} */ lt, /** @type {number} */ d) {
  const run = d * (1 - (cam.hold ?? DEFAULTS.hold));
  const k = run <= 0 ? 1 : Math.max(0, Math.min(1, lt / run));
  const z = cam.z + (cam.z1 - cam.z) * k;
  const [cx, cy] = clampView(cam.cx + (cam.cx1 - cam.cx) * k, cam.cy + (cam.cy1 - cam.cy) * k, z);
  return { cx, cy, z };
}

/** suggest a run of shot sizes: ~47% medium, a change on most cuts, never more than 4 in a row (FR-012).
 * Medium alternates with the other sizes, which keep their measured proportions (wide 19, very wide 14, close 11,
 * inserts, extreme close 3). */
export function suggestSizes(/** @type {number} */ n, seed = 'sizes') {
  const other = [['wide', 0.36], ['huge', 0.26], ['cu', 0.21], ['insert', 0.11], ['ecu', 0.06]];
  const out = []; let run = 0;
  for (let i = 0; i < n; i++) {
    const prev = out[i - 1], stay = hash01(seed + 's' + i) < 0.12;
    let pick;
    if (prev === 'med') pick = stay && run < 3 ? 'med' : null;
    else pick = prev && stay && run < 3 ? prev : 'med';
    if (!pick) { const u = hash01(seed + i); let acc = 0; pick = 'wide'; for (const [s, p] of other) { acc += /** @type {number} */ (p); if (u < acc) { pick = /** @type {string} */ (s); break; } } }
    run = pick === prev ? run + 1 : 0;
    out.push(pick);
  }
  return out;
}
