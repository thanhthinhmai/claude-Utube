// Graphics of the Dusk Hypothetical kit (specs/022 R7), drawn on the 2D canvas over the frame, inside the picture
// area (between the 6.4 % bars). Titles: caps, wide tracking, a high-contrast serif in cream or pale gold with a soft
// glow; numbers in pills; side-character lines in white bubbles (STYLE.md §4, §8). Every draw returns the text boxes
// it drew, for window.TEXTS.
export const SERIF = "'IM Fell English', Georgia, serif";
export const SANS = "'Fredoka', 'Lilita One', sans-serif";
export const CREAM = '#f3e3b0', GOLD = '#e8c45a', INKC = '#1a1226', PANEL = 'rgba(30,20,48,0.72)';
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const easeOut = (t) => 1 - Math.pow(1 - clamp(t), 3);
export const POP = 0.12;                                   // graphics pop in within 0.07–0.15 s

export function area(W, H) { const top = Math.round(H * 0.064); return { x0: 0, y0: top, x1: W, y1: H - top, W, H, u: H / 1080 }; }

// rounded rectangle from lines and arcs: Chrome on WSL2's GPU draws roundRect/arcTo fills as broken triangle fans
function rr(c, x, y, w, h, r) {
  r = Math.max(0, Math.min(r, w / 2, h / 2)); c.beginPath(); c.moveTo(x + r, y);
  c.lineTo(x + w - r, y); c.arc(x + w - r, y + r, r, -Math.PI / 2, 0);
  c.lineTo(x + w, y + h - r); c.arc(x + w - r, y + h - r, r, 0, Math.PI / 2);
  c.lineTo(x + r, y + h); c.arc(x + r, y + h - r, r, Math.PI / 2, Math.PI);
  c.lineTo(x, y + r); c.arc(x + r, y + r, r, Math.PI, Math.PI * 1.5); c.closePath();
}
function spaced(c, text, x, y, track, align = 'center') {   // wide tracking: draw letter by letter
  const chars = [...text], widths = chars.map((ch) => c.measureText(ch).width);
  const total = widths.reduce((a, b) => a + b, 0) + track * (chars.length - 1);
  let cx = align === 'center' ? x - total / 2 : align === 'right' ? x - total : x;
  const ta = c.textAlign; c.textAlign = 'left';
  chars.forEach((ch, i) => { c.fillText(ch, cx, y); cx += widths[i] + track; });
  c.textAlign = ta; return total;
}
function title(c, text, x, y, size, color, a, boxes, id, track = 0.18) {
  c.font = `${Math.round(size)}px ${SERIF}`; c.textBaseline = 'middle';
  c.shadowColor = 'rgba(255,220,160,0.55)'; c.shadowBlur = size * 0.35; c.fillStyle = color;
  const w = spaced(c, text, x, y, size * track); c.shadowBlur = 0;
  boxes.push({ id, text, x0: x - w / 2, y0: y - size * 0.6, x1: x + w / 2, y1: y + size * 0.6 });
  return w;
}
// the scene behind a full graphic: blurred and darker. Done on the scene's own canvas (a.under), never by copying it
// into the graphics canvas: that copy turns the graphics canvas back into the broken GPU path (see stage.js)
function dim(c, a, amount = 0.45, blur = true) {
  const u = a.under || c, W = u.canvas.width;
  if (blur && amount > 0) { u.save(); u.filter = `blur(${Math.round(10 * a.u)}px)`; u.drawImage(u.canvas, 0, 0); u.restore(); }
  u.fillStyle = `rgba(28,18,48,${amount})`; u.fillRect(0, a.y0, W, a.y1 - a.y0);
}
const pos = (g, a, dx = 0.5, dy = 0.2) => [a.x0 + (g.x ?? dx) * (a.x1 - a.x0), a.y0 + (g.y ?? dy) * (a.y1 - a.y0)];

// draw one graphic at local time lt (seconds since it appeared); returns text boxes
export function drawGfx(c, g, lt, a, extra = {}) {
  const boxes = [], id = g.id || g.type;
  const k = clamp(lt / POP); if (k <= 0) return boxes;
  c.save(); c.globalAlpha = k;
  const u = a.u;
  switch (g.type) {
    case 'counter': {
      const v = (g.from ?? 0) + ((g.to ?? 0) - (g.from ?? 0)) * easeOut((lt - (g.delay ?? 0.1)) / (g.roll ?? 1.3));
      const text = `${g.prefix || ''}${fmt(v, g.to, g.decimals)}${g.suffix || ''}`;
      const [x, y] = pos(g, a, 0.5, 0.1);
      c.font = `${Math.round(54 * u)}px ${SANS}`; c.textBaseline = 'middle';
      const w = c.measureText(text).width + (g.icon ? 70 : 44) * u, h = 84 * u;
      rr(c, x - w / 2, y - h / 2, w, h, h / 2); c.fillStyle = PANEL; c.fill(); c.strokeStyle = 'rgba(243,227,176,0.7)'; c.lineWidth = 3 * u; c.stroke();
      if (g.icon) { c.fillStyle = g.icon === 'heart' ? '#e85a6a' : g.icon === 'coin' ? GOLD : '#f0d060'; c.beginPath(); c.arc(x - w / 2 + 38 * u, y, 16 * u, 0, 7); c.fill(); }
      c.fillStyle = CREAM; c.textAlign = 'center'; c.fillText(text, x + (g.icon ? 14 * u : 0), y + 2 * u);
      boxes.push({ id, text, x0: x - w / 2, y0: y - h / 2, x1: x + w / 2, y1: y + h / 2 });
      break;
    }
    case 'menu': {                                          // game-like corner menu with locks
      const items = g.items || [], x = a.x1 - 470 * u, y = a.y0 + 40 * u, rowH = 58 * u, w = 430 * u, h = 80 * u + items.length * rowH;
      rr(c, x, y, w, h, 18 * u); c.fillStyle = PANEL; c.fill(); c.strokeStyle = 'rgba(243,227,176,0.55)'; c.lineWidth = 2 * u; c.stroke();
      c.font = `${Math.round(34 * u)}px ${SERIF}`; c.fillStyle = GOLD; c.textBaseline = 'middle';
      if (g.title) { spaced(c, g.title, x + w / 2, y + 40 * u, 5 * u); boxes.push({ id: id + '.title', text: g.title, x0: x, y0: y, x1: x + w, y1: y + 70 * u }); }
      items.forEach((it, i) => {
        const yy = y + 90 * u + i * rowH, locked = (g.locked || []).includes(i), on = g.active === i;
        if (on) { rr(c, x + 14 * u, yy - rowH / 2 + 4 * u, w - 28 * u, rowH - 8 * u, 10 * u); c.fillStyle = 'rgba(232,196,90,0.25)'; c.fill(); }
        c.globalAlpha = k * (locked ? 0.55 : 1); c.font = `${Math.round(28 * u)}px ${SANS}`; c.fillStyle = CREAM; c.textAlign = 'left';
        c.fillText(it, x + 36 * u, yy); boxes.push({ id: `${id}.${i}`, text: it, x0: x + 30 * u, y0: yy - 18 * u, x1: x + w - 60 * u, y1: yy + 18 * u });
        if (locked) lock(c, x + w - 46 * u, yy, 14 * u); c.globalAlpha = k;
      });
      break;
    }
    case 'diagram': {
      dim(c, a, 0.4 * k, !extra.noBlur);
      if (g.title) title(c, g.title, a.W / 2, a.y0 + 110 * u, 58 * u, CREAM, a, boxes, id + '.title');
      const cx = a.W / 2, cy = a.y0 + (a.y1 - a.y0) * 0.56;
      if ((g.kind || 'bars') === 'bars') {
        const vals = g.values || [1, 2], max = Math.max(...vals, 1e-9), labels = g.labels || [];
        vals.forEach((v, i) => {
          const bw = 170 * u, bx = cx + (i - (vals.length - 1) / 2) * 300 * u - bw / 2, full = 380 * u, bh = full * (v / max) * easeOut((lt - 0.15) / 1.3);
          rr(c, bx, cy + full / 2 - bh, bw, Math.max(bh, 1), 12 * u); c.fillStyle = i === (g.highlight ?? vals.length - 1) ? GOLD : '#9a7ad0'; c.fill();
          c.font = `${Math.round(30 * u)}px ${SANS}`; c.fillStyle = CREAM; c.textAlign = 'center';
          if (labels[i]) { c.fillText(labels[i], bx + bw / 2, cy + full / 2 + 40 * u); boxes.push({ id: `${id}.l${i}`, text: labels[i], x0: bx - 30 * u, y0: cy + full / 2 + 22 * u, x1: bx + bw + 30 * u, y1: cy + full / 2 + 58 * u }); }
        });
      } else if (g.kind === 'gauge') {
        const R = 200 * u, v = clamp(g.value ?? 0.5) * easeOut((lt - 0.15) / 1.3);
        c.lineWidth = 34 * u; c.lineCap = 'round';
        c.strokeStyle = 'rgba(243,227,176,0.25)'; c.beginPath(); c.arc(cx, cy + 80 * u, R, Math.PI, 2 * Math.PI); c.stroke();
        c.strokeStyle = v > 0.75 ? '#e85a6a' : GOLD; c.beginPath(); c.arc(cx, cy + 80 * u, R, Math.PI, Math.PI * (1 + v)); c.stroke();
        c.lineWidth = 8 * u; c.strokeStyle = CREAM; c.beginPath(); c.moveTo(cx, cy + 80 * u); c.lineTo(cx + Math.cos(Math.PI * (1 + v)) * R * 0.8, cy + 80 * u + Math.sin(Math.PI * (1 + v)) * R * 0.8); c.stroke();
      } else if (g.kind === 'figures') {                      // flat people, some highlighted: "one in N"
        const n = g.n || 10, hi = g.highlight ?? 1, cols = Math.min(n, 10), s = 64 * u;
        for (let i = 0; i < n; i++) {
          const x = cx + ((i % cols) - (cols - 1) / 2) * s * 1.3, y = cy + Math.floor(i / cols) * s * 1.9;
          c.globalAlpha = k * clamp((lt - 0.1 - i * 0.03) / 0.12); flatPerson(c, x, y, s, i < hi ? GOLD : '#9a7ad0');
        }
      }
      break;
    }
    case 'bubble': {                                        // white bubble beside the speaker's head
      const [x, y] = extra.anchor || pos(g, a, 0.62, 0.22);
      c.font = `${Math.round(32 * u)}px ${SANS}`; c.textBaseline = 'middle';
      const text = g.text || '', w = c.measureText(text).width + 48 * u, h = 66 * u, bx = x - (g.left ? w : 0), by = y - h;
      rr(c, bx, by, w, h, 22 * u); c.fillStyle = '#ffffff'; c.fill();
      c.beginPath(); c.moveTo(x + (g.left ? -30 : 30) * u, by + h - 2); c.lineTo(x, by + h + 22 * u); c.lineTo(x + (g.left ? -58 : 58) * u, by + h - 2); c.fill();
      c.fillStyle = INKC; c.textAlign = 'left'; c.fillText(text, bx + 24 * u, by + h / 2 + 2 * u);
      boxes.push({ id, text, x0: bx, y0: by, x1: bx + w, y1: by + h });
      break;
    }
    case 'stat': {                                          // number card on violet
      c.fillStyle = '#3b2a62'; c.fillRect(0, a.y0, a.W, a.y1 - a.y0);
      const g2 = c.createRadialGradient(a.W / 2, a.H / 2, 0, a.W / 2, a.H / 2, a.W * 0.6); g2.addColorStop(0, 'rgba(160,120,220,0.35)'); g2.addColorStop(1, 'rgba(0,0,0,0)');
      c.fillStyle = g2; c.fillRect(0, a.y0, a.W, a.y1 - a.y0);
      title(c, g.text || '', a.W / 2, a.H * 0.45, 120 * u, GOLD, a, boxes, id);
      if (g.sub) title(c, g.sub, a.W / 2, a.H * 0.6, 46 * u, CREAM, a, boxes, id + '.sub', 0.14);
      break;
    }
    case 'title': {                                         // two lines, the second larger and gold
      const [x, y] = pos(g, a, 0.5, 0.2);
      if (g.text) title(c, g.text, x, y, 50 * u, CREAM, a, boxes, id);
      if (g.sub) title(c, g.sub, x, y + 90 * u, 92 * u, GOLD, a, boxes, id + '.sub', 0.12);
      break;
    }
    case 'chapter': {
      dim(c, a, 0.35 * k, !extra.noBlur);
      const w = title(c, g.text || '', a.W / 2, a.H / 2, 78 * u, CREAM, a, boxes, id);
      c.strokeStyle = 'rgba(232,196,90,0.8)'; c.lineWidth = 2 * u;
      for (const s of [-1, 1]) { c.beginPath(); c.moveTo(a.W / 2 + s * (w / 2 + 30 * u), a.H / 2); c.lineTo(a.W / 2 + s * (w / 2 + 180 * u), a.H / 2); c.stroke(); }
      break;
    }
    case 'end-choice': {                                    // closing yes/no card with the episode's cast in a row
      dim(c, a, 0.5 * k, !extra.noBlur);
      if (g.text) title(c, g.text, a.W / 2, a.y0 + 150 * u, 62 * u, CREAM, a, boxes, id);
      (g.options || ['YES', 'NO']).forEach((o, i) => {
        const bw = 360 * u, bh = 150 * u, bx = a.W / 2 + (i ? 40 : -40 - 360) * u, by = a.H * 0.42;
        rr(c, bx, by, bw, bh, 24 * u); c.fillStyle = PANEL; c.fill(); c.strokeStyle = i ? '#e85a6a' : '#7ad08a'; c.lineWidth = 4 * u; c.stroke();
        c.font = `${Math.round(56 * u)}px ${SERIF}`; c.fillStyle = CREAM; c.textAlign = 'center'; c.textBaseline = 'middle'; spaced(c, o, bx + bw / 2, by + bh / 2, 8 * u);
        boxes.push({ id: `${id}.o${i}`, text: o, x0: bx, y0: by, x1: bx + bw, y1: by + bh });
      });
      const cast = g.cast || ['#d9b23a', '#c0423e', '#3f9a9a', '#7a5cc0', '#4f8f4a'];
      cast.forEach((col, i) => flatPerson(c, a.W / 2 + (i - (cast.length - 1) / 2) * 120 * u, a.y1 - 150 * u, 70 * u, col));
      break;
    }
    default: break;
  }
  c.restore();
  return boxes;
}

function fmt(v, to, decimals) {
  const d = decimals ?? (Number.isInteger(to) ? 0 : 1);
  return Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}
function lock(c, x, y, s) {
  c.fillStyle = GOLD; c.fillRect(x - s, y - s * 0.2, s * 2, s * 1.5);
  c.strokeStyle = GOLD; c.lineWidth = s * 0.35; c.beginPath(); c.arc(x, y - s * 0.2, s * 0.7, Math.PI, 2 * Math.PI); c.stroke();
}
function flatPerson(c, x, y, s, col) {
  c.fillStyle = '#e2d6ee'; c.beginPath(); c.arc(x, y - s * 0.55, s * 0.36, 0, 7); c.fill();
  c.fillStyle = col; rr(c, x - s * 0.34, y - s * 0.16, s * 0.68, s * 0.7, s * 0.25); c.fill();
}

// subtitles: pale cream sans, 34–44 px at 1080p, soft shadow, inside the picture area, fixed position
export function drawCue(c, text, a) {
  const u = a.u, size = Math.round(40 * u), y = a.y1 - 70 * u;
  c.save(); c.font = `${size}px ${SANS}`; c.textAlign = 'center'; c.textBaseline = 'middle';
  c.shadowColor = 'rgba(0,0,0,0.7)'; c.shadowBlur = 8 * u; c.shadowOffsetY = 2 * u; c.fillStyle = '#f6ecd0';
  const lines = wrap(c, text, a.W * 0.7), out = [];
  lines.forEach((ln, i) => {
    const yy = y - (lines.length - 1 - i) * size * 1.2; c.fillText(ln, a.W / 2, yy);
    const w = c.measureText(ln).width; out.push({ id: 'cue', text: ln, x0: a.W / 2 - w / 2, y0: yy - size * 0.6, x1: a.W / 2 + w / 2, y1: yy + size * 0.6 });
  });
  c.restore(); return out;
}
function wrap(c, text, max) {
  const words = String(text).split(/\s+/), lines = []; let cur = '';
  for (const w of words) { const t = cur ? cur + ' ' + w : w; if (c.measureText(t).width > max && cur) { lines.push(cur); cur = w; } else cur = t; }
  if (cur) lines.push(cur); return lines.slice(0, 2);
}
