// @ts-check
// Sketch Explainer kit — shared drawing helpers (specs/028 T004).
// Hardware rule of this studio: filled paths use only straight lines and Bézier curves. The machine's GPU Chrome
// does not fill SVG arc commands, breaks rounded `rx` corners, and shows seams on one thick stroked polyline
// around a filled shape: use circ(), rrect() and segOutline() instead (tests/filmcheck/test_sketch_gpu.py).

export const NS = 'http://www.w3.org/2000/svg';
export const INK = '#1a191a';
/** line weight in character units (head radius 165): 12.5 gives ≈ 0.5% of the frame width in a medium shot */
export const LW = 12.5;

/** @param {string} tag @param {Record<string, any>} attrs @param {Element} [parent] */
export const el = (tag, attrs, parent) => {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, String(attrs[k]));
  if (parent) parent.appendChild(e);
  return e;
};
export const lerp = (/** @type {number} */ a, /** @type {number} */ b, /** @type {number} */ k) => a + (b - a) * k;
export const clamp01 = (/** @type {number} */ x) => Math.max(0, Math.min(1, x));
export const ease = (/** @type {number} */ x) => (x < 0 ? 0 : x > 1 ? 1 : x * x * (3 - 2 * x));
export const r1 = (/** @type {number} */ v) => Math.round(v * 10) / 10;

/** circle as four cubics */
export const circ = (/** @type {number} */ cx, /** @type {number} */ cy, /** @type {number} */ r) => {
  const k = 0.5523 * r;
  return `M${r1(cx - r)} ${r1(cy)} C${r1(cx - r)} ${r1(cy - k)} ${r1(cx - k)} ${r1(cy - r)} ${r1(cx)} ${r1(cy - r)} C${r1(cx + k)} ${r1(cy - r)} ${r1(cx + r)} ${r1(cy - k)} ${r1(cx + r)} ${r1(cy)} C${r1(cx + r)} ${r1(cy + k)} ${r1(cx + k)} ${r1(cy + r)} ${r1(cx)} ${r1(cy + r)} C${r1(cx - k)} ${r1(cy + r)} ${r1(cx - r)} ${r1(cy + k)} ${r1(cx - r)} ${r1(cy)} Z`;
};
/** ellipse as four cubics */
export const oval = (/** @type {number} */ cx, /** @type {number} */ cy, /** @type {number} */ rx, /** @type {number} */ ry) => {
  const kx = 0.5523 * rx, ky = 0.5523 * ry;
  return `M${r1(cx - rx)} ${r1(cy)} C${r1(cx - rx)} ${r1(cy - ky)} ${r1(cx - kx)} ${r1(cy - ry)} ${r1(cx)} ${r1(cy - ry)} C${r1(cx + kx)} ${r1(cy - ry)} ${r1(cx + rx)} ${r1(cy - ky)} ${r1(cx + rx)} ${r1(cy)} C${r1(cx + rx)} ${r1(cy + ky)} ${r1(cx + kx)} ${r1(cy + ry)} ${r1(cx)} ${r1(cy + ry)} C${r1(cx - kx)} ${r1(cy + ry)} ${r1(cx - rx)} ${r1(cy + ky)} ${r1(cx - rx)} ${r1(cy)} Z`;
};
/** rounded rectangle with cubic corners (never `rx`) */
export const rrect = (/** @type {number} */ x, /** @type {number} */ y, /** @type {number} */ w, /** @type {number} */ h, r = 12) => {
  r = Math.min(r, w / 2, h / 2);
  const k = r * 0.45;
  return `M${x + r} ${y} L${x + w - r} ${y} C${x + w - k} ${y} ${x + w} ${y + k} ${x + w} ${y + r} L${x + w} ${y + h - r} C${x + w} ${y + h - k} ${x + w - k} ${y + h} ${x + w - r} ${y + h} L${x + r} ${y + h} C${x + k} ${y + h} ${x} ${y + h - k} ${x} ${y + h - r} L${x} ${y + r} C${x} ${y + k} ${x + k} ${y} ${x + r} ${y} Z`;
};
export const box = (/** @type {number} */ x, /** @type {number} */ y, /** @type {number} */ w, /** @type {number} */ h) => `M${x} ${y} L${x + w} ${y} L${x + w} ${y + h} L${x} ${y + h} Z`;
export const poly = (/** @type {number[][]} */ pts) => 'M' + pts.map(p => `${r1(p[0])} ${r1(p[1])}`).join(' L') + ' Z';
/** pie slice as a polygon (no arcs) */
export const slice = (/** @type {number} */ cx, /** @type {number} */ cy, /** @type {number} */ r, /** @type {number} */ a0, /** @type {number} */ a1) => {
  const pts = [[cx, cy]];
  for (let k = 0; k <= 40; k++) { const a = a0 + (a1 - a0) * k / 40; pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); }
  return poly(pts);
};
/** a closed outline through points, each edge bulging outward from the centre by amp (curls, tufts) */
export const bumpy = (/** @type {number[][]} */ pts, /** @type {number} */ amp, cx = 0, cy = 0) => {
  let d = `M${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length];
    const mx = (x0 + x1) / 2, my = (y0 + y1) / 2, dx = mx - cx, dy = my - cy, L = Math.hypot(dx, dy) || 1;
    d += ` Q${r1(mx + dx / L * amp)} ${r1(my + dy / L * amp)} ${x1} ${y1}`;
  }
  return d + ' Z';
};
/** points on an ellipse from angle a0 to a1 (degrees, 0 = right, -90 = top) */
export const arcPts = (/** @type {number} */ rx, /** @type {number} */ ry, /** @type {number} */ a0, /** @type {number} */ a1, /** @type {number} */ n, cx = 0, cy = 0) =>
  Array.from({ length: n + 1 }, (_, i) => { const a = (a0 + (a1 - a0) * i / n) * Math.PI / 180; return [r1(cx + rx * Math.cos(a)), r1(cy + ry * Math.sin(a))]; });
/** head outline: oval with a narrower jaw */
export const ovalHead = (/** @type {number} */ rx, /** @type {number} */ ry, jaw = 0.62) =>
  `M0 ${-ry} C${r1(rx * .56)} ${-ry} ${rx} ${r1(-ry * .64)} ${rx} ${r1(-ry * .12)} C${rx} ${r1(ry * .3)} ${r1(rx * .87)} ${r1(ry * .63)} ${r1(rx * jaw + 10)} ${r1(ry * .82)} C${r1(rx * .45)} ${r1(ry * .95)} ${r1(rx * .2)} ${ry} 0 ${ry} C${r1(-rx * .2)} ${ry} ${r1(-rx * .45)} ${r1(ry * .95)} ${r1(-rx * jaw - 10)} ${r1(ry * .82)} C${r1(-rx * .87)} ${r1(ry * .63)} ${-rx} ${r1(ry * .3)} ${-rx} ${r1(-ry * .12)} C${-rx} ${r1(-ry * .64)} ${r1(-rx * .56)} ${-ry} 0 ${-ry} Z`;
/** a thick outline drawn as separate segments with round caps (one thick stroked polyline seams on the GPU) */
export const segOutline = (/** @type {number[][]} */ pts, /** @type {number} */ w, col = INK, closed = true) => {
  let o = '';
  const n = closed ? pts.length : pts.length - 1;
  for (let i = 0; i < n; i++) {
    const a = pts[i], b = pts[(i + 1) % pts.length];
    o += `<path d="M${r1(a[0])} ${r1(a[1])} L${r1(b[0])} ${r1(b[1])}" fill="none" stroke="${col}" stroke-width="${w}" stroke-linecap="round"/>`;
  }
  return o;
};
/** a filled box with a segment outline */
export const segBox = (/** @type {number} */ x, /** @type {number} */ y, /** @type {number} */ w, /** @type {number} */ h, /** @type {string} */ fill, lw = LW * .6) =>
  `<path d="${box(x, y, w, h)}" fill="${fill}" stroke="none"/>` + segOutline([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], lw);

/** deterministic pseudo-random numbers from a string seed */
export function rng(/** @type {string} */ seed) {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) { h ^= seed.charCodeAt(i); h = Math.imul(h, 16777619); }
  return () => { h ^= h << 13; h ^= h >>> 17; h ^= h << 5; return ((h >>> 0) % 100000) / 100000; };
}
/** text element markup (handwritten face) */
export const T = (/** @type {number} */ x, /** @type {number} */ y, /** @type {number} */ s, /** @type {string} */ txt, o = /** @type {any} */ ({})) =>
  `<text x="${x}" y="${y}" font-family="Hand" font-size="${s}" text-anchor="${o.a || 'middle'}" fill="${o.f || INK}" stroke="none"${o.op != null ? ` opacity="${o.op}"` : ''}>${txt}</text>`;
/** colour helpers: mix toward grey to keep sets muted (style §3) */
export function hex(/** @type {string} */ c) { return [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16)); }
export function toHex(/** @type {number[]} */ v) { return '#' + v.map(x => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2, '0')).join(''); }
export function shade(/** @type {string} */ c, k = 0.8) { return toHex(hex(c).map(x => x * k)); }
export function mute(/** @type {string} */ c, k = 0.5) { const v = hex(c), g = (v[0] + v[1] + v[2]) / 3; return toHex(v.map(x => lerp(x, g, k))); }
