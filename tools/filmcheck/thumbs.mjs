// Thumbnails of a film for its publish pack (specs/011 R2, R3). Draws the film's own page at a time t, lays one
// line of big text over it, and measures that text: its height and its contrast against what is under it.
// Uses the library's page helper like texts.mjs does; nothing in the library is changed.
//   node tools/filmcheck/thumbs.mjs <film dir> <lib dir> <job.json> <out dir>
// job.json = {w, h, thumbs: [{t, text, position, color, plate, plate_opacity, font}]}
// Writes <out dir>/raw-<n>.png at the film's size and prints {"thumbs": [{t, text, font, font_loaded,
// text_height_ratio, contrast, bg_luma}]}.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [dir, lib, jobFile, out] = process.argv.slice(2);
const job = JSON.parse(fs.readFileSync(jobFile, 'utf8'));
const P = await import(pathToFileURL(path.join(lib, 'core/render/page.mjs')).href);
P.requireDemo(dir);
const { browser, page } = await P.openDemo(dir, { w: job.w, h: job.h });

// Runs in the page: pick the font and lay out the text (hidden), return its line boxes
const layout = async (th) => {
  const H = window.innerHeight, W = window.innerWidth;
  const clean = (f) => (f || '').split(',')[0].trim().replace(/^["']|["']$/g, '');
  let fam = clean(th.font);
  if (!fam && typeof window.TEXTS === 'function') {          // the font of the biggest text on screen
    const boxes = (window.TEXTS(th.t) || []).filter((b) => b && b.text)
      .sort((a, b) => (b.y1 - b.y0) - (a.y1 - a.y0));
    for (const b of boxes) {
      const el = document.elementFromPoint((b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2);
      if (el && !(el instanceof HTMLCanvasElement)) { fam = clean(getComputedStyle(el).fontFamily); break; }
    }
  }
  const faces = [...document.fonts];
  if (!fam) fam = clean((faces.find((f) => f.status === 'loaded') || faces[0] || {}).family);
  if (!fam) fam = clean(getComputedStyle(document.body).fontFamily);
  try { await document.fonts.load(`800 100px "${fam}"`, th.text); } catch { /* checked below */ }
  const loaded = faces.length === 0 || faces.some((f) => clean(f.family) === fam && f.status === 'loaded');

  const d = document.createElement('div');
  d.id = 'studio-thumb';
  const pos = th.position || 'bottom';
  d.style.cssText = 'position:fixed;left:5%;right:5%;z-index:2147483647;pointer-events:none;text-align:center;' +
    'visibility:hidden;line-height:1.15;' +
    (pos === 'top' ? 'top:6%;' : pos === 'center' ? 'top:50%;transform:translateY(-50%);' : 'bottom:6%;');
  const s = document.createElement('span');
  s.textContent = th.text;
  const a = th.plate ? Math.max(0, Math.min(1, th.plate_opacity ?? 0.6)) : 0;
  const hex = (th.plate || '#000000').replace('#', '');
  const rgb = [0, 2, 4].map((i) => parseInt(hex.length === 3 ? hex[i / 2] + hex[i / 2] : hex.slice(i, i + 2), 16));
  s.style.cssText = `font-family:"${fam}",sans-serif;font-weight:800;color:${th.color || '#ffffff'};` +
    `padding:.08em .3em;border-radius:.12em;-webkit-box-decoration-break:clone;box-decoration-break:clone;` +
    (a ? `background:rgba(${rgb.join(',')},${a});` : '');
  d.appendChild(s);
  document.body.appendChild(d);
  let size = Math.round(H * 0.13);                           // big, then smaller until it fits in 2 lines
  for (;;) {
    s.style.fontSize = size + 'px';
    const lines = s.getClientRects().length;
    if ((lines <= 2 && d.scrollWidth <= d.clientWidth + 1) || size <= H * 0.05) break;
    size = Math.round(size * 0.92);
  }
  const rects = [...s.getClientRects()].map((r) => ({ x: r.left, y: r.top, w: r.width, h: r.height }));
  return { fam, loaded, rects, size, W, H };
};

// Runs in the page: luminance percentiles of a PNG (given as a data URL)
const luma = async (url) => {
  const img = new Image();
  img.src = url;
  await img.decode();
  const c = document.createElement('canvas');
  c.width = img.width; c.height = img.height;
  const g = c.getContext('2d');
  g.drawImage(img, 0, 0);
  const px = g.getImageData(0, 0, c.width, c.height).data;
  const lin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  const L = [];
  for (let i = 0; i < px.length; i += 16) L.push(0.2126 * lin(px[i]) + 0.7152 * lin(px[i + 1]) + 0.0722 * lin(px[i + 2]));
  L.sort((x, y) => x - y);
  return [L[Math.floor(L.length * 0.1)], L[Math.floor(L.length * 0.9)]];
};

const relLum = (hex) => {
  const h = (hex || '#ffffff').replace('#', '');
  const v = h.length === 3 ? [...h].map((x) => parseInt(x + x, 16)) : [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  return 0.2126 * lin(v[0]) + 0.7152 * lin(v[1]) + 0.0722 * lin(v[2]);
};
const ratio = (a, b) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);

const res = [];
for (let n = 0; n < job.thumbs.length; n++) {
  const th = job.thumbs[n];
  await page.evaluate((t) => window.render(t), th.t);
  const L = await page.evaluate(layout, th);
  const box = L.rects.reduce((b, r) => ({ x0: Math.min(b.x0, r.x), y0: Math.min(b.y0, r.y), x1: Math.max(b.x1, r.x + r.w),
    y1: Math.max(b.y1, r.y + r.h) }), { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity });
  const clip = { x: Math.max(0, box.x0), y: Math.max(0, box.y0), width: Math.max(1, Math.min(L.W, box.x1) - Math.max(0, box.x0)),
    height: Math.max(1, Math.min(L.H, box.y1) - Math.max(0, box.y0)) };
  const under = await page.screenshot({ clip });            // the overlay is still hidden: this is the picture alone
  const bg = await page.evaluate(luma, 'data:image/png;base64,' + under.toString('base64'));
  await page.evaluate(() => { document.getElementById('studio-thumb').style.visibility = 'visible'; });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(out, `raw-${n + 1}.png`) });
  await page.evaluate(() => document.getElementById('studio-thumb').remove());
  const a = th.plate ? Math.max(0, Math.min(1, th.plate_opacity ?? 0.6)) : 0;
  const plate = th.plate ? relLum(th.plate) : 0;
  const text = relLum(th.color);
  const eff = bg.map((l) => a * plate + (1 - a) * l);      // what is behind the letters, at both ends of the range
  res.push({ t: th.t, text: th.text, font: L.fam, font_loaded: L.loaded, font_px: L.size,
    text_height_ratio: +(Math.min(...L.rects.map((r) => r.h)) / L.H).toFixed(4),
    contrast: +Math.min(...eff.map((l) => ratio(text, l))).toFixed(2), bg_luma: bg.map((x) => +x.toFixed(4)) });
}
await browser.close();
P.closeServer();
console.log(JSON.stringify({ thumbs: res }));
