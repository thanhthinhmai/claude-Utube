// Shared After Effects kit of the studio (specs/031). Moved from films/ae-crayon-test/ae/persp.jsx on 2026-11-23.
// Paths come from CU.WORK (the folder the entry script runs in); film data lives in CU.WORK/data/.
// persp.jsx: depth kit. Flat artwork pinned into perspective (Corner Pin), 3/4 boxes, monitors and keyboards,
// wall light, vignette, contact shadows and parallax. Used to stop props from facing the camera flat.

// Draw flat content in its own w x h comp (drawFn(comp)), then pin its corners onto a quad [UL, UR, LL, LR] in comp.
CU.pinned = function (comp, name, w, h, dur, drawFn, quad) {
  var pc = CU.comp(name, dur, w, h);
  drawFn(pc);
  var L = comp.layers.add(pc); L.name = name;
  CU.anc(L).setValue([0, 0]); CU.pos(L).setValue([0, 0]);
  var cp = CU.fx(L, "ADBE Corner Pin");
  CU.fxset(cp, ["ADBE Corner Pin-0001", "Upper Left"], quad[0]);
  CU.fxset(cp, ["ADBE Corner Pin-0002", "Upper Right"], quad[1]);
  CU.fxset(cp, ["ADBE Corner Pin-0003", "Lower Left"], quad[2]);
  CU.fxset(cp, ["ADBE Corner Pin-0004", "Lower Right"], quad[3]);
  return L;
};

CU.lerp = function (a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; };

// A box seen from above-front: top face given by its 4 corners [backL, backR, frontR, frontL]; height h straight down.
// The side face on the side away from the centre line is drawn when visible.
CU.box3q = function (R, top, h, col, o) {
  o = o || {};
  var c = CU.hex(col), topC = o.topCol ? CU.hex(o.topCol) : CU.shade(c, 1.1), frontC = c, sideC = CU.shade(c, 0.78);
  var bl = top[0], br = top[1], fr = top[2], fl = top[3];
  if (o.side === "right" || (o.side !== "left" && o.side !== "none" && br[0] > fr[0])) { CU.poly(R, [fr, br, [br[0], br[1] + h], [fr[0], fr[1] + h]], { fill: sideC, stroke: true, sw: o.sw || 4 }); }
  if (o.side === "left" || (o.side !== "right" && o.side !== "none" && bl[0] < fl[0])) { CU.poly(R, [bl, fl, [fl[0], fl[1] + h], [bl[0], bl[1] + h]], { fill: sideC, stroke: true, sw: o.sw || 4 }); }
  CU.poly(R, [fl, fr, [fr[0], fr[1] + h], [fl[0], fl[1] + h]], { fill: frontC, stroke: true, sw: o.sw || 4 });
  CU.poly(R, top, { fill: topC, stroke: true, sw: o.sw || 4 });
};

// Monitor turned by yaw (-1 .. +1). yaw > 0: the screen faces right (toward someone on the right), so its left edge is
// nearer (taller) and the casing's side shows beyond that near edge. Returns the screen quad [UL, UR, LL, LR].
CU.monitor3q = function (R, cx, cy, w, h, yaw, o) {
  o = o || {};
  var k = 0.18 * Math.abs(yaw), near = h / 2, far = h / 2 * (1 - k * 1.4), hw = w / 2 * (1 - 0.35 * Math.abs(yaw));
  var lH = yaw > 0 ? near : far, rH = yaw > 0 ? far : near;
  var UL = [cx - hw, cy - lH], LL = [cx - hw, cy + lH], UR = [cx + hw, cy - rH], LR = [cx + hw, cy + rH];
  var b = 0.035 * w, t = (o.depth || 0.1) * w * Math.abs(yaw) + 6, dir = yaw >= 0 ? -1 : 1;
  var bUL = [UL[0] - b, UL[1] - b], bUR = [UR[0] + b, UR[1] - b], bLR = [LR[0] + b, LR[1] + b], bLL = [LL[0] - b, LL[1] + b];
  var nUp = yaw >= 0 ? bUL : bUR, nDn = yaw >= 0 ? bLL : bLR, sh = 0.05 * h * Math.abs(yaw);
  var neckX = cx + dir * t * 0.6, baseY = cy + h / 2 + h * 0.32;
  CU.poly(R, [[neckX - 0.04 * w, cy + h * 0.3], [neckX + 0.04 * w, cy + h * 0.3], [neckX + 0.03 * w, baseY], [neckX - 0.03 * w, baseY]], { fill: "#2a2e35", stroke: true, sw: 3 });
  CU.ell(R, neckX, baseY + 4, 0.38 * w, 0.06 * w, { fill: "#2a2e35", stroke: true, sw: 3 });
  if (Math.abs(yaw) > 0.05) { CU.poly(R, [nUp, [nUp[0] + dir * t, nUp[1] + sh], [nDn[0] + dir * t, nDn[1] - sh], nDn], { fill: "#14161a", stroke: true, sw: 3.5 }); }
  CU.poly(R, [bUL, bUR, bLR, bLL], { fill: o.bezel || "#2a2e35", stroke: true, sw: 4 });
  CU.poly(R, [UL, UR, LR, LL], { fill: o.screen || "#1d4f78", stroke: true, sw: 2.5 });
  return [UL, UR, LL, LR];
};

// Keyboard lying on a desk: a parallelogram (front edge at y, depth going back and toward vx) with key rows.
CU.keyboard3q = function (R, x, y, w, depth, skew, col) {
  var fl = [x, y], fr = [x + w, y], br = [x + w + skew, y - depth], bl = [x + skew, y - depth];
  CU.poly(R, [fl, fr, [fr[0], fr[1] + 10], [fl[0], fl[1] + 10]], { fill: "#15171b", stroke: true, sw: 3 });
  CU.poly(R, [bl, br, fr, fl], { fill: col || "#2a2e35", stroke: true, sw: 3.5 });
  var r, d = "";
  for (r = 1; r < 5; r++) { var a = CU.lerp(bl, fl, r / 5), b = CU.lerp(br, fr, r / 5); d += "M " + (a[0] + 8) + " " + a[1] + " L " + (b[0] - 8) + " " + b[1] + " "; }
  for (r = 1; r < 12; r++) { var p = CU.lerp(bl, br, r / 12), q = CU.lerp(fl, fr, r / 12); d += "M " + p[0] + " " + (p[1] + 4) + " L " + q[0] + " " + (q[1] - 4) + " "; }
  CU.path(R, d, { stroke: "#4a4f58", sw: 2 });
};

// Soft light on a wall and a vignette: depth by value (near bright, far and edges darker).
CU.wallLight = function (comp, name, cx, cy, rx, ry, col, op) {
  var L = CU.layer(comp, name); CU.ell(CU.root(L), cx, cy, rx * 2, ry * 2, { fill: col || "#ffffff" });
  CU.blur(L, Math.max(rx, ry) * 0.45); L.blendingMode = BlendingMode.SOFT_LIGHT; CU.opa(L).setValue(op || 45);
  return L;
};
CU.vignette = function (comp, strength) {
  var L = CU.solid(comp, "vignette", "#000000"); CU.ramp(L, [comp.width / 2, comp.height / 2], "#ffffff", [comp.width / 2, -comp.height * 0.15], "#000000", true);
  L.blendingMode = BlendingMode.MULTIPLY; CU.opa(L).setValue(strength || 35);
  return L;
};
CU.shadowAt = function (R, x, y, w, op) { CU.ell(R, x, y, w, w * 0.16, { fill: "#000000", fo: op || 22 }); };

// Parallax: after CU.camera, layers further from the camera plane move less (d < 1) or more (d > 1) than the CAM.
CU.parallax = function (comp, names, d) {
  var i;
  for (i = 0; i < names.length; i++) {
    var L = null, k; for (k = 1; k <= comp.numLayers; k++) { if (comp.layer(k).name === names[i]) { L = comp.layer(k); } }
    if (!L) { continue; }
    CU.pos(L).expression = "var c = thisComp.layer('CAM').transform.position; var c0 = thisComp.layer('CAM').transform.position.valueAtTime(0); value + (c - c0) * " + (d - 1) + " / (thisComp.layer('CAM').transform.scale[0] / 100);";
  }
};

// Typing: small alternating arm motion while a time window is active (arms layers of a person comp).
CU.typing = function (personComp, t0, t1) {
  var k;
  for (k = 1; k <= personComp.numLayers; k++) {
    var L = personComp.layer(k);
    if (L.name === "arm l" || L.name === "arm r") {
      var ph = L.name === "arm l" ? 0 : 1.7;
      CU.pos(L).expression = "(time > " + t0 + " && time < " + t1 + ") ? value + [0, 5 * Math.sin(time * 26 + " + ph + ")] : value;";
    }
  }
};

// A stack of paper lying on a desk: box3q with sheet lines on the front face and scribbles on top.
CU.stack3q = function (R, top, h, col, topCol) {
  CU.box3q(R, top, h, col, { topCol: topCol || "#d9d4c6" });
  var fl = top[3], fr = top[2], k, d = "";
  for (k = 1; k * 9 < h; k++) { d += "M " + (fl[0] + 4) + " " + (fl[1] + k * 9) + " L " + (fr[0] - 4) + " " + (fr[1] + k * 9) + " "; }
  if (d) { CU.path(R, d, { stroke: CU.shade(CU.hex(col), 0.7), sw: 2 }); }
  var s = "";
  for (k = 1; k < 5; k++) { var a = CU.lerp(CU.lerp(top[0], top[3], k / 5.5), CU.lerp(top[1], top[2], k / 5.5), 0.12), b = CU.lerp(CU.lerp(top[0], top[3], k / 5.5), CU.lerp(top[1], top[2], k / 5.5), 0.8 - (k % 2) * 0.2);
    s += "M " + a[0] + " " + a[1] + " L " + b[0] + " " + b[1] + " "; }
  CU.path(R, s, { stroke: "#77736a", sw: 3 });
};

// Sofa turned 3/4: seat top [backL, backR, frontR, frontL]; the back rest stands on the back edge, the near arm (o.near
// "right" | "left") goes to its own layer so it can sit in front of the legs. Returns {layer, arm, box}.
CU.sofa3q = function (comp, name, o) {
  var L = CU.layer(comp, name), R = CU.root(L), col = CU.hex(o.color), s = o.seat, bl = s[0], br = s[1], fr = s[2], fl = s[3];
  var bh = o.backH || 240, fh = o.frontH || 140, aw = o.armW || 110, ah = o.armH || 110, up = function (p, d) { return [p[0], p[1] - d]; };
  var dark = CU.shade(col, 0.72), side = CU.shade(col, 0.85), top = CU.shade(col, 1.12);
  CU.ell(R, (fl[0] + fr[0]) / 2, Math.max(fl[1], fr[1]) + fh + 8, Math.abs(fr[0] - fl[0]) * 1.05, 40, { fill: "#000000", fo: 22 });
  CU.poly(R, [up(bl, bh), up(br, bh), br, bl], { fill: col, stroke: true });                                     // back rest
  CU.poly(R, [up(bl, bh), up(br, bh), up(CU.lerp(br, fr, 0.22), bh - 10), up(CU.lerp(bl, fl, 0.22), bh - 10)], { fill: top, stroke: true, sw: 4 });
  CU.poly(R, [CU.lerp(bl, fl, 0.16), CU.lerp(br, fr, 0.16), fr, fl], { fill: top, stroke: true });               // seat cushion
  var m0 = CU.lerp(CU.lerp(bl, fl, 0.16), CU.lerp(br, fr, 0.16), 0.5), m1 = CU.lerp(fl, fr, 0.5);
  CU.path(R, "M " + m0[0] + " " + m0[1] + " L " + m1[0] + " " + m1[1], { stroke: true, sw: 3 });
  CU.poly(R, [fl, fr, [fr[0], fr[1] + fh], [fl[0], fl[1] + fh]], { fill: side, stroke: true });                 // seat front
  var A = CU.layer(comp, name + " arm"), ra = CU.root(A), e0 = o.near === "left" ? bl : br, e1 = o.near === "left" ? fl : fr, sg = o.near === "left" ? -1 : 1;
  e0 = CU.lerp(e1, e0, 0.3);
  var cx1 = e1[0] + sg * aw * 0.25, cx0 = e0[0] + sg * aw * 0.25, w2 = aw / 2;
  CU.poly(ra, [[cx0 - w2 * 0.8, e0[1] - ah], [cx0 + w2 * 0.8, e0[1] - ah], [cx1 + w2, e1[1] - ah + 20], [cx1 - w2, e1[1] - ah + 20]], { fill: top, stroke: true, sw: 4 });
  CU.poly(ra, [[cx0 - sg * w2 * 0.8, e0[1] - ah + 20], [cx1 - sg * w2, e1[1] - ah + 30], [cx1 - sg * w2, e1[1] + fh], [cx0 - sg * w2 * 0.8, e0[1] + fh * 0.6]], { fill: dark, stroke: true, sw: 4 });
  CU.rect(ra, cx1 - w2, e1[1] - ah, aw, ah + fh, 34, { fill: col, stroke: true });
  CU.path(ra, "M " + (cx1 - w2 + 18) + " " + (e1[1] - ah + 40) + " Q " + cx1 + " " + (e1[1] - ah + 18) + " " + (cx1 + w2 - 18) + " " + (e1[1] - ah + 40), { stroke: CU.shade(col, 0.6), sw: 3 });
  return { layer: L, arm: A, box: [Math.min(bl[0], fl[0]) - aw, Math.min(bl[1], br[1]) - bh, Math.max(br[0], fr[0]) + aw, Math.max(fl[1], fr[1]) + fh] };
};

// Flat screen contents for CU.pinned.
CU.codeScreen = function (w, h, seed, title) {
  return function (pc) {
    var R = CU.root(CU.layer(pc, "screen")), r = CU.rand(seed || 3), k;
    CU.rect(R, 0, 0, w, h, 0, { fill: "#1d4f78" });
    var cols = ["#8ff4ff", "#57c6e0", "#e6a23c", "#5ec06a", "#e0574a"], n = 9;
    for (k = 0; k < n; k++) { CU.path(R, CU.squiggle(20 + (k % 3) * 14, 26 + k * (h - 40) / n, w * (0.4 + r() * 0.45), 4, seed * 10 + k), { stroke: cols[k % cols.length], sw: 4 }); }
    if (title) { CU.text(pc, title, { size: h * 0.1, color: "#8ff4ff", x: w / 2, y: h * 0.14, center: true, name: "title" }); }
  };
};
CU.waveScreen = function (w, h) {
  return function (pc) {
    var R = CU.root(CU.layer(pc, "screen")), k, wv = "M 20 " + h * 0.6;
    CU.rect(R, 0, 0, w, h, 0, { fill: "#1d4f78" });
    for (k = 0; k < 44; k++) { wv += " L " + (20 + k * (w - 40) / 43) + " " + (h * 0.6 + Math.sin(k * 1.3) * (8 + (k % 7) * 4)); }
    CU.path(R, wv, { stroke: "#8ff4ff", sw: 4 }); CU.path(R, CU.squiggle(30, h * 0.2, w - 80, 5, 5), { stroke: "#8ff4ff", sw: 4 });
  };
};

// Wavy hand-drawn line from a to b (for scribbles on surfaces in perspective).
CU.wavy = function (a, b, amp, seed) {
  var r = CU.rand(seed || 3), n = Math.max(3, Math.round(Math.sqrt(Math.pow(b[0] - a[0], 2) + Math.pow(b[1] - a[1], 2)) / 16)), d = "M " + a[0] + " " + a[1], i;
  for (i = 1; i <= n; i++) { var p0 = CU.lerp(a, b, (i - 0.5) / n), p1 = CU.lerp(a, b, i / n); d += " Q " + p0[0] + " " + (p0[1] + (i % 2 ? amp : -amp) * (0.5 + r())) + " " + p1[0] + " " + p1[1]; }
  return d;
};
// A messy pile of paper: sheets stacked bottom to top, each a little shifted and turned, wavy front edges, scribbles on top.
// top = [backL, backR, frontR, frontL] of the pile's top face; h = pile height.
CU.paperPile = function (R, top, h, seed, o) {
  o = o || {};
  var r = CU.rand(seed || 5), n = o.n || Math.max(3, Math.round(h / 11)), th = h / n, col = CU.hex(o.col || "#bdb6a4"), k, j;
  var cx = (top[0][0] + top[1][0] + top[2][0] + top[3][0]) / 4, cy = (top[0][1] + top[1][1] + top[2][1] + top[3][1]) / 4, jit = o.jit === undefined ? 22 : o.jit;
  for (k = 0; k < n; k++) {
    var dy = h - (k + 1) * th, jx = (r() - 0.5) * jit, jy = (r() - 0.5) * jit * 0.25, an = (r() - 0.5) * (o.turn === undefined ? 0.06 : o.turn), ca = Math.cos(an), sa = Math.sin(an), q = [];
    for (j = 0; j < 4; j++) { var x = top[j][0] - cx, y = top[j][1] - cy; q.push([cx + x * ca - y * sa * 0.4 + jx, cy + x * sa * 0.4 + y * ca + dy + jy]); }
    var fl = q[3], fr = q[2], m = 6, edge = "M " + fl[0] + " " + fl[1] + " L " + fr[0] + " " + fr[1] + " L " + fr[0] + " " + (fr[1] + th), ii;
    for (ii = m - 1; ii >= 0; ii--) { var pe = CU.lerp(fl, fr, ii / m); edge += " Q " + (pe[0] + (fr[0] - fl[0]) / m * 0.5) + " " + (pe[1] + th + (ii % 2 ? 4 : -3)) + " " + pe[0] + " " + (pe[1] + th); }
    CU.path(R, edge + " Z", { fill: CU.shade(col, 0.72 + (k % 3) * 0.06), stroke: true, sw: 2.5 });
    CU.poly(R, q, { fill: CU.shade(col, k === n - 1 ? 1.08 : 0.95 + (k % 2) * 0.05), stroke: true, sw: 2.5 });
    if (k === n - 1) { // scribbled writing on the top sheet
      var s2 = "", rows = o.rows || 5;
      for (j = 1; j <= rows; j++) { var a = CU.lerp(CU.lerp(q[0], q[3], j / (rows + 1)), CU.lerp(q[1], q[2], j / (rows + 1)), 0.1), b = CU.lerp(CU.lerp(q[0], q[3], j / (rows + 1)), CU.lerp(q[1], q[2], j / (rows + 1)), 0.55 + r() * 0.35); s2 += CU.wavy(a, b, 4, seed * 7 + j) + " "; }
      CU.path(R, s2, { stroke: o.ink || "#4a473f", sw: 3 });
    }
  }
};
// Six interlocking rounded links in a hexagonal knot (outlined, woven), centred at cx, cy with size s.
CU.knotLogo = function (R, cx, cy, s, o) {
  o = o || {};
  var L = 1.0 * s, W = 0.3 * s, off = 0.25 * s, fill = o.fill || "#f2f2ee", sw = o.sw || Math.max(2.5, s * 0.045), k;
  function cap(k, cut) {
    var th = k * Math.PI / 3, px = cx + off * Math.cos(th + Math.PI / 2), py = cy + off * Math.sin(th + Math.PI / 2), r = W / 2, hl = L / 2 - r, pts = [], i, n = 14, out = [];
    for (i = 0; i <= n; i++) { var a = -Math.PI / 2 + Math.PI * i / n; pts.push([hl + r * Math.cos(a), r * Math.sin(a)]); }
    for (i = 0; i <= n; i++) { var a2 = Math.PI / 2 + Math.PI * i / n; pts.push([-hl + r * Math.cos(a2), r * Math.sin(a2)]); }
    for (i = 0; i < pts.length; i++) { if (!cut || (pts[i][0] <= -0.1 * s && pts[i][1] >= 0)) { out.push([px + pts[i][0] * Math.cos(th) - pts[i][1] * Math.sin(th), py + pts[i][0] * Math.sin(th) + pts[i][1] * Math.cos(th)]); } }
    return out;
  }
  for (k = 0; k < 6; k++) { CU.poly(R, cap(k, false), { fill: fill, stroke: true, sw: sw }); }
  CU.poly(R, cap(0, true), { fill: fill, stroke: true, sw: sw }, true);
};
// Circular mask on a layer (avatar in a round frame).
CU.maskCircle = function (L, cx, cy, r) {
  var mk = L.property("ADBE Mask Parade").addProperty("ADBE Mask Atom"), ms = new Shape(), k = 0.5523 * r;
  ms.vertices = [[cx, cy - r], [cx + r, cy], [cx, cy + r], [cx - r, cy]];
  ms.inTangents = [[-k, 0], [0, -k], [k, 0], [0, k]]; ms.outTangents = [[k, 0], [0, k], [-k, 0], [0, -k]]; ms.closed = true;
  mk.property("ADBE Mask Shape").setValue(ms);
  return mk;
};
// Rectangular mask on a layer (comp coordinates of the layer's source).
CU.maskRect = function (L, x0, y0, x1, y1) {
  var mk = L.property("ADBE Mask Parade").addProperty("ADBE Mask Atom"), ms = new Shape();
  ms.vertices = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]; ms.closed = true;
  mk.property("ADBE Mask Shape").setValue(ms);
  return mk;
};

// Monitor from a measured screen quad q = [UL, UR, LL, LR] (taken off the reference frame). o.side: width of the casing side
// slab beyond the near edge (< 0: left edge is near, > 0: right edge); o.base: [x, y] of the stand foot; o.bw foot width.
CU.monitorQ = function (R, q, o) {
  o = o || {};
  var UL = q[0], UR = q[1], LL = q[2], LR = q[3], b = o.bezel === undefined ? 10 : o.bezel, s = o.side || 0, a = Math.abs(s);
  var bUL = [UL[0] - b, UL[1] - b], bUR = [UR[0] + b, UR[1] - b], bLL = [LL[0] - b, LL[1] + b], bLR = [LR[0] + b, LR[1] + b];
  if (o.base) {
    var mb = CU.lerp(LL, LR, 0.5), nx = mb[0] + s * 0.6, nw = Math.max(10, (o.bw || 120) * 0.12);
    CU.poly(R, [[nx - nw, mb[1] - 20], [nx + nw, mb[1] - 20], [o.base[0] + nw * 0.8, o.base[1]], [o.base[0] - nw * 0.8, o.base[1]]], { fill: "#22252b", stroke: true, sw: 3.5 });
    CU.ell(R, o.base[0], o.base[1] + 4, o.bw || 120, (o.bw || 120) * 0.22, { fill: "#2a2e35", stroke: true, sw: 3.5 });
  }
  if (s < 0) { CU.poly(R, [bUL, [bUL[0] + s, bUL[1] + a * 0.15], [bLL[0] + s, bLL[1] - a * 0.15], bLL], { fill: "#15171b", stroke: true, sw: 4 }); }
  if (s > 0) { CU.poly(R, [bUR, [bUR[0] + s, bUR[1] + a * 0.15], [bLR[0] + s, bLR[1] - a * 0.15], bLR], { fill: "#15171b", stroke: true, sw: 4 }); }
  CU.poly(R, [bUL, bUR, bLR, bLL], { fill: o.bezelCol || "#2a2e35", stroke: true, sw: 4 });
  CU.poly(R, [UL, UR, LR, LL], { fill: o.screen || "#1d4f78", stroke: true, sw: 2.5 });
  return [UL, UR, LL, LR];
};
// Keyboard from a measured quad [backL, backR, frontR, frontL], with a thin front edge and key grid.
CU.keyboardQ = function (R, q, col) {
  var bl = q[0], br = q[1], fr = q[2], fl = q[3], r, d = "";
  CU.poly(R, [fl, fr, [fr[0], fr[1] + 10], [fl[0], fl[1] + 10]], { fill: "#15171b", stroke: true, sw: 3 });
  CU.poly(R, [bl, br, fr, fl], { fill: col || "#2a2e35", stroke: true, sw: 3.5 });
  for (r = 1; r < 5; r++) { var a = CU.lerp(CU.lerp(bl, fl, r / 5), CU.lerp(br, fr, r / 5), 0.04), b = CU.lerp(CU.lerp(bl, fl, r / 5), CU.lerp(br, fr, r / 5), 0.96); d += "M " + a[0] + " " + a[1] + " L " + b[0] + " " + b[1] + " "; }
  for (r = 1; r < 12; r++) { var p = CU.lerp(CU.lerp(bl, br, r / 12), CU.lerp(fl, fr, r / 12), 0.06), qq = CU.lerp(CU.lerp(bl, br, r / 12), CU.lerp(fl, fr, r / 12), 0.94); d += "M " + p[0] + " " + p[1] + " L " + qq[0] + " " + qq[1] + " "; }
  CU.path(R, d, { stroke: "#4a4f58", sw: 2 });
};
