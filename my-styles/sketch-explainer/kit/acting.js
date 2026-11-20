// @ts-check
// Acting schedule of the kit (specs/028 T018, research R6). Pure: no DOM. Evidence (EVIDENCE.md): something moves
// inside the frame 93% of a shot; the first event starts right after the cut; a new event about every 2.4 s, each
// about 1.25 s long, then held (pose-to-pose); 1 event in shots under 4 s, 2–3 in shots of 6 s and more; a person
// is never frozen for a whole shot. Hand-written events (scene.acts) go first; the schedule fills the gaps.

export const KINDS = ['gesture', 'expr', 'blink', 'build', 'pop', 'enter', 'type'];
export const EVENT_DUR = 1.25;
const FIRST = 0.15, GAP_MIN = 2.0, GAP_SPAN = 0.75;

function rng(/** @type {string} */ seed) {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) { h ^= seed.charCodeAt(i); h = Math.imul(h, 16777619); }
  return () => { h ^= h << 13; h ^= h >>> 17; h ^= h << 5; return ((h >>> 0) % 100000) / 100000; };
}

/**
 * @param {{id: string, dur: number, cast?: any[], board?: any, acts?: any[]}} scene
 * @returns {{t: number, kind: string, who: number|string, dur: number, manual?: boolean, p?: any}[]}
 */
export function schedule(scene) {
  const d = scene.dur || 3, cast = scene.cast || [], r = rng(String(scene.id) + ':act');
  const manual = (scene.acts || []).map(([t, kind, who, p]) => ({ t, kind, who, dur: EVENT_DUR, manual: true, p }));
  const movers = cast.map((c, i) => [c, i]).filter(([c]) => !c.view || c.view !== 'back').map(([, i]) => /** @type {number} */ (i));
  const auto = [];
  let t = FIRST, k = 0;
  while (t < d - 0.2) {
    if (!manual.some(e => Math.abs(e.t - t) < 0.9)) {
      if (movers.length) {
        const who = movers[k % movers.length], c = cast[who];
        const still = c.still || c.seat || c.pose === 'hold' || !!c.walk;
        const cycle = still ? ['expr', 'blink'] : ['gesture', 'expr', 'gesture', 'blink'];
        auto.push({ t: +t.toFixed(3), kind: cycle[Math.floor(k / movers.length) % cycle.length], who, dur: EVENT_DUR });
      } else if (scene.board) auto.push({ t: +t.toFixed(3), kind: 'build', who: 'board', dur: EVENT_DUR });
      else auto.push({ t: +t.toFixed(3), kind: 'pop', who: 'scene', dur: EVENT_DUR });
      k++;
    }
    t += GAP_MIN + r() * GAP_SPAN;
  }
  return [...manual, ...auto].sort((a, b) => a.t - b.t);
}

/** pose, expression of person i at time lt, from the schedule. base: {pose, expr}; gestures: list to cycle */
export function stateAt(/** @type {any[]} */ events, /** @type {number} */ i, /** @type {number} */ lt, /** @type {any} */ base, /** @type {string[]} */ gestures, /** @type {string[]} */ exprs) {
  let pose = base.pose || 'rest', from = pose, poseT = -1, expr = base.expr || 'neutral', blink = false, g = 0, e = 0;
  for (const ev of events) {
    if (ev.who !== i || ev.t > lt) continue;
    if (ev.kind === 'gesture') { from = pose; g++; pose = ev.p && ev.p.pose ? ev.p.pose : gestures[g % gestures.length]; poseT = ev.t; }
    else if (ev.kind === 'expr') { e++; expr = ev.p && ev.p.expr ? ev.p.expr : exprs[e % exprs.length]; }
    else if (ev.kind === 'blink' && lt - ev.t < 0.14) blink = true;
  }
  return { pose, poseFrom: from, poseK: poseT < 0 ? 1 : Math.min(1, (lt - poseT) / 0.3), expr, blink };
}
