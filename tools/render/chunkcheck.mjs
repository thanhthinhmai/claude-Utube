// @ts-check
// Tier 3: check each chunk as soon as it is recorded (specs/020 FR-016, research R8).
// checkChunk runs one ffmpeg pass (blackdetect + freezedetect on a 320 px copy); combine joins still stretches across
// chunk edges (when no shot cut sits on the edge) and returns the faults: black_frames (≥ 0.25 s, away from the film's
// first and last 0.5 s) and still (longer than the style allows, unless the shot is an exception for "still").
import { spawnSync } from 'node:child_process';

export const BLACK_MIN = 0.25;
const EDGE = 0.5;

/** Black and frozen stretches (seconds from the chunk start) from ffmpeg's log; an open freeze runs to the end. */
export function parseLog(/** @type {string} */ log, /** @type {number} */ dur) {
  const num = (/** @type {RegExp} */ re) => [...log.matchAll(re)].map(m => +m[1]);
  const bs = num(/black_start:\s*([\d.]+)/g), be = num(/black_end:\s*([\d.]+)/g);
  const fs_ = num(/freeze_start:\s*([\d.]+)/g), fe = num(/freeze_end:\s*([\d.]+)/g);
  const black = bs.map((s, i) => [s, be[i] ?? dur]);
  const stills = fs_.map((s, i) => [s, fe[i] ?? dur]);
  return { black, stills };
}

/** Run ffmpeg on one finished chunk. */
export function checkChunk(/** @type {string} */ file, /** @type {number} */ dur) {
  const r = spawnSync('ffmpeg', ['-nostats', '-hide_banner', '-i', file, '-vf',
    `scale=320:-2,blackdetect=d=${BLACK_MIN}:pix_th=0.06,freezedetect=n=0.003:d=0.5`, '-an', '-f', 'null', '-'], { encoding: 'utf8' });
  return parseLog(r.stderr || '', dur);
}

/** The shot that holds second t: SHOTS rows are [t0, t1, set, id]. */
export function shotAt(/** @type {any[]} */ shots, /** @type {number} */ t) {
  const s = (shots || []).find(x => t >= x[0] - 1e-6 && t < x[1] - 1e-6) || (shots || [])[shots.length - 1];
  return s ? String(s[3] || '') : '';
}

/**
 * Faults over the chunks checked so far.
 * @param {{c:number, t0:number, t1:number, res:{black:number[][], stills:number[][]}}[]} done
 * @param {{stillMax:number, shots:any[], exceptions:{shot:string, rule:string}[], dur:number, fps:number}} o
 */
export function combine(done, o) {
  const out = [];
  const exc = new Set((o.exceptions || []).filter(e => e.rule === 'still').map(e => e.shot));
  const cutAt = (/** @type {number} */ t) => (o.shots || []).some(s => Math.abs(s[0] - t) <= 1.5 / o.fps);
  const sorted = [...done].sort((a, b) => a.t0 - b.t0);
  for (const ch of sorted) for (const [s, e] of ch.res.black) {
    const a = ch.t0 + s, b = ch.t0 + e;
    if (b - a >= BLACK_MIN && a > EDGE && b < o.dur - EDGE)
      out.push({ chunk: ch.c, shot: shotAt(o.shots, a), at: +a.toFixed(2), rule: 'black_frames', measure: +(b - a).toFixed(2), limit: BLACK_MIN });
  }
  // still stretches in film time, joined across a chunk edge when the next chunk is checked, starts frozen and no cut is there
  const runs = [];
  for (let i = 0; i < sorted.length; i++) {
    const ch = sorted[i];
    for (const [s, e] of ch.res.stills) {
      const a = ch.t0 + s, b = ch.t0 + e, last = runs[runs.length - 1];
      if (last && Math.abs(last.b - a) <= 1.5 / o.fps && last.open && !cutAt(a)) { last.b = b; last.chunks.push(ch.c); }
      else runs.push({ a, b, chunks: [ch.c], open: false });
      runs[runs.length - 1].open = b >= ch.t1 - 1.5 / o.fps;
    }
    const nxt = sorted[i + 1];
    if (!nxt || Math.abs(nxt.t0 - ch.t1) > 1e-6) for (const r of runs) r.open = false;   // a gap: nothing joins across it
  }
  for (const r of runs) {
    const shot = shotAt(o.shots, r.a);
    if (r.b - r.a > o.stillMax + 1e-6 && !exc.has(shot))
      out.push({ chunk: r.chunks[0], shot, at: +r.a.toFixed(2), rule: 'still', measure: +(r.b - r.a).toFixed(2), limit: o.stillMax });
  }
  return out;
}
