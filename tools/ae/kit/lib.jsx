// Shared After Effects kit of the studio (specs/032). Moved from films/ae-crayon-test/ae/lib.jsx on 2026-11-23.
// Paths come from CU.WORK (the folder the entry script runs in); film data lives in CU.WORK/data/.
// lib.jsx: drawing and animation helpers for After Effects (ExtendScript, ES3).
// Shapes use comp coordinates (layer anchor and position at 0,0 unless a pivot is set).
// Groups added later are drawn ON TOP (like SVG), unlike AE's default.

var CU = {};
CU.FPS = 30;
CU.W = 1920;
CU.H = 1080;
CU.INK = [0.11, 0.11, 0.12];
CU.SW = 4.5;           // outline width at 1080p
CU.FONT = "InkFree";   // handwriting font on this machine
CU.log = null;

// Each line reaches the disk at once (close + reopen to append): ExtendScript keeps writes in memory until close, and
// the waiting side reads log.txt to know After Effects started (a long full-size build showed an empty log for > 240 s).
CU.say = function (s) { if (CU.log) { CU.log.writeln(s); CU.log.close(); CU.log.encoding = "UTF-8"; CU.log.open("a"); } };

CU.hex = function (h) {
  if (h === null || h === undefined) { return null; }
  if (h instanceof Array) { return h; }
  h = h.replace("#", "");
  if (h.length === 3) { h = h.charAt(0) + h.charAt(0) + h.charAt(1) + h.charAt(1) + h.charAt(2) + h.charAt(2); }
  return [parseInt(h.substr(0, 2), 16) / 255, parseInt(h.substr(2, 2), 16) / 255, parseInt(h.substr(4, 2), 16) / 255];
};

CU.shade = function (h, k) { // k<1 darker, k>1 lighter
  var c = CU.hex(h), o = [], i;
  for (i = 0; i < 3; i++) { o.push(k <= 1 ? c[i] * k : c[i] + (1 - c[i]) * (k - 1)); }
  return o;
};

// ---------- comps and layers ----------
CU.comp = function (name, dur, w, h) {
  return app.project.items.addComp(name, w || CU.W, h || CU.H, 1, dur, CU.FPS);
};

CU.layer = function (comp, name, pivot) {
  var L = comp.layers.addShape();
  L.name = name;
  var tr = L.property("ADBE Transform Group");
  var p = pivot || [0, 0];
  tr.property("ADBE Anchor Point").setValue(p);
  tr.property("ADBE Position").setValue(p);
  return L;
};

CU.root = function (L) { return L.property("ADBE Root Vectors Group"); };

CU.solid = function (comp, name, color) {
  var L = comp.layers.addSolid(CU.hex(color), name, comp.width, comp.height, 1, comp.duration);
  return L;
};

CU.nul = function (comp, name, pos) {
  var L = comp.layers.addNull(comp.duration);
  L.name = name;
  L.property("ADBE Transform Group").property("ADBE Position").setValue(pos || [comp.width / 2, comp.height / 2]);
  return L;
};

CU.pre = function (comp, item, name, pos, scale) {
  var L = comp.layers.add(item);
  if (name) { L.name = name; }
  var tr = L.property("ADBE Transform Group");
  if (item.name.indexOf("P ") === 0 && CU.FEET) { tr.property("ADBE Anchor Point").setValue(CU.FEET); }
  if (pos) { tr.property("ADBE Position").setValue(pos); }
  if (scale) { tr.property("ADBE Scale").setValue([scale, scale]); }
  if (CU.SC && CU.SC.comp === comp && CU.META && CU.META[item.name]) {
    var mt = CU.META[item.name];
    if (mt.armsOf) { var q9; for (q9 = 0; q9 < CU.SC.persons.length; q9++) { if (CU.SC.persons[q9].layer.source.name === mt.armsOf) { CU.SC.persons[q9].armsLayer = L; } } }
    else { CU.SC.persons.push({ name: name || item.name, layer: L, meta: mt }); }
  }
  return L;
};

// ---------- geometry ----------
// Parse an SVG-like path (M L C Q H V Z, absolute and relative) into AE Shapes.
CU.parse = function (d) {
  var toks = d.replace(/([MmLlCcQqHhVvZz])/g, " $1 ").replace(/,/g, " ").replace(/-/g, " -").replace(/e -/g, "e-").split(/\s+/);
  var out = [], i = 0, cmd = "", cx = 0, cy = 0, sx = 0, sy = 0, cur = null;
  var t = [];
  for (i = 0; i < toks.length; i++) { if (toks[i] !== "") { t.push(toks[i]); } }
  function num() { return parseFloat(t[i++]); }
  function start(x, y) {
    if (cur) { out.push(cur); }
    cur = { v: [[x, y]], it: [[0, 0]], ot: [[0, 0]], closed: false };
  }
  function lineTo(x, y) { cur.v.push([x, y]); cur.it.push([0, 0]); cur.ot.push([0, 0]); }
  function curveTo(x1, y1, x2, y2, x, y) {
    var n = cur.v.length - 1;
    cur.ot[n] = [x1 - cur.v[n][0], y1 - cur.v[n][1]];
    cur.v.push([x, y]); cur.it.push([x2 - x, y2 - y]); cur.ot.push([0, 0]);
  }
  i = 0;
  while (i < t.length) {
    var tk = t[i];
    if (/^[MmLlCcQqHhVvZz]$/.test(tk)) { cmd = tk; i++; }
    var rel = (cmd === cmd.toLowerCase());
    var C = cmd.toUpperCase();
    var bx = rel ? cx : 0, by = rel ? cy : 0;
    if (C === "Z") {
      if (cur) {
        var n0 = cur.v.length - 1;
        if (n0 > 0 && Math.abs(cur.v[n0][0] - cur.v[0][0]) < 0.01 && Math.abs(cur.v[n0][1] - cur.v[0][1]) < 0.01) {
          cur.it[0] = cur.it[n0]; cur.v.pop(); cur.it.pop(); cur.ot.pop();
        }
        cur.closed = true; cx = sx; cy = sy;
      }
      continue;
    }
    if (C === "M") { cx = bx + num(); cy = by + num(); sx = cx; sy = cy; start(cx, cy); cmd = rel ? "l" : "L"; }
    else if (C === "L") { cx = bx + num(); cy = by + num(); lineTo(cx, cy); }
    else if (C === "H") { cx = bx + num(); lineTo(cx, cy); }
    else if (C === "V") { cy = (rel ? cy : 0) + num(); lineTo(cx, cy); }
    else if (C === "C") {
      var x1 = bx + num(), y1 = by + num(), x2 = bx + num(), y2 = by + num();
      cx = bx + num(); cy = by + num(); curveTo(x1, y1, x2, y2, cx, cy);
    } else if (C === "Q") {
      var qx = bx + num(), qy = by + num(), ex = bx + num(), ey = by + num();
      curveTo(cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy), ex + 2 / 3 * (qx - ex), ey + 2 / 3 * (qy - ey), ex, ey);
      cx = ex; cy = ey;
    } else { i++; }
  }
  if (cur) { out.push(cur); }
  var shapes = [], k;
  for (k = 0; k < out.length; k++) {
    var s = new Shape();
    s.vertices = out[k].v; s.inTangents = out[k].it; s.outTangents = out[k].ot; s.closed = out[k].closed;
    shapes.push(s);
  }
  return shapes;
};

// Points -> smooth closed or open path string (Catmull-Rom to cubic).
CU.smooth = function (pts, closed, tension) {
  var n = pts.length, k = (tension === undefined ? 1 : tension) / 6, d = "M " + pts[0][0] + " " + pts[0][1], i;
  var last = closed ? n : n - 1;
  for (i = 0; i < last; i++) {
    var p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n];
    if (!closed) { if (i === 0) { p0 = p1; } if (i + 2 >= n) { p3 = p2; } }
    d += " C " + (p1[0] + (p2[0] - p0[0]) * k) + " " + (p1[1] + (p2[1] - p0[1]) * k) + " " +
      (p2[0] - (p3[0] - p1[0]) * k) + " " + (p2[1] - (p3[1] - p1[1]) * k) + " " + p2[0] + " " + p2[1];
  }
  return d + (closed ? " Z" : "");
};

// Circular arc as cubic segments, angles in degrees (0 = +x, 90 = +y down).
CU.arc = function (cx, cy, r, a0, a1, moveFirst) {
  var segs = Math.max(1, Math.ceil(Math.abs(a1 - a0) / 90)), da = (a1 - a0) / segs, d = "", i;
  var rad = Math.PI / 180;
  for (i = 0; i < segs; i++) {
    var s = (a0 + da * i) * rad, e = (a0 + da * (i + 1)) * rad, h = 4 / 3 * Math.tan((e - s) / 4) * r;
    var x0 = cx + r * Math.cos(s), y0 = cy + r * Math.sin(s), x3 = cx + r * Math.cos(e), y3 = cy + r * Math.sin(e);
    if (i === 0 && moveFirst) { d += "M " + x0 + " " + y0 + " "; }
    d += "C " + (x0 - h * Math.sin(s)) + " " + (y0 + h * Math.cos(s)) + " " + (x3 + h * Math.sin(e)) + " " + (y3 - h * Math.cos(e)) + " " + x3 + " " + y3 + " ";
  }
  return d;
};

// Lower crescent shadow of a round head: head circle minus a circle shifted by (dx,dy).
// Returns a dense polygon path string (no stroke needed).
CU.crescent = function (cx, cy, r, dx, dy, r2) {
  r2 = r2 || r;
  var ox = cx + dx, oy = cy + dy, rad = Math.PI / 180, outer = [], inner = [], a, i;
  var base = Math.atan2(-dy, -dx) / rad; // direction away from the offset
  for (a = base - 180; a <= base + 180; a += 2) {
    var x = cx + r * Math.cos(a * rad), y = cy + r * Math.sin(a * rad);
    if ((x - ox) * (x - ox) + (y - oy) * (y - oy) > r2 * r2) { outer.push([x, y]); }
  }
  var b0 = Math.atan2(dy, dx) / rad + 180;
  for (a = b0 + 180; a >= b0 - 180; a -= 2) {
    var x2 = ox + r2 * Math.cos(a * rad), y2 = oy + r2 * Math.sin(a * rad);
    if ((x2 - cx) * (x2 - cx) + (y2 - cy) * (y2 - cy) < r * r) { inner.push([x2, y2]); }
  }
  // inner points must run from the outer arc's end back to its start
  if (inner.length > 1 && outer.length > 1) {
    var e = outer[outer.length - 1], f = inner[0], g = inner[inner.length - 1];
    if ((e[0] - g[0]) * (e[0] - g[0]) + (e[1] - g[1]) * (e[1] - g[1]) < (e[0] - f[0]) * (e[0] - f[0]) + (e[1] - f[1]) * (e[1] - f[1])) { inner.reverse(); }
  }
  var pts = outer.concat(inner), d = "M " + pts[0][0] + " " + pts[0][1];
  for (i = 1; i < pts.length; i++) { d += " L " + pts[i][0] + " " + pts[i][1]; }
  return d + " Z";
};

// ---------- shape contents ----------
CU.grp = function (parent, name) { // parent: a Root Vectors Group or a group's "ADBE Vectors Group"
  var g = parent.addProperty("ADBE Vector Group");
  if (name) { g.name = name; }
  return g;
};
CU.inner = function (g) { return g.property("ADBE Vectors Group"); };
CU.xf = function (g) { return g.property("ADBE Vector Transform Group"); };

CU.paint = function (cont, st) {
  if (st.stroke !== null && st.stroke !== undefined && st.stroke !== false && (st.sw === undefined || st.sw > 0)) {
    var s = cont.addProperty("ADBE Vector Graphic - Stroke");
    s.property("ADBE Vector Stroke Color").setValue(CU.hex(st.stroke === true ? CU.INK : st.stroke));
    s.property("ADBE Vector Stroke Width").setValue(st.sw === undefined ? CU.SW : st.sw);
    s.property("ADBE Vector Stroke Line Cap").setValue(st.cap || 2);
    s.property("ADBE Vector Stroke Line Join").setValue(2);
    if (st.so !== undefined) { s.property("ADBE Vector Stroke Opacity").setValue(st.so); }
  }
  if (st.fill) {
    var f = cont.addProperty("ADBE Vector Graphic - Fill");
    f.property("ADBE Vector Fill Color").setValue(CU.hex(st.fill));
    if (st.fo !== undefined) { f.property("ADBE Vector Fill Opacity").setValue(st.fo); }
    if (st.evenodd) { f.property("ADBE Vector Fill Rule").setValue(2); }
  }
};

CU.top = function (g) { try { g.moveTo(1); } catch (e) { } };

// style: {fill, stroke (true = ink), sw, fo, so, cap, name, trim:[t0,t1], evenodd}
CU.path = function (parent, d, st) {
  st = st || {};
  var g = CU.grp(parent, st.name || "path");
  var c = CU.inner(g), shapes = (typeof d === "string") ? CU.parse(d) : d, i;
  for (i = 0; i < shapes.length; i++) {
    var p = c.addProperty("ADBE Vector Shape - Group");
    p.property("ADBE Vector Shape").setValue(shapes[i]);
  }
  if (st.trim) {
    var tr = c.addProperty("ADBE Vector Filter - Trim");
    var te = tr.property("ADBE Vector Trim End");
    te.setValueAtTime(st.trim[0], 0); te.setValueAtTime(st.trim[1], 100);
  }
  CU.paint(c, st);
  var idx = g.propertyIndex;
  CU.top(parent.property(idx));
  return parent.property(1);
};

CU.ell = function (parent, cx, cy, w, h, st) {
  st = st || {};
  var g = CU.grp(parent, st.name || "ellipse"), c = CU.inner(g);
  var e = c.addProperty("ADBE Vector Shape - Ellipse");
  e.property("ADBE Vector Ellipse Size").setValue([w, h]);
  e.property("ADBE Vector Ellipse Position").setValue([cx, cy]);
  CU.paint(c, st);
  CU.top(parent.property(g.propertyIndex));
  return parent.property(1);
};

CU.rect = function (parent, x, y, w, h, r, st) { // x,y = top-left
  st = st || {};
  var g = CU.grp(parent, st.name || "rect"), c = CU.inner(g);
  var e = c.addProperty("ADBE Vector Shape - Rect");
  e.property("ADBE Vector Rect Size").setValue([w, h]);
  e.property("ADBE Vector Rect Position").setValue([x + w / 2, y + h / 2]);
  e.property("ADBE Vector Rect Roundness").setValue(r || 0);
  CU.paint(c, st);
  CU.top(parent.property(g.propertyIndex));
  return parent.property(1);
};

// Polygon from a flat list of points.
CU.poly = function (parent, pts, st, open) {
  var d = "M " + pts[0][0] + " " + pts[0][1], i;
  for (i = 1; i < pts.length; i++) { d += " L " + pts[i][0] + " " + pts[i][1]; }
  return CU.path(parent, d + (open ? "" : " Z"), st);
};

// Hand-drawn squiggle text line (like the channel's scribbled fake text).
CU.squiggle = function (x, y, len, amp, seed) {
  var d = "M " + x + " " + y, cx = x, k = 0, r = seed || 1;
  function rnd() { r = (r * 9301 + 49297) % 233280; return r / 233280; }
  while (cx < x + len) {
    var step = 10 + rnd() * 10;
    if (rnd() < 0.12 && cx > x + 20) { cx += 14; d += " M " + cx + " " + y; continue; }
    d += " Q " + (cx + step / 2) + " " + (y + (k % 2 ? amp : -amp) * (0.6 + rnd() * 0.6)) + " " + (cx + step) + " " + y;
    cx += step; k++;
  }
  return d;
};

CU.rand = function (seed) {
  var r = seed || 7;
  return function () { r = (r * 9301 + 49297) % 233280; return r / 233280; };
};

// ---------- keys and expressions ----------
CU.ease = function (prop, inf) {
  var i, n = prop.numKeys;
  for (i = 1; i <= n; i++) {
    var e = new KeyframeEase(0, inf || 50), ok = false, arr = [[e], [e, e], [e, e, e]], j;
    for (j = 0; j < 3 && !ok; j++) { try { prop.setTemporalEaseAtKey(i, arr[j], arr[j]); ok = true; } catch (er) { } }
  }
};

CU.keys = function (prop, list, inf) { // list of [t, value]
  var i;
  for (i = 0; i < list.length; i++) { prop.setValueAtTime(list[i][0], list[i][1]); }
  if (inf !== 0) { CU.ease(prop, inf); }
  return prop;
};

CU.T = function (L, name) { return L.property("ADBE Transform Group").property(name); };
CU.pos = function (L) { return CU.T(L, "ADBE Position"); };
CU.scl = function (L) { return CU.T(L, "ADBE Scale"); };
CU.rot = function (L) { return CU.T(L, "ADBE Rotate Z"); };
CU.opa = function (L) { return CU.T(L, "ADBE Opacity"); };
CU.anc = function (L) { return CU.T(L, "ADBE Anchor Point"); };

// Camera: parent every layer (except those listed) to a CAM null and frame [t, fx, fy, zoom].
CU.CAMSTILL = CU.CAMSTILL || false;  // specs/039: `camera stills` builds every shot at scale 1, centred (the options crop it)
CU.camera = function (comp, frames, skip, inf) {
  if (CU.CAMSTILL) { frames = [[0, comp.width / 2, comp.height / 2, 1], [comp.duration, comp.width / 2, comp.height / 2, 1]]; frames.fromMotion = true; inf = 0; }
  if (CU.CUR_SHOT && !frames.fromMotion && !(CU.NO_MOTION && CU.NO_MOTION[CU.CUR_SHOT])) {
    var mf = new File(CU.MOTION + "S" + CU.CUR_SHOT + ".json");
    if (mf.exists) { frames = CU.camFromMotion(comp, CU.readJSON(mf.fsName), [frames[0][1], frames[0][2]], frames[0][3]); inf = 0; CU.say("camera S" + CU.CUR_SHOT + ": measured path"); }
  }
  if (CU.applySnaps) { CU.applySnaps(comp, frames); }
  var cam = CU.nul(comp, "CAM"), i, k;
  for (i = 2; i <= comp.numLayers; i++) {
    var L = comp.layer(i), sk = false;
    for (k = 0; skip && k < skip.length; k++) { if (L.name === skip[k]) { sk = true; } }
    if (!sk && L.parent === null) { L.parent = cam; }
  }
  var cx = comp.width / 2, cy = comp.height / 2, pk = [], sc = [];
  for (i = 0; i < frames.length; i++) {
    var f = frames[i];
    pk.push([f[0], [cx - f[3] * (f[1] - cx), cy - f[3] * (f[2] - cy)]]);
    sc.push([f[0], [f[3] * 100, f[3] * 100]]);
  }
  if (!CU.camInside(comp, frames)) { CU.say("CHECK camera " + comp.name + ": the view leaves the drawn background (exposed frame edge)"); }
  CU.keys(CU.pos(cam), pk, inf === 0 ? 0 : (inf || 45));
  CU.keys(CU.scl(cam), sc, inf === 0 ? 0 : (inf || 45));
  return cam;
};

CU.fx = function (L, match) { return L.property("ADBE Effect Parade").addProperty(match); };
CU.fxset = function (eff, names, v) { // try several property names / matchNames
  var i;
  for (i = 0; i < names.length; i++) {
    try { var p = eff.property(names[i]); if (p) { p.setValue(v); return p; } } catch (e) { }
  }
  CU.say("fxset failed: " + names.join("/"));
  return null;
};
CU.glow = function (L, radius, intensity, threshold) {
  var g = CU.fx(L, "ADBE Glo2");
  CU.fxset(g, ["ADBE Glo2-0002", "Glow Threshold"], threshold === undefined ? 40 : threshold);
  CU.fxset(g, ["ADBE Glo2-0003", "Glow Radius"], radius || 30);
  CU.fxset(g, ["ADBE Glo2-0004", "Glow Intensity"], intensity || 1.2);
  return g;
};
CU.blur = function (L, amt) {
  var b = CU.fx(L, "ADBE Gaussian Blur 2");
  CU.fxset(b, ["ADBE Gaussian Blur 2-0001", "Blurriness"], amt);
  try { b.property("ADBE Gaussian Blur 2-0003").setValue(1); } catch (e) { } // repeat edge pixels
  return b;
};
CU.ramp = function (L, p0, c0, p1, c1, radial) {
  var r = CU.fx(L, "ADBE Ramp");
  CU.fxset(r, ["ADBE Ramp-0001", "Start of Ramp"], p0);
  CU.fxset(r, ["ADBE Ramp-0002", "Start Color"], CU.hex(c0));
  CU.fxset(r, ["ADBE Ramp-0003", "End of Ramp"], p1);
  CU.fxset(r, ["ADBE Ramp-0004", "End Color"], CU.hex(c1));
  if (radial) { CU.fxset(r, ["ADBE Ramp-0005", "Ramp Shape"], 2); }
  return r;
};
CU.wobble = function (L, amount, size, speed) { // hand-drawn line wobble (screen line art)
  var t = CU.fx(L, "ADBE Turbulent Displace");
  CU.fxset(t, ["ADBE Turbulent Displace-0002", "Amount"], amount || 6);
  CU.fxset(t, ["ADBE Turbulent Displace-0003", "Size"], size || 14);
  try { t.property("ADBE Turbulent Displace-0006").expression = "time*" + (speed || 120); } catch (e) { }
  return t;
};

// ---------- text ----------
CU.text = function (comp, str, o) {
  o = o || {};
  var L = comp.layers.addText(str);
  L.name = o.name || ("txt " + str.substr(0, 12));
  var sp = L.property("ADBE Text Properties").property("ADBE Text Document");
  var td = sp.value;
  td.resetCharStyle();
  td.fontSize = o.size || 48;
  td.fillColor = CU.hex(o.color || CU.INK);
  td.applyFill = true;
  if (o.strokeColor) {
    td.applyStroke = true; td.strokeColor = CU.hex(o.strokeColor); td.strokeWidth = o.strokeWidth || 4; td.strokeOverFill = false;
  } else if (o.bold) {
    td.applyStroke = true; td.strokeColor = CU.hex(o.color || CU.INK); td.strokeWidth = Math.max(2, (o.size || 48) * 0.075); td.strokeOverFill = true;
  } else { td.applyStroke = false; }
  try { td.font = o.font || CU.FONT; } catch (e) { }
  if (o.tracking !== undefined) { td.tracking = o.tracking; }
  if (o.bold) { try { td.fauxBold = true; } catch (e2) { } }
  td.justification = o.center ? ParagraphJustification.CENTER_JUSTIFY : (o.right ? ParagraphJustification.RIGHT_JUSTIFY : ParagraphJustification.LEFT_JUSTIFY);
  sp.setValue(td);
  CU.pos(L).setValue([o.x || 0, o.y || 0]);
  if (o.rot) { CU.rot(L).setValue(o.rot); }
  return L;
};

CU.esc = function (s) { return s.replace(/\\/g, "\\\\").replace(/"/g, "\\\""); };

// Typewriter: characters appear from t0 at cps chars per second; optional clear at t1.
CU.typeOn = function (L, str, t0, cps, t1) {
  var e = "var s=\"" + CU.esc(str) + "\"; var n=Math.floor((time-" + t0 + ")*" + cps + "); ";
  e += (t1 !== undefined ? "if(time>=" + t1 + ") n=0; " : "") + "n<=0?\" \":s.substr(0,n);";
  L.property("ADBE Text Properties").property("ADBE Text Document").expression = e;
};

CU.textWidth = function (L) {
  try { return L.sourceRectAtTime(0, false).width; } catch (e) { return 600; }
};

// Speech bubble: rounded box with a pointed tail to (tx,ty). Returns the layer.
CU.bubble = function (comp, name, x, y, w, h, tx, ty, inT) {
  var L = CU.layer(comp, name), R = CU.root(L);
  var bx = Math.max(x + 40, Math.min(x + w - 90, tx - 30));
  var d = "M " + (x + 30) + " " + y + " L " + (x + w - 30) + " " + y + " Q " + (x + w) + " " + y + " " + (x + w) + " " + (y + 30) +
    " L " + (x + w) + " " + (y + h - 30) + " Q " + (x + w) + " " + (y + h) + " " + (x + w - 30) + " " + (y + h) +
    " L " + (bx + 70) + " " + (y + h) + " L " + tx + " " + ty + " L " + bx + " " + (y + h) +
    " L " + (x + 30) + " " + (y + h) + " Q " + x + " " + (y + h) + " " + x + " " + (y + h - 30) +
    " L " + x + " " + (y + 30) + " Q " + x + " " + y + " " + (x + 30) + " " + y + " Z";
  CU.path(R, d, { fill: "#ffffff", stroke: true, sw: 4 });
  if (inT !== undefined) { L.inPoint = inT; }
  if (CU.SC && CU.SC.comp === comp) { (CU.SC.bubbles = CU.SC.bubbles || []).push({ name: name, box: [x, y, x + w, y + h], t0: inT || 0 }); }
  return L;
};

// Floating caption (white handwriting with a dark outline) with a small tick toward the speaker.
CU.caption = function (comp, str, x, y, t0, cps, o) {
  o = o || {};
  var sz = (o.size || 54) * 1.2;
  var Lb = CU.text(comp, str, { size: sz, color: "#1c1c1f", strokeColor: "#1c1c1f", strokeWidth: sz * 0.22, x: x, y: y, center: o.center, name: (o.name || "caption") + " outline" });
  CU.typeOn(Lb, str, t0, cps, o.t1);
  var L = CU.text(comp, str, { size: sz, color: "#ffffff", strokeColor: "#ffffff", strokeWidth: sz * 0.05, x: x, y: y, center: o.center, name: o.name || "caption" });
  var tw = CU.textWidth(L);
  CU.typeOn(L, str, t0, cps, o.t1);
  if (o.speaker && CU.SC) { CU.pointer("caption '" + str + "'", o.tick ? [o.tick[0] + (o.tick[2] || 10), o.tick[1] + 14] : [x + tw / 2, y + 10], o.speaker, t0, o.t1, "screen"); CU.SC.pointers[CU.SC.pointers.length - 1].box = [x, y - sz * 0.8, x + tw, y + sz * 0.2]; if (o.tick) { CU.SC.pointers[CU.SC.pointers.length - 1].tickStart = [o.tick[0], o.tick[1]]; } }
  if (CU.CAPSKIP) { CU.CAPSKIP.push((o.name || "caption") + " outline"); }
  if (o.tick) {
    var T = CU.layer(comp, (o.name || "caption") + " tick"), R = CU.root(T);
    CU.path(R, "M " + o.tick[0] + " " + o.tick[1] + " l " + (o.tick[2] || 10) + " 14", { stroke: "#ffffff", sw: 3 });
    CU.opa(T).expression = "time<" + t0 + " || " + (o.t1 !== undefined ? "time>=" + o.t1 : "false") + " ? 0 : 100";
  }
  return L;
};

// Warm cone of lamp light, screen-blended and softened.
CU.lightCone = function (comp, name, apex, w0, w1, y1, color, opacity) {
  var L = CU.layer(comp, name), R = CU.root(L);
  CU.poly(R, [[apex[0] - w0 / 2, apex[1]], [apex[0] + w0 / 2, apex[1]], [apex[0] + w1 / 2, y1], [apex[0] - w1 / 2, y1]], { fill: color || "#ffd98a" });
  CU.blur(L, 25); L.blendingMode = BlendingMode.SCREEN; CU.opa(L).setValue(opacity || 30);
  return L;
};

// Layout matching (cách 2): place a person so its head follows a measured track [[t, screenX, screenY, radius]].
// cam: a function t -> [fx, fy, zoom] (our camera), or "size" to derive the zoom from the head size (person keeps
// its depth, so a smaller head on screen means the camera pulls back). Returns the camera frames to use.
CU.headTrack = function (c, item, name, track, cam, keepFrames) {
  var m = CU.META[item.name], i, frames = [], keys = [];
  var r0 = track[0][3], rs = r0 * 1.05; // scene head radius (+5%: the detector reads the skin disc, inside the outline and below the hair)
  if (cam !== "size") { rs = rs / cam(track[0][0])[2]; }
  for (i = 0; i < track.length; i++) {
    var t = track[i][0], cf;
    if (cam === "size") { cf = [c.width / 2, c.height / 2, track[i][3] * 1.05 / rs]; frames.push([t, cf[0], cf[1], cf[2]]); }
    else { cf = cam(t); }
    var hx = cf[0] + (track[i][1] - 960) / cf[2], hy = cf[1] + (track[i][2] - 540) / cf[2];
    var s = rs / m.R;
    keys.push([t, [hx - m.dir * 0.06 * m.R * s, hy + (m.legLen + m.bodyH + 0.62 * m.R) * s]]);
  }
  var L = CU.pre(c, item, name, keys[0][1], 100 * rs / m.R);
  CU.keys(CU.pos(L), keys, 40);
  if (CU.SC) { var q8; for (q8 = 0; q8 < CU.SC.persons.length; q8++) { if (CU.SC.persons[q8].layer === L) { CU.SC.persons[q8].tracked = true; } } }
  if (cam === "size") { frames.unshift([0, frames[0][1], frames[0][2], frames[0][3]]); frames.push([c.duration, frames[frames.length - 1][1], frames[frames.length - 1][2], frames[frames.length - 1][3]]); }
  return frames;
};
CU.camLinear = function (frames) { // t -> [fx, fy, z], linear between frames
  return function (t) {
    var i;
    if (t <= frames[0][0]) { return [frames[0][1], frames[0][2], frames[0][3]]; }
    for (i = 1; i < frames.length; i++) {
      if (t <= frames[i][0]) { var a = frames[i - 1], b = frames[i], u = (t - a[0]) / (b[0] - a[0]); return [a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u, a[3] + (b[3] - a[3]) * u]; }
    }
    var l = frames[frames.length - 1]; return [l[1], l[2], l[3]];
  };
};

// Camera matching (cách 3): a measured camera path [[t, scale, tx, ty]] (frame-0 screen positions -> frame-t, 1920x1080)
// becomes CAM frames [t, fx, fy, zoom], starting from our framing f0 (scene point at the frame centre) and zoom z0.
// Sofa asset (cách 3 of the staging research): back, seat top in perspective, seat front, arms and feet.
// o: {x0, x1, seatY (where the hips rest), frontY (front edge of the seat), floorY, backTop, color}
// Returns {layer, seat: [x, y], seatW, box} for CU.prop / CU.support("…", "seat:sofa").
CU.sofa = function (comp, name, o) {
  var L = CU.layer(comp, name), R = CU.root(L), col = CU.hex(o.color), top = CU.shade(col, 1.12), side = CU.shade(col, 0.85), dark = CU.shade(col, 0.7);
  var x0 = o.x0, x1 = o.x1, sy = o.seatY, fy = o.frontY, fl = o.floorY, bt = o.backTop, aw = o.armW || 120;
  CU.rect(R, x0 + 30, bt, x1 - x0 - 60, sy - bt + 20, 40, { fill: col, stroke: true });                                   // back rest
  CU.path(R, "M " + (x0 + 40) + " " + (sy - 22) + " L " + (x1 - 40) + " " + (sy - 22) + " L " + (x1 - 10) + " " + fy + " L " + (x0 + 10) + " " + fy + " Z", { fill: top, stroke: true }); // seat top
  var cxm = (x0 + x1) / 2;
  CU.path(R, "M " + cxm + " " + (sy - 22) + " L " + cxm + " " + fy, { stroke: true, sw: 3 });                               // cushion seam
  var fh = Math.max(40, (fl - fy) * 0.62);
  CU.rect(R, x0 + 10, fy, x1 - x0 - 20, fh, 10, { fill: side, stroke: true });                                            // seat front
  CU.path(R, "M " + cxm + " " + fy + " L " + cxm + " " + (fy + fh), { stroke: true, sw: 3 });
  CU.rect(R, x0 - aw / 2, bt + (sy - bt) * 0.45, aw, fy + fh - (bt + (sy - bt) * 0.45), 36, { fill: col, stroke: true });  // arms
  CU.rect(R, x1 - aw / 2, bt + (sy - bt) * 0.45, aw, fy + fh - (bt + (sy - bt) * 0.45), 36, { fill: col, stroke: true });
  CU.rect(R, x0 + 20, fy + fh, 26, Math.max(10, fl - fy - fh), 4, { fill: "#3b2a20", stroke: true, sw: 3 });             // feet
  CU.rect(R, x1 - 46, fy + fh, 26, Math.max(10, fl - fy - fh), 4, { fill: "#3b2a20", stroke: true, sw: 3 });
  CU.ell(R, cxm, fl + 4, x1 - x0, 26, { fill: "#000000", fo: 18 });                                                        // floor shadow
  return { layer: L, seat: [cxm, sy], seatW: (x1 - x0) / 2, box: [x0 - aw / 2, bt, x1 + aw / 2, fl] };
};
CU.readJSON = function (path) { var f = new File(path); f.open("r"); var s = f.read(); f.close(); return eval("(" + s + ")"); };
CU.WORK = CU.WORK || "";   // set by entry.jsx (tools/ae/bundle.py)
CU.MOTION = "";            // CU.WORK + "/data/motion/", set by entry.jsx
// specs/035: shot lengths come from the film's timing.json (bundled as data/timing.json). A film writes
// `var n = CU.shotFrames("S2") || 117;` so it still builds before it has a timing.json.
CU.TIMING = null;
CU.DRAFT = CU.DRAFT || false;  // set by entry.jsx for `ae draft`: quarter resolution, draft quality
CU.shotFrames = function (id) {
  if (CU.TIMING === null) {
    var f = new File(CU.WORK + "/data/timing.json");
    try { CU.TIMING = f.exists ? CU.readJSON(f.fsName) : {}; } catch (e) { CU.TIMING = {}; }
  }
  var fr = CU.TIMING && CU.TIMING.frames;
  return (fr && fr[id] && fr[id] >= 1) ? fr[id] : undefined;
};
// CU.keyScan(comp): every property with 2 or more keyframes in the comp's layers (and in the precomps they hold),
// as [{layer, prop, t0, t1}] in seconds of this comp (specs/035 R5: which motions a shorter shot drops or squeezes).
CU.keyScan = function (comp) {
  var out = [];
  function walk(g, lname, off, depth) {
    var k, p;
    for (k = 1; k <= g.numProperties; k++) {
      try { p = g.property(k); } catch (e) { p = null; }
      if (!p) { continue; }
      if (p.propertyType === PropertyType.PROPERTY) {
        if (p.numKeys >= 2) {                               // an effect's control (a rig's 'HR' Point) goes by the effect's name
          out.push({ layer: lname, prop: CU.keyName(p), t0: Math.max(0, p.keyTime(1) + off), t1: Math.min(comp.duration, p.keyTime(p.numKeys) + off) });
        }
      } else if (depth < 12) { walk(p, lname, off, depth + 1); }
    }
  }
  function scan(c, off, level, outer) {
    var i, L;
    for (i = 1; i <= c.numLayers; i++) {
      L = c.layer(i);                                       // inside a precomp: "B s1 hero" (its CTRL) or "B s1 hero › Arm"
      walk(L, outer ? (L.name === "CTRL" ? outer : outer + " \u203a " + L.name) : L.name, off, 0);
      if (level < 3 && L.source && L.source instanceof CompItem) { scan(L.source, off + L.startTime, level + 1, L.name); }
    }
  }
  scan(comp, 0, 0, "");
  return out;
};
// The name of a keyed property for keys.json: an effect control is named by its effect ('HR', 'crouch'), adding the
// control's own name when the effect has more than one control; any other property keeps its name ('Position').
CU.keyName = function (p) {
  var g = null;
  try { g = p.parentProperty; } catch (e) { g = null; }
  try {
    if (g && g.parentProperty && g.parentProperty.matchName === "ADBE Effect Parade") {
      return g.numProperties > 1 && !/^(Point|Slider|Angle|Checkbox|Color)$/.test(p.name) ? g.name + " " + p.name : g.name;
    }
  } catch (e2) { }
  return p.name;
};
CU.jstr = function (s) {
  return "\"" + String(s).replace(/\\/g, "\\\\").replace(/"/g, "\\\"").replace(/[\u0000-\u001f]/g, " ") + "\"";
};
CU.camFromMotion = function (comp, motion, f0, z0) {
  var k, fr;
  for (k = 0; k < 25; k++) { fr = CU._camFromMotion(comp, motion, f0, z0); if (CU.camInside(comp, fr)) { return fr; } z0 *= 1.02; }
  CU.say("CHECK camera " + comp.name + ": the measured move leaves the drawn background even at zoom " + z0.toFixed(2));
  return fr;
};
// specs/039 R7: the camera chosen at the Camera review (the shot plan of film.json, bundled as data/camera.json).
// CU.planCam(comp, "S3", skip) parents the layers to CAM like CU.camera and keys its start and end:
//   start {scale, cx, cy}  zoom and the scene point (% of the comp) at the frame centre on the first frame
//   zoom_pct, drift_px     end zoom = scale·(1 + zoom/100); the window moves drift_px (1080p screen px) by the end
//   ease_ae [in, out]      speed-0 ease, out influence on the first key and in influence on the last
// A measured path (data/motion/S#.json) still wins (CU.camera). Returns the CAM null, or null when the shot has no
// camera block (the shot then keeps its own CU.camera frames).
CU.CAMPLAN = null;
CU.planCamBlock = function (id) {
  if (CU.CAMPLAN === null) {
    var f = new File(CU.WORK + "/data/camera.json");
    try { CU.CAMPLAN = f.exists ? CU.readJSON(f.fsName) : {}; } catch (e) { CU.CAMPLAN = {}; }
  }
  return CU.CAMPLAN[id] || null;
};
CU.planFrames = function (comp, c) {
  var W = comp.width, H = comp.height, st = c.start, z0 = st.scale, z1 = st.scale * (1 + c.zoom_pct / 100);
  var fx = st.cx / 100 * W, fy = st.cy / 100 * H, d = c.drift_px || [0, 0];
  return [[0, fx, fy, z0], [comp.duration, fx + d[0] / z1, fy + d[1] / z1, z1]];
};
CU.planCam = function (comp, id, skip) {
  var c = CU.planCamBlock(id || ("S" + CU.CUR_SHOT));
  if (!c) { return null; }
  var frames = CU.planFrames(comp, c), cam = CU.camera(comp, frames, skip, 0), k, p, e = c.ease_ae;
  if (!e || c.move === "static") { return cam; }
  var props = [CU.pos(cam), CU.scl(cam)];
  for (k = 0; k < props.length; k++) {
    p = props[k];
    if (p.numKeys !== 2) { continue; }                       // a measured path keyed every frame: keep it
    var j, q, a, b;                                          // Position takes 1 ease, Scale one per dimension
    for (j = 1; j <= 3; j++) {
      a = []; b = []; for (q = 0; q < j; q++) { a.push(new KeyframeEase(0, e[1])); b.push(new KeyframeEase(0, e[0])); }
      try { p.setTemporalEaseAtKey(1, a, a); p.setTemporalEaseAtKey(2, b, b); break; } catch (er) { }
    }
  }
  CU.say("camera " + id + ": " + c.move + " " + c.zoom_pct + "% (Camera review)");
  return cam;
};
CU.BOUNDS = {}; // comp name -> [x0, y0, x1, y1] drawn background area when it is larger than the comp
CU.camInside = function (comp, frames) {
  var i, b = CU.BOUNDS[comp.name] || [0, 0, comp.width, comp.height];
  for (i = 0; i < frames.length; i++) {
    var f = frames[i], hw = 960 / f[3], hh = 540 / f[3];
    if (f[1] - hw < b[0] - 1 || f[1] + hw > b[2] + 1 || f[2] - hh < b[1] - 1 || f[2] + hh > b[3] + 1) { return false; }
  }
  return true;
};
CU._camFromMotion = function (comp, motion, f0, z0) {
  var W = comp.width, H = comp.height, d = [(W - 1920) / 2, (H - 1080) / 2], C = [W / 2, H / 2], out = [], i;
  for (i = 0; i < motion.length; i++) {
    var t = motion[i][0], s = motion[i][1], tx = motion[i][2] + d[0] * (1 - s), ty = motion[i][3] + d[1] * (1 - s), z = s * z0;
    out.push([Math.min(t, comp.duration), (C[0] - s * C[0] + s * z0 * f0[0] - tx) / z, (C[1] - s * C[1] + s * z0 * f0[1] - ty) / z, z]);
  }
  if (out[out.length - 1][0] < comp.duration) { var l = out[out.length - 1]; out.push([comp.duration, l[1], l[2], l[3]]); }
  out.fromMotion = true;
  return out;
};
