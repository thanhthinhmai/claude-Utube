// Shared After Effects kit of the studio (specs/032). Moved from films/ae-crayon-test/ae/chars.jsx on 2026-11-23.
// Paths come from CU.WORK (the folder the entry script runs in); film data lives in CU.WORK/data/.
// chars.jsx: rigged cartoon people built from shape layers inside a precomp.
// A person comp is 800 x 1100; feet at (400, 1060). Faces turn toward dir (+1 right, -1 left).

CU.PW = 800; CU.PH = 1100; CU.FEET = [400, 1060];

CU.windowsExpr = function (w) {
  var s = "[", i;
  for (i = 0; i < w.length; i++) { s += (i ? "," : "") + "[" + w[i][0] + "," + w[i][1] + "]"; }
  return s + "]";
};

// expression returning true while talking (mouth flaps at ~12 fps)
CU.talkExpr = function (talk) {
  return "var w=" + CU.windowsExpr(talk || []) + "; var on=false; for (var i=0;i<w.length;i++){ if (time>=w[i][0] && time<w[i][1]) on=true; } " +
    "var f=Math.floor(time*12); var open = on && (Math.sin(f*2.3)+Math.sin(f*1.7+1))>-0.4; ";
};

CU.walkGate = function (o) { // "on" = 1 while walking (eases in and out over 0.15 s), 0 otherwise
  if (!o.walkWindow) { return "var on=1; "; }
  var a = o.walkWindow[0], b = o.walkWindow[1];
  return "var on=Math.max(0, Math.min(1, (time-" + a + ")/0.15, (" + b + "-time)/0.15)); ";
};
// Toon Boom style split: the body goes behind furniture, the arms (with hand props) go on top of it.
CU.personSplit = function (o) {
  var a = {}, b = {}, k;
  for (k in o) { if (o.hasOwnProperty(k)) { a[k] = o[k]; b[k] = o[k]; } }
  a.part = "body"; b.part = "arms";
  return [CU.person(a), CU.person(b)];
};
CU.armPose = function (pose, s, bx, top, R, dir) { var p = CU.armPts(pose, s, bx, top, R, dir); return CU.smooth(p, false, 1.1); };
CU.armPts = function (pose, s, bx, top, R, dir) {
  var S = [bx + s * 0.6 * R, top + 0.32 * R], E, H; bx = bx + 0; R = R * 1.12;
  if (pose === "handsUp") { E = [bx + s * 0.62 * R, top + 1.5 * R]; H = [bx + s * 0.16 * R + dir * 0.18 * R, top + 0.25 * R]; }
  else if (pose === "gesture") { E = [bx + s * 1.0 * R, top + 0.95 * R]; H = [bx + s * 1.65 * R, top + 0.7 * R]; }
  else if (pose === "point") { E = [bx + s * 1.05 * R, top + 0.55 * R]; H = [bx + s * 1.75 * R, top + 0.2 * R]; }
  else if (pose === "hold") { E = [bx + s * 0.75 * R, top + 1.15 * R]; H = [bx + s * 0.2 * R, top + 0.95 * R]; }
  else if (pose === "desk") { E = [bx + s * 0.8 * R, top + 1.05 * R]; H = [bx + s * 0.3 * R, top + 1.65 * R]; }
  else if (pose === "behind") { E = [bx + s * 0.62 * R, top + 0.9 * R]; H = [bx + s * 0.35 * R, top + 1.25 * R]; }
  else if (pose === "chin") { E = [bx + s * 0.75 * R, top + 1.15 * R]; H = [bx + s * 0.05 * R + dir * 0.32 * R, top + 0.14 * R]; }
  else if (pose === "write") { E = [bx + s * 0.85 * R, top + 1.05 * R]; H = [bx + s * 0.25 * R, top + 1.3 * R]; }
  else if (pose === "read") { E = [bx + s * 0.95 * R, top + 0.9 * R]; H = [bx + s * 0.8 * R + dir * 0.05 * R, top + 0.42 * R]; } // hands at the lower corners of a book held up to the face
  else if (pose === "hug") { E = [bx + s * 1.05 * R, top + 0.9 * R]; H = [bx + s * 0.89 * R + dir * 0.27 * R, top + 0.94 * R]; } // hands on the sides of a carried stack
  else if (pose === "carry") { E = [bx + s * 0.8 * R, top + 1.2 * R]; H = [bx + s * 0.35 * R, top + 1.1 * R]; }
  else if (pose === "pull") { E = [bx + s * 1.0 * R, top + 0.75 * R]; H = [bx + s * 0.9 * R, top + 0.05 * R]; }
  else if (pose === "shoulder") { E = [bx + s * 0.9 * R, top + 0.55 * R]; H = [bx + s * 1.7 * R, top + 0.25 * R]; }
  else { E = [bx + s * 0.7 * R, top + 0.95 * R]; H = [bx + s * 0.62 * R, top + 1.55 * R]; } // down
  if (pose.indexOf("to:") === 0) { var tq2 = pose.split(":"); H = [parseFloat(tq2[1]), parseFloat(tq2[2])]; E = [(S[0] + H[0]) / 2 + s * 0.25 * R, Math.max(S[1], H[1]) + 0.3 * R]; }
  if (CU.HANDY !== undefined && CU.HANDY !== null && (pose === "desk" || pose === "write" || pose === "onTable")) { H = [H[0], CU.HANDY]; E = [E[0], Math.min(E[1], CU.HANDY - 0.1 * R)]; }
  if (CU.HANDY !== undefined && CU.HANDY !== null && pose === "write") { E = [bx + s * 0.95 * R, CU.HANDY - 0.12 * R]; }   // elbow out on the desk, forearm in to the pencil
  if (pose === "pull") { E = [bx + s * 1.25 * R, top + 0.7 * R]; H = [bx + s * 1.6 * R, top + 0.25 * R]; }
  return [S, E, H];
};

// Hair: curly cloud cap. Returns path string.
CU.hairCurly = function (cx, cy, R, dir, bumps, low) {
  var pts = [], i, a0 = dir > 0 ? 160 : 198, a1 = dir > 0 ? 342 : 380, n = bumps || 13;
  for (i = 0; i <= n; i++) {
    var a = (a0 + (a1 - a0) * i / n) * Math.PI / 180, rr = R * (i % 2 ? (CU.CURL_HI || 1.2) : (CU.CURL_LO || 1.05));
    pts.push([cx + rr * Math.cos(a) - dir * 0.08 * R, cy + rr * Math.sin(a) - 0.06 * R]);
  }
  // hairline across the forehead (wavy), from the last outer point back to the first
  var hl = low || 0.42, m = 7;
  for (i = 1; i < m; i++) {
    var x = pts[n][0] + (pts[0][0] - pts[n][0]) * i / m;
    var y = cy - hl * R + (i % 2 ? -0.07 : 0.03) * R - Math.sin(Math.PI * i / m) * 0.18 * R;
    if (dir > 0 && i > m / 2) { y += (i - m / 2) * 0.14 * R; }
    if (dir < 0 && i < m / 2) { y += (m / 2 - i) * 0.14 * R; }
    pts.push([x, y]);
  }
  return CU.smooth(pts, true, 1);
};

CU.hairShort = function (cx, cy, R, dir) {
  var b = -dir;
  return "M " + (cx + b * 1.0 * R) + " " + (cy + 0.15 * R) +
    " C " + (cx + b * 1.12 * R) + " " + (cy - 0.9 * R) + " " + (cx - b * 0.2 * R) + " " + (cy - 1.35 * R) + " " + (cx - b * 0.85 * R) + " " + (cy - 0.62 * R) +
    " C " + (cx - b * 0.6 * R) + " " + (cy - 0.72 * R) + " " + (cx - b * 0.1 * R) + " " + (cy - 0.62 * R) + " " + (cx + b * 0.2 * R) + " " + (cy - 0.5 * R) +
    " C " + (cx + b * 0.5 * R) + " " + (cy - 0.4 * R) + " " + (cx + b * 0.62 * R) + " " + (cy - 0.15 * R) + " " + (cx + b * 0.72 * R) + " " + (cy + 0.12 * R) +
    " C " + (cx + b * 0.85 * R) + " " + (cy + 0.2 * R) + " " + (cx + b * 0.95 * R) + " " + (cy + 0.2 * R) + " " + (cx + b * 1.0 * R) + " " + (cy + 0.15 * R) + " Z";
};

CU.hairBobFront = function (cx, cy, R, dir) {
  var b = -dir;
  return "M " + (cx + b * 1.08 * R) + " " + (cy + 0.55 * R) +
    " C " + (cx + b * 1.25 * R) + " " + (cy - 0.6 * R) + " " + (cx + b * 0.6 * R) + " " + (cy - 1.3 * R) + " " + (cx - b * 0.2 * R) + " " + (cy - 1.12 * R) +
    " C " + (cx - b * 0.85 * R) + " " + (cy - 1.0 * R) + " " + (cx - b * 1.15 * R) + " " + (cy - 0.4 * R) + " " + (cx - b * 1.02 * R) + " " + (cy + 0.1 * R) +
    " C " + (cx - b * 0.92 * R) + " " + (cy - 0.3 * R) + " " + (cx - b * 0.55 * R) + " " + (cy - 0.62 * R) + " " + (cx - b * 0.05 * R) + " " + (cy - 0.66 * R) +
    " C " + (cx + b * 0.35 * R) + " " + (cy - 0.6 * R) + " " + (cx + b * 0.62 * R) + " " + (cy - 0.2 * R) + " " + (cx + b * 0.72 * R) + " " + (cy + 0.55 * R) +
    " C " + (cx + b * 0.85 * R) + " " + (cy + 0.62 * R) + " " + (cx + b * 1.0 * R) + " " + (cy + 0.62 * R) + " " + (cx + b * 1.08 * R) + " " + (cy + 0.55 * R) + " Z";
};

// Long hair, front layer: the crown of the same mass as the back hair (filled just inside its outline, so the two read as
// one head of hair), and the hairline over the forehead. Returns [fill path, hairline path].
CU.hairLongFront = function (cx, cy, R, dir) {
  var b = -dir, k = 0.955;
  function P(x, y) { return (cx + (x - cx) * k) + " " + (cy + (y - cy) * k); }
  var top = "M " + P(cx + b * 1.15 * R, cy + 0.6 * R) +
    " C " + P(cx + b * 1.45 * R, cy - 0.7 * R) + " " + P(cx + b * 0.6 * R, cy - 1.38 * R) + " " + P(cx - b * 0.2 * R, cy - 1.16 * R) +
    " C " + P(cx - b * 1.05 * R, cy - 1.0 * R) + " " + P(cx - b * 1.3 * R, cy - 0.1 * R) + " " + P(cx - b * 1.15 * R, cy + 0.7 * R);
  var line = " C " + (cx - b * 0.95 * R) + " " + (cy + 0.1 * R) + " " + (cx - b * 0.72 * R) + " " + (cy - 0.5 * R) + " " + (cx - b * 0.1 * R) + " " + (cy - 0.62 * R) +
    " C " + (cx + b * 0.45 * R) + " " + (cy - 0.6 * R) + " " + (cx + b * 0.85 * R) + " " + (cy - 0.15 * R) + " " + (cx + b * 0.9 * R) + " " + (cy + 0.55 * R);
  var start = (cx - b * 1.15 * R * k) + " " + (cy + 0.7 * R * k);
  return [top + line + " Z", "M " + start + line];
};
// Long hair under a hat: the mass starts below the brim (the hat covers the crown), then falls past the jaw on both sides.
CU.hairLongBackUnderHat = function (cx, cy, R, dir) {
  var b = -dir, y2 = cy + 1.5 * R, yb = cy - 0.32 * R;
  return "M " + (cx + b * 1.08 * R) + " " + yb +
    " Q " + (cx + b * 1.3 * R) + " " + (cy + 0.2 * R) + " " + (cx + b * 1.18 * R) + " " + (cy + 0.9 * R) +
    " Q " + (cx + b * 1.35 * R) + " " + (y2 - 0.1 * R) + " " + (cx + b * 0.9 * R) + " " + (y2 - 0.1 * R) +
    " L " + (cx - b * 0.4 * R) + " " + (y2 - 0.1 * R) +
    " Q " + (cx - b * 0.6 * R) + " " + (y2 + 0.15 * R) + " " + (cx - b * 1.05 * R) + " " + y2 +
    " Q " + (cx - b * 1.3 * R) + " " + (cy + 1.1 * R) + " " + (cx - b * 1.15 * R) + " " + (cy + 0.5 * R) +
    " Q " + (cx - b * 1.22 * R) + " " + (cy + 0.0 * R) + " " + (cx - b * 1.02 * R) + " " + yb + " Z";
};
CU.hairLongBack = function (cx, cy, R, dir) {
  var b = -dir, y2 = cy + 1.5 * R;
  return "M " + (cx + b * 1.15 * R) + " " + (cy + 0.6 * R) +
    " C " + (cx + b * 1.45 * R) + " " + (cy - 0.7 * R) + " " + (cx + b * 0.6 * R) + " " + (cy - 1.38 * R) + " " + (cx - b * 0.2 * R) + " " + (cy - 1.16 * R) +
    " C " + (cx - b * 1.05 * R) + " " + (cy - 1.0 * R) + " " + (cx - b * 1.3 * R) + " " + (cy - 0.1 * R) + " " + (cx - b * 1.15 * R) + " " + (cy + 0.7 * R) +
    " Q " + (cx - b * 1.3 * R) + " " + (cy + 1.1 * R) + " " + (cx - b * 1.05 * R) + " " + y2 +
    " Q " + (cx - b * 0.6 * R) + " " + (y2 + 0.15 * R) + " " + (cx - b * 0.4 * R) + " " + (y2 - 0.1 * R) +
    " L " + (cx + b * 0.9 * R) + " " + (y2 - 0.1 * R) +
    " Q " + (cx + b * 1.35 * R) + " " + (y2 + 0.05 * R) + " " + (cx + b * 1.3 * R) + " " + (cy + 1.0 * R) +
    " Q " + (cx + b * 1.15 * R) + " " + (cy + 0.8 * R) + " " + (cx + b * 1.15 * R) + " " + (cy + 0.6 * R) + " Z";
};
CU.hairSides = function (cx, cy, R, dir) { // bald crown: hair band around the back of the head, from temple height to the nape
  var a0 = dir > 0 ? 225 : -45, a1 = dir > 0 ? 145 : 35, rr = R * 1.04;
  var d = CU.arc(cx, cy, rr, a0, a1, true);
  var sx = cx + rr * Math.cos(a0 * Math.PI / 180), sy = cy + rr * Math.sin(a0 * Math.PI / 180);
  d += " Q " + (cx - dir * 0.5 * R) + " " + (cy + 0.1 * R) + " " + sx + " " + sy + " Z";
  return d;
};
CU.hairBobBack = function (cx, cy, R, dir) {
  var b = -dir;
  return "M " + (cx + b * 1.15 * R) + " " + (cy + 0.75 * R) +
    " C " + (cx + b * 1.4 * R) + " " + (cy - 0.6 * R) + " " + (cx + b * 0.6 * R) + " " + (cy - 1.35 * R) + " " + (cx - b * 0.2 * R) + " " + (cy - 1.15 * R) +
    " C " + (cx - b * 1.0 * R) + " " + (cy - 1.0 * R) + " " + (cx - b * 1.25 * R) + " " + (cy - 0.2 * R) + " " + (cx - b * 1.1 * R) + " " + (cy + 0.55 * R) +
    " L " + (cx + b * 1.15 * R) + " " + (cy + 0.75 * R) + " Z";
};

CU.hairBack = function (cx, cy, R, dir) { // back 3/4 view: hair over top and back, face toward dir
  var rr = R * 1.03, a0 = dir > 0 ? -40 : 220, a1 = dir > 0 ? -228 : 408;
  var d = CU.arc(cx, cy, rr, a0, a1, true);
  var sx = cx + rr * Math.cos(a0 * Math.PI / 180), sy = cy + rr * Math.sin(a0 * Math.PI / 180);
  d += " C " + (cx - dir * 0.35 * R) + " " + (cy + 0.75 * R) + " " + (cx + dir * 0.05 * R) + " " + (cy + 0.55 * R) + " " + (cx + dir * 0.12 * R) + " " + (cy + 0.05 * R);
  d += " C " + (cx + dir * 0.18 * R) + " " + (cy - 0.45 * R) + " " + (cx + dir * 0.55 * R) + " " + (cy - 0.6 * R) + " " + sx + " " + sy + " Z";
  return d;
};
// Fluffy cloud (old woman's hair mass behind the head): bumpy closed outline around an ellipse.
CU.hairCloud = function (cx, cy, rx, ry, n) {
  var pts = [], i;
  for (i = 0; i < n; i++) { var a = 2 * Math.PI * i / n, k = i % 2 ? 1.0 : 0.9; pts.push([cx + rx * k * Math.cos(a), cy + ry * k * Math.sin(a)]); }
  return CU.smooth(pts, true, 1);
};
// Curly hair seen from behind (3/4 back): bumpy mass over top, back and nape; cheek and ear free on the facing side.
CU.hairCurlyBack = function (cx, cy, R, dir) {
  var pts = [], i, n = 15, a0 = dir > 0 ? -35 : 215, a1 = dir > 0 ? -235 : 415;
  for (i = 0; i <= n; i++) { var a = (a0 + (a1 - a0) * i / n) * Math.PI / 180, rr = R * (i % 2 ? 1.16 : 1.03); pts.push([cx + rr * Math.cos(a), cy + rr * Math.sin(a)]); }
  pts.push([cx + dir * 0.25 * R, cy + 0.92 * R]); pts.push([cx + dir * 0.52 * R, cy + 0.5 * R]); pts.push([cx + dir * 0.6 * R, cy + 0.02 * R]);
  pts.push([cx + dir * 0.68 * R, cy - 0.4 * R]); pts.push([cx + dir * 0.82 * R, cy - 0.58 * R]);
  return CU.smooth(pts, true, 1);
};
CU.hairBackOld = function (cx, cy, R, dir) {
  var rr = R * 1.04, a0 = dir > 0 ? 10 : 170, a1 = dir > 0 ? -235 : 415, d = CU.arc(cx, cy, rr, a0, a1, true);
  var ex = cx + rr * Math.cos(a1 * Math.PI / 180), ey = cy + rr * Math.sin(a1 * Math.PI / 180);
  var sx = cx + rr * Math.cos(a0 * Math.PI / 180), sy = cy + rr * Math.sin(a0 * Math.PI / 180);
  d += " C " + (cx - dir * 0.2 * R) + " " + (cy + 0.55 * R) + " " + (cx + dir * 0.55 * R) + " " + (cy + 0.1 * R) + " " + (cx + dir * 0.5 * R) + " " + (cy - 0.35 * R);
  d += " C " + (cx + dir * 0.62 * R) + " " + (cy - 0.2 * R) + " " + (cx + dir * 0.9 * R) + " " + (cy - 0.05 * R) + " " + sx + " " + sy + " Z";
  return d;
};

CU.capHat = function (cx, cy, R, dir) { // newsboy cap
  return "M " + (cx - 1.05 * R) + " " + (cy - 0.3 * R) +
    " C " + (cx - 1.1 * R) + " " + (cy - 1.1 * R) + " " + (cx + 0.9 * R) + " " + (cy - 1.25 * R) + " " + (cx + 1.15 * R) + " " + (cy - 0.55 * R) +
    " C " + (cx + 1.45 * R * (dir > 0 ? 1.12 : 0.85)) + " " + (cy - 0.45 * R) + " " + (cx + 1.35 * R) + " " + (cy - 0.22 * R) + " " + (cx + 1.0 * R) + " " + (cy - 0.25 * R) +
    " C " + (cx + 0.4 * R) + " " + (cy - 0.32 * R) + " " + (cx - 0.5 * R) + " " + (cy - 0.15 * R) + " " + (cx - 1.05 * R) + " " + (cy - 0.3 * R) + " Z";
};

// Build a person precomp. o: {name,dur,R,skin,hair,hairColor,glasses,body,bodyShade,collar,dir,view,
//   mouth,brows,talk,blinks,arms:{l:[[t,pose]],r:[[t,pose]]},legs,bob,rim,lens,headTurn,headNod}
CU.person = function (o) {
  CU.HANDY = o.handY;
  if (o.sit) { o.legs = false; }
  var c = CU.comp("P " + o.name + (o.part === "arms" ? " arms" : ""), o.dur, CU.PW, o.sit ? CU.PH + 700 : CU.PH);
  var armsSave = o.arms; if (o.part === "body") { o.arms = false; }
  var R = o.R || 100, dir = o.dir || 1, fx = CU.FEET[0], fy = CU.FEET[1];
  var legLen = (o.legs === false) ? 0 : (o.legLen || 1.25 * R);
  var bodyH = o.bodyH || 1.85 * R, top = fy - legLen - bodyH, bx = fx;
  var hx = bx + dir * 0.06 * R, hy = top - 0.62 * R;
  var skin = CU.hex(o.skin || "#efc8a8"), skinSh = CU.shade(skin, 0.86);
  var body = CU.hex(o.body || "#7d3a3a");
  var ink = o.ink || CU.INK, sw = o.sw || CU.SW;
  var root = CU.nul(c, "ROOT", [fx, fy]);
  var layers = [];

  // legs
  if (legLen > 0) {
    var lgs = [[-1, "leg l"], [1, "leg r"]], li;
    for (li = 0; li < 2; li++) {
      var ls = lgs[li][0], hipX = bx + ls * 0.22 * R, hipY = top + bodyH - 10;
      var Lg = CU.layer(c, lgs[li][1], [hipX, hipY]), r = CU.root(Lg);
      CU.path(r, "M " + hipX + " " + hipY + " Q " + (hipX + ls * 0.03 * R) + " " + (fy - legLen / 2) + " " + (hipX - ls * 0.01 * R) + " " + fy, { stroke: ink, sw: sw * 1.6 });
      if (o.walk) { CU.rot(Lg).expression = CU.walkGate(o) + (ls * 14) + "*Math.sin(time*" + (o.walk * 2 * Math.PI) + ")*on"; }
      if (o.crouch) {
        var lp = CU.inner(r.property(1)).property(1).property("ADBE Vector Shape"), cq;
        for (cq = 0; cq < o.crouch.length; cq++) {
          var am = o.crouch[cq][1], drop = am * 0.55 * legLen, hy3 = hipY + drop, kx3 = hipX + ls * (0.1 + 0.35 * am) * R, ky3 = (hy3 + fy) / 2 - am * 0.05 * R;
          lp.setValueAtTime(o.crouch[cq][0], CU.parse("M " + hipX + " " + hy3 + " Q " + kx3 + " " + ky3 + " " + (hipX - ls * 0.01 * R) + " " + fy)[0]);
        }
        CU.ease(lp, 60);
      }
      layers.push(Lg);
    }
  }
  var bodySh = o.bodyShade ? CU.hex(o.bodyShade) : CU.shade(CU.hex(o.body || "#7d3a3a"), 0.8);
  if (o.sit) { // hips on the seat at the feet point: contact shadow, thighs over the seat edge, shins down to the floor
    var Sh = CU.layer(c, "seat contact shadow"); CU.ell(CU.root(Sh), bx, fy - 0.02 * R, 2.0 * R, 0.3 * R, { fill: "#000000", fo: 30 });
    layers.push(Sh);
    var kd = (o.sit.knee || 0.45) * R, fd = (o.sit.foot || 1.6) * R, sl, sides2 = [-1, 1];
    for (sl = 0; sl < 2; sl++) {
      var sx2 = sides2[sl], hx2 = bx + sx2 * 0.28 * R, kx = hx2 + sx2 * 0.16 * R, ky = fy + kd;
      var Lsit = CU.layer(c, sx2 < 0 ? "leg l" : "leg r"), rls = CU.root(Lsit);
      if (o.sit.side) { // turned 3/4: thighs lie toward dir on the seat, shins drop from the knees at the seat front
        var hx3 = bx + sx2 * 0.18 * R, kx3 = hx3 + dir * o.sit.side * R, ky3 = fy + (sx2 * dir > 0 ? 0.16 : 0.04) * R, tw = 0.44 * R;
        var thigh = "M " + hx3 + " " + (fy - 0.1 * R) + " L " + kx3 + " " + ky3;
        CU.path(rls, "M " + kx3 + " " + ky3 + " Q " + (kx3 + dir * 0.04 * R) + " " + (ky3 + (fd - kd) * 0.5) + " " + (kx3 - dir * 0.05 * R) + " " + (fy + fd), { stroke: ink, sw: sw * 1.6 });
        CU.path(rls, thigh, { stroke: ink, sw: tw + 2 * sw * 0.9 }); CU.path(rls, thigh, { stroke: o.legColor || bodySh, sw: tw });
        CU.ell(rls, kx3, ky3, tw + sw * 0.9, tw + sw * 0.9, { fill: o.legColor || bodySh, stroke: ink, sw: sw * 0.9 });
        layers.push(Lsit); continue;
      }
      // thigh: a short foreshortened trouser shape lying on the seat, from under the body to the seat's front edge
      CU.path(rls, "M " + (hx2 - 0.2 * R) + " " + (fy - 0.12 * R) + " L " + (hx2 + 0.2 * R) + " " + (fy - 0.12 * R) + " Q " + (kx + 0.24 * R) + " " + (ky - 0.15 * R) + " " + (kx + 0.18 * R) + " " + (ky + 0.06 * R) +
        " Q " + kx + " " + (ky + 0.14 * R) + " " + (kx - 0.18 * R) + " " + (ky + 0.06 * R) + " Q " + (kx - 0.24 * R) + " " + (ky - 0.15 * R) + " " + (hx2 - 0.2 * R) + " " + (fy - 0.12 * R) + " Z", { fill: o.legColor || bodySh, stroke: ink, sw: sw * 0.9 });
      // shin: from the knee at the seat edge down to the floor, tucked slightly back under the seat
      CU.path(rls, "M " + kx + " " + (ky + 0.08 * R) + " Q " + (kx + sx2 * 0.02 * R) + " " + (ky + (fd - kd) * 0.55) + " " + (kx - sx2 * 0.06 * R) + " " + (fy + fd), { stroke: ink, sw: sw * 1.6 });
      layers.push(Lsit);
    }
  }
  // back hair (bob)
  if (o.hair === "bob" || o.hair === "long") {
    var Hb = CU.layer(c, "hairBack", [hx, hy + 0.9 * R]);
    CU.path(CU.root(Hb), o.hair === "long" ? (o.hat ? CU.hairLongBackUnderHat(hx, hy, R, dir) : CU.hairLongBack(hx, hy, R, dir)) : CU.hairBobBack(hx, hy, R, dir), { fill: o.hairColor || "#2b2b2b", stroke: ink, sw: sw });
    layers.push(Hb);
  }
  var HbG = (o.hair === "bob" || o.hair === "long") ? Hb : null;   // back hair turns with the head (parented below)
  if (o.hair === "granny") { HbG = null; } if (o.hair === "granny") { // fluffy mass framing the face down to the chin (parented to the head below)
    HbG = CU.layer(c, "hairBack", [hx, hy + 0.9 * R]);
    CU.path(CU.root(HbG), CU.hairCloud(hx - dir * 0.12 * R, hy + 0.12 * R, 1.36 * R, 1.22 * R, 22), { fill: o.hairColor || "#e9e9e9", stroke: ink, sw: sw });
    CU.path(CU.root(HbG), CU.squiggle(hx - dir * 1.05 * R, hy + 0.5 * R, 0.3 * R, 5, 3) + CU.squiggle(hx + dir * 0.75 * R, hy + 0.6 * R, 0.3 * R, 5, 4), { stroke: CU.shade(CU.hex(o.hairColor || "#e9e9e9"), 0.75), sw: sw * 0.6 });
    layers.push(HbG);
  }
  // body (bean)
  var B = CU.layer(c, "body", [bx, top + bodyH]), rb = CU.root(B);
  var bw = (o.bodyW || 1.6) * R, bwb = (o.bodyWB || 1.9) * R * (o.sit ? 1.06 : 1); // a seated body spreads a little
  var bodyD = "M " + (bx - bw / 2) + " " + (top + 0.25 * R) +
    " C " + (bx - bw / 2) + " " + (top - 0.05 * R) + " " + (bx + bw / 2) + " " + (top - 0.05 * R) + " " + (bx + bw / 2) + " " + (top + 0.25 * R) +
    " C " + (bx + bwb / 2 + 0.05 * R) + " " + (top + 0.8 * R) + " " + (bx + bwb / 2) + " " + (top + bodyH - 0.1 * R) + " " + (bx + bwb / 2 - 0.25 * R) + " " + (top + bodyH) +
    " L " + (bx - bwb / 2 + 0.25 * R) + " " + (top + bodyH) +
    " C " + (bx - bwb / 2) + " " + (top + bodyH - 0.1 * R) + " " + (bx - bwb / 2 - 0.05 * R) + " " + (top + 0.8 * R) + " " + (bx - bw / 2) + " " + (top + 0.25 * R) + " Z";
  CU.path(rb, bodyD, { fill: body, stroke: ink, sw: sw });
  // body shade on the side away from the light (opposite dir)
  var sx = -dir;
  CU.path(rb, "M " + (bx + sx * bw / 2) + " " + (top + 0.28 * R) + " C " + (bx + sx * (bwb / 2 + 0.05 * R)) + " " + (top + 0.8 * R) + " " + (bx + sx * bwb / 2) + " " + (top + bodyH - 0.1 * R) + " " + (bx + sx * (bwb / 2 - 0.25 * R)) + " " + (top + bodyH - sw) +
    " L " + (bx + sx * 0.2 * R) + " " + (top + bodyH - sw) + " C " + (bx + sx * 0.35 * R) + " " + (top + 1.0 * R) + " " + (bx + sx * 0.3 * R) + " " + (top + 0.5 * R) + " " + (bx + sx * bw / 2) + " " + (top + 0.28 * R) + " Z", { fill: bodySh });
  if (o.rim) { // back light rim on one edge
    CU.path(rb, "M " + (bx + dir * bw / 2) + " " + (top + 0.3 * R) + " C " + (bx + dir * (bwb / 2 + 0.05 * R)) + " " + (top + 0.8 * R) + " " + (bx + dir * bwb / 2) + " " + (top + bodyH - 0.15 * R) + " " + (bx + dir * (bwb / 2 - 0.25 * R)) + " " + (top + bodyH - 0.05 * R), { stroke: o.rim, sw: sw * 1.6 });
  }
  if (o.rim2) {
    CU.path(rb, "M " + (bx - dir * bw / 2) + " " + (top + 0.3 * R) + " C " + (bx - dir * (bwb / 2 + 0.05 * R)) + " " + (top + 0.8 * R) + " " + (bx - dir * bwb / 2) + " " + (top + bodyH - 0.15 * R) + " " + (bx - dir * (bwb / 2 - 0.25 * R)) + " " + (top + bodyH - 0.05 * R), { stroke: o.rim2, sw: sw * 1.6 });
  }
  if (o.collar === "white") {
    CU.path(rb, "M " + (bx - 0.32 * R) + " " + (top + 0.02 * R) + " L " + (bx - 0.05 * R) + " " + (top + 0.28 * R) + " L " + (bx - 0.02 * R) + " " + (top + 0.05 * R) + " Z", { fill: "#ffffff", stroke: ink, sw: sw * 0.8 });
    CU.path(rb, "M " + (bx + 0.34 * R) + " " + (top + 0.02 * R) + " L " + (bx + 0.08 * R) + " " + (top + 0.3 * R) + " L " + (bx + 0.02 * R) + " " + (top + 0.05 * R) + " Z", { fill: "#ffffff", stroke: ink, sw: sw * 0.8 });
  }
  if (o.collar === "tie") { // suit: white shirt V, red tie, lapels
    CU.path(rb, "M " + (bx - 0.28 * R) + " " + (top + 0.02 * R) + " L " + (bx) + " " + (top + 0.75 * R) + " L " + (bx + 0.28 * R) + " " + (top + 0.02 * R) + " Z", { fill: "#f2f2f2", stroke: ink, sw: sw * 0.8 });
    CU.path(rb, "M " + (bx - 0.06 * R) + " " + (top + 0.08 * R) + " L " + (bx + 0.06 * R) + " " + (top + 0.08 * R) + " L " + (bx + 0.09 * R) + " " + (top + 0.6 * R) + " L " + bx + " " + (top + 0.72 * R) + " L " + (bx - 0.09 * R) + " " + (top + 0.6 * R) + " Z", { fill: "#a3232b", stroke: ink, sw: sw * 0.7 });
    CU.path(rb, "M " + (bx - 0.33 * R) + " " + (top + 0.05 * R) + " L " + (bx - 0.05 * R) + " " + (top + 0.85 * R), { stroke: ink, sw: sw * 0.8 });
    CU.path(rb, "M " + (bx + 0.33 * R) + " " + (top + 0.05 * R) + " L " + (bx + 0.05 * R) + " " + (top + 0.85 * R), { stroke: ink, sw: sw * 0.8 });
  }
  if (o.collar === "polo") {
    CU.path(rb, "M " + (bx - 0.25 * R) + " " + (top + 0.0 * R) + " L " + (bx) + " " + (top + 0.22 * R) + " L " + (bx + 0.25 * R) + " " + (top + 0.0 * R), { stroke: ink, sw: sw * 0.8 });
    CU.ell(rb, bx, top + 0.38 * R, 6, 6, { fill: ink }); CU.ell(rb, bx, top + 0.55 * R, 6, 6, { fill: ink });
  }
  if (o.collar === "turtle") { // turtleneck: a ribbed band showing under the chin
    var tc = CU.shade(body, 0.88), ty0 = top + 0.18 * R;
    CU.path(rb, "M " + (bx - 0.5 * R) + " " + ty0 + " Q " + bx + " " + (ty0 + 0.62 * R) + " " + (bx + 0.5 * R) + " " + ty0 + " L " + (bx + 0.46 * R) + " " + (ty0 - 0.1 * R) + " Q " + bx + " " + (ty0 + 0.4 * R) + " " + (bx - 0.46 * R) + " " + (ty0 - 0.1 * R) + " Z", { fill: tc, stroke: ink, sw: sw * 0.8 });
    var tq2, td = ""; for (tq2 = -3; tq2 <= 3; tq2++) { var tx2 = bx + tq2 * 0.11 * R, tyy = ty0 + 0.36 * R - Math.abs(tq2) * 0.045 * R; td += "M " + tx2 + " " + (tyy - 0.02 * R) + " L " + (tx2 + tq2 * 0.01 * R) + " " + (tyy + 0.1 * R) + " "; }
    CU.path(rb, td, { stroke: CU.shade(body, 0.6), sw: sw * 0.5 });
  }
  if (o.outfit === "apron") {
    CU.path(rb, "M " + (bx - 0.45 * R) + " " + (top + 0.55 * R) + " L " + (bx + 0.45 * R) + " " + (top + 0.55 * R) + " L " + (bx + 0.62 * R) + " " + (top + bodyH - sw) + " L " + (bx - 0.62 * R) + " " + (top + bodyH - sw) + " Z", { fill: o.apron || "#7a5434", stroke: ink, sw: sw * 0.8 });
    CU.path(rb, "M " + (bx - 0.4 * R) + " " + (top + 0.58 * R) + " L " + (bx - 0.5 * R) + " " + (top + 0.0 * R) + " M " + (bx + 0.4 * R) + " " + (top + 0.58 * R) + " L " + (bx + 0.5 * R) + " " + (top + 0.0 * R), { stroke: o.apron || "#7a5434", sw: sw * 2.2 });
    CU.rect(rb, bx - 0.25 * R, top + 0.95 * R, 0.5 * R, 0.3 * R, 4, { fill: CU.shade(o.apron || "#7a5434", 0.8), stroke: ink, sw: sw * 0.6 });
  }
  if (o.outfit === "vest") {
    CU.path(rb, "M " + (bx - bw / 2 + 4) + " " + (top + 0.25 * R) + " L " + (bx - 0.12 * R) + " " + (top + 0.1 * R) + " L " + (bx - 0.1 * R) + " " + (top + bodyH - sw) + " L " + (bx - bwb / 2 + 0.28 * R) + " " + (top + bodyH - sw) + " Z", { fill: "#b6d14a", stroke: ink, sw: sw * 0.7 });
    CU.path(rb, "M " + (bx + bw / 2 - 4) + " " + (top + 0.25 * R) + " L " + (bx + 0.12 * R) + " " + (top + 0.1 * R) + " L " + (bx + 0.1 * R) + " " + (top + bodyH - sw) + " L " + (bx + bwb / 2 - 0.28 * R) + " " + (top + bodyH - sw) + " Z", { fill: "#b6d14a", stroke: ink, sw: sw * 0.7 });
    CU.path(rb, "M " + (bx - bwb / 2 + 0.1 * R) + " " + (top + 1.1 * R) + " L " + (bx + bwb / 2 - 0.1 * R) + " " + (top + 1.1 * R) + " M " + (bx - bwb / 2 + 0.1 * R) + " " + (top + 1.35 * R) + " L " + (bx + bwb / 2 - 0.1 * R) + " " + (top + 1.35 * R), { stroke: "#d8d8d8", sw: sw * 1.6 });
  }
  if (o.outfit === "labcoat" || o.outfit === "jacket" || o.outfit === "cardigan") {
    var oc = o.outfit === "labcoat" ? "#f4f4f2" : (o.outfit === "jacket" ? (o.jacket || "#4b4d52") : (o.jacket || "#c6943f"));
    var inner = o.inner || (o.outfit === "cardigan" ? "#d9d9d6" : "#7a3436");
    CU.path(rb, "M " + (bx - 0.22 * R) + " " + (top + 0.02 * R) + " L " + (bx + 0.22 * R) + " " + (top + 0.02 * R) + " L " + (bx + 0.16 * R) + " " + (top + bodyH - sw) + " L " + (bx - 0.16 * R) + " " + (top + bodyH - sw) + " Z", { fill: inner, stroke: ink, sw: sw * 0.6 });
    if (o.tie) { CU.path(rb, "M " + (bx - 0.05 * R) + " " + (top + 0.08 * R) + " L " + (bx + 0.05 * R) + " " + (top + 0.08 * R) + " L " + (bx + 0.07 * R) + " " + (top + 0.75 * R) + " L " + bx + " " + (top + 0.85 * R) + " L " + (bx - 0.07 * R) + " " + (top + 0.75 * R) + " Z", { fill: o.tie, stroke: ink, sw: sw * 0.6 }); }
    CU.path(rb, "M " + (bx - bw / 2 + 2) + " " + (top + 0.22 * R) + " C " + (bx - bw / 2 + 0.1 * R) + " " + (top - 0.02 * R) + " " + (bx - 0.25 * R) + " " + (top - 0.02 * R) + " " + (bx - 0.2 * R) + " " + (top + 0.05 * R) + " L " + (bx - 0.12 * R) + " " + (top + bodyH - sw) + " L " + (bx - bwb / 2 + 0.25 * R) + " " + (top + bodyH - sw) + " C " + (bx - bwb / 2) + " " + (top + bodyH - 0.1 * R) + " " + (bx - bwb / 2 - 0.05 * R) + " " + (top + 0.8 * R) + " " + (bx - bw / 2 + 2) + " " + (top + 0.22 * R) + " Z", { fill: oc, stroke: ink, sw: sw * 0.8 });
    CU.path(rb, "M " + (bx + bw / 2 - 2) + " " + (top + 0.22 * R) + " C " + (bx + bw / 2 - 0.1 * R) + " " + (top - 0.02 * R) + " " + (bx + 0.25 * R) + " " + (top - 0.02 * R) + " " + (bx + 0.2 * R) + " " + (top + 0.05 * R) + " L " + (bx + 0.12 * R) + " " + (top + bodyH - sw) + " L " + (bx + bwb / 2 - 0.25 * R) + " " + (top + bodyH - sw) + " C " + (bx + bwb / 2) + " " + (top + bodyH - 0.1 * R) + " " + (bx + bwb / 2 + 0.05 * R) + " " + (top + 0.8 * R) + " " + (bx + bw / 2 - 2) + " " + (top + 0.22 * R) + " Z", { fill: oc, stroke: ink, sw: sw * 0.8 });
    CU.path(rb, "M " + (bx - 0.2 * R) + " " + (top + 0.05 * R) + " L " + (bx - 0.02 * R) + " " + (top + 0.45 * R) + " M " + (bx + 0.2 * R) + " " + (top + 0.05 * R) + " L " + (bx + 0.02 * R) + " " + (top + 0.45 * R), { stroke: ink, sw: sw * 0.7 });
  }
  if (o.bag) { // shoulder strap
    CU.path(rb, "M " + (bx - 0.55 * R) + " " + (top + 0.1 * R) + " L " + (bx + 0.6 * R) + " " + (top + 1.2 * R), { stroke: "#5b4330", sw: sw * 2 });
  }
  layers.push(B);

  // head
  var Hd = CU.layer(c, "head", [hx, hy + 0.9 * R]), rh = CU.root(Hd);
  var dark = o.dark;
  CU.ell(rh, hx, hy, 2 * R, 2 * R, { fill: skin, stroke: ink, sw: sw, name: "skull" });
  if (o.backlit) {
    CU.ell(rh, hx, hy, 2 * R - sw, 2 * R - sw, { fill: o.backlit, name: "rimfill" });
    CU.ell(rh, hx + dir * 0.03 * R, hy - 0.04 * R, 1.72 * R, 1.98 * R, { fill: skin, name: "face" });
  } else if (o.rimTop) {
    CU.path(rh, CU.crescent(hx, hy, R - sw / 2, -dir * 0.12 * R, 0.16 * R, R * 1.0), { fill: o.rimTop, name: "rimtop" });
  } else {
    CU.path(rh, CU.crescent(hx, hy, R - sw / 2, dir * 0.28 * R, -0.24 * R, R * 1.02), { fill: skinSh, name: "shade" });
  }
  if (o.view === "back") {
    // back of the head: hair covers most; a sliver of cheek with one eye at the facing edge
    if (o.hair === "curly") { CU.path(rh, CU.hairCurlyBack(hx, hy, R, dir), { fill: o.hairColor || "#4a3526", stroke: ink, sw: sw, name: "hair" }); }
    else if (o.hair !== "none") { CU.path(rh, CU.hairBack(hx, hy, R, dir), { fill: o.hairColor || "#2b2b2b", stroke: ink, sw: sw, name: "hair" }); }
    if (o.hair === "curly") { // ear at the hair edge, glasses temple running to the facing edge
      CU.ell(rh, hx + dir * 0.62 * R, hy + 0.1 * R, 0.18 * R, 0.28 * R, { fill: skin, stroke: ink, sw: sw * 0.8, name: "ear" });
      if (o.glasses) { CU.path(rh, "M " + (hx + dir * 0.6 * R) + " " + (hy - 0.06 * R) + " L " + (hx + dir * 0.98 * R) + " " + (hy - 0.12 * R), { stroke: ink, sw: sw * 0.6, name: "temple" });
        CU.path(rh, "M " + (hx + dir * 0.96 * R) + " " + (hy - 0.26 * R) + " L " + (hx + dir * 1.04 * R) + " " + (hy - 0.24 * R) + " L " + (hx + dir * 1.04 * R) + " " + (hy + 0.02 * R) + " L " + (hx + dir * 0.98 * R) + " " + (hy + 0.02 * R), { stroke: ink, sw: sw * 0.6, name: "lens edge" }); }
    }
    if (o.backFace === "awe") { // bald back 3/4: brow and open mouth breaking the outline at the facing edge
      CU.path(rh, "M " + (hx + dir * 0.62 * R) + " " + (hy - 0.42 * R) + " Q " + (hx + dir * 0.74 * R) + " " + (hy - 0.52 * R) + " " + (hx + dir * 0.86 * R) + " " + (hy - 0.4 * R), { stroke: ink, sw: sw * 0.8, name: "brow" });
      var mo2 = CU.path(rh, "M " + (hx + dir * 0.9 * R) + " " + (hy + 0.12 * R) + " Q " + (hx + dir * 1.12 * R) + " " + (hy + 0.1 * R) + " " + (hx + dir * 1.1 * R) + " " + (hy + 0.26 * R) +
        " Q " + (hx + dir * 1.12 * R) + " " + (hy + 0.42 * R) + " " + (hx + dir * 0.9 * R) + " " + (hy + 0.38 * R) + " Q " + (hx + dir * 0.98 * R) + " " + (hy + 0.25 * R) + " " + (hx + dir * 0.9 * R) + " " + (hy + 0.12 * R) + " Z", { fill: "#e07c7c", stroke: ink, sw: sw * 0.8, name: "mouthO" });
      if (o.openAt) { CU.xf(rh.property("mouthO")).property("ADBE Vector Scale").expression = "time<" + o.openAt[0] + " ? [60,40] : (time<" + (o.openAt[0] + 0.25) + " ? [60+40*(time-" + o.openAt[0] + ")/0.25, 40+60*(time-" + o.openAt[0] + ")/0.25] : [100,100]);"; 
        CU.xf(rh.property("mouthO")).property("ADBE Vector Anchor").setValue([hx + dir * 0.95 * R, hy + 0.25 * R]); CU.xf(rh.property("mouthO")).property("ADBE Vector Position").setValue([hx + dir * 0.95 * R, hy + 0.25 * R]); }
    }
    if (o.eyes !== "none" && o.backFace !== "awe") {
      var ex = hx + dir * 0.58 * R, ey = hy - 0.05 * R;
      var eg = CU.grp(rh, "eyes"); CU.top(rh.property(eg.propertyIndex));
      var egc = CU.inner(rh.property(1));
      CU.ell(egc, ex, ey, 0.13 * R, 0.19 * R, { fill: ink });
      CU.path(egc, "M " + (ex - 0.1 * R) + " " + (ey - 0.22 * R) + " Q " + ex + " " + (ey - 0.32 * R) + " " + (ex + 0.1 * R) + " " + (ey - 0.24 * R), { stroke: ink, sw: sw * 0.7 });
      CU.path(rh, "M " + (hx + dir * 0.4 * R) + " " + (hy + 0.36 * R) + " Q " + (hx + dir * 0.58 * R) + " " + (hy + 0.5 * R) + " " + (hx + dir * 0.82 * R) + " " + (hy + 0.34 * R), { stroke: ink, sw: sw * 0.8, name: "mouth" });
    }
  } else {
    // hair
    if (o.hair === "curly") {
      CU.path(rh, CU.hairCurly(hx, hy, R, dir, o.bumps, o.hairLow), { fill: o.hairColor || "#4a3526", stroke: ink, sw: sw, name: "hair" });
    } else if (o.hair === "short") {
      CU.path(rh, CU.hairShort(hx, hy, R * 1.02, dir), { fill: o.hairColor || "#2b2b2b", stroke: ink, sw: sw, name: "hair" });
    } else if (o.hair === "sides") {
      CU.path(rh, CU.hairSides(hx, hy, R, dir), { fill: o.hairColor || "#e6e6e6", stroke: ink, sw: sw * 0.9, name: "hair" });
    } else if (o.hair === "granny") {
      CU.path(rh, CU.hairCurly(hx, hy, R * 0.98, dir, 17, 0.55), { fill: o.hairColor || "#e9e9e9", stroke: ink, sw: sw, name: "hair" });
    } else if (o.hair === "bob") {
      CU.path(rh, CU.hairBobFront(hx, hy, R * 1.02, dir), { fill: o.hairColor || "#2b2b2b", stroke: ink, sw: sw, name: "hair" });
    } else if (o.hair === "long" && !o.hat) {   // under a hat the long back mass alone shows (one layer of hair)
      var lf = CU.hairLongFront(hx, hy, R, dir);
      CU.path(rh, lf[0], { fill: o.hairColor || "#2b2b2b", name: "hair" }); CU.path(rh, lf[1], { stroke: ink, sw: sw * 0.9, name: "hairline" });
    } else if (o.hair === "cap") {
      CU.path(rh, "M " + (hx - dir * 0.95 * R) + " " + (hy + 0.1 * R) + " Q " + (hx - dir * 1.02 * R) + " " + (hy - 0.4 * R) + " " + (hx - dir * 0.7 * R) + " " + (hy - 0.5 * R) + " L " + (hx - dir * 0.55 * R) + " " + (hy + 0.05 * R) + " Z", { fill: o.hairColor || "#5a3d2b", stroke: ink, sw: sw * 0.8, name: "hair" });
      CU.path(rh, CU.capHat(hx, hy - 0.05 * R, R * 1.02, dir), { fill: o.hatColor || "#8a7d6b", stroke: ink, sw: sw, name: "cap" });
    }
    if (o.hat === "hard") {
      CU.path(rh, "M " + (hx - 1.0 * R) + " " + (hy - 0.35 * R) + " C " + (hx - 1.0 * R) + " " + (hy - 1.45 * R) + " " + (hx + 1.0 * R) + " " + (hy - 1.45 * R) + " " + (hx + 1.0 * R) + " " + (hy - 0.35 * R) + " Z", { fill: o.hatColor || "#e2a93b", stroke: ink, sw: sw, name: "hat" });
      CU.path(rh, "M " + (hx - 0.15 * R) + " " + (hy - 1.15 * R) + " Q " + (hx + 0.1 * R) + " " + (hy - 0.8 * R) + " " + (hx - 0.05 * R) + " " + (hy - 0.38 * R), { stroke: ink, sw: sw * 0.7 });
      CU.path(rh, "M " + (hx - 1.12 * R) + " " + (hy - 0.33 * R) + " Q " + hx + " " + (hy - 0.45 * R) + " " + (hx + 1.25 * R * (dir > 0 ? 1.05 : 0.9)) + " " + (hy - 0.3 * R) + " L " + (hx + 1.2 * R) + " " + (hy - 0.2 * R) + " Q " + hx + " " + (hy - 0.32 * R) + " " + (hx - 1.12 * R) + " " + (hy - 0.22 * R) + " Z", { fill: CU.shade(o.hatColor || "#e2a93b", 0.85), stroke: ink, sw: sw * 0.8 });
    }
    // face: eyes, lids, mouth (3/4 toward dir)
    var e1 = hx + dir * 0.12 * R, e2 = hx + dir * 0.56 * R, eyY = hy - 0.02 * R + (o.eyeDrop || 0) * R;
    var eyes = CU.grp(rh, "eyes"); CU.top(rh.property(eyes.propertyIndex));
    var eyc = CU.inner(rh.property(1));
    var ew = 0.15 * R, eh = 0.22 * R;
    if (o.lens) { // glowing lenses on a dark face: eyes hidden
      ew = 0; eh = 0;
    }
    if (ew > 0) { CU.ell(eyc, e1, eyY, ew, eh, { fill: ink }); CU.ell(eyc, e2, eyY, ew, eh, { fill: ink }); }
    var exf = CU.xf(rh.property(1));
    exf.property("ADBE Vector Anchor").setValue([(e1 + e2) / 2, eyY]);
    exf.property("ADBE Vector Position").setValue([(e1 + e2) / 2, eyY]);
    var bl = o.blinks || [];
    exf.property("ADBE Vector Scale").expression = "var b=" + CU.windowsExpr([]).replace("[]", "[" + bl.join(",") + "]") + "; var s=100; for (var i=0;i<b.length;i++){ var d=time-b[i]; if (d>=0 && d<0.1) s=8; } [100,s];";
    // brows / lids
    var bw2 = 0.11 * R, by = eyY - 0.24 * R, brow = o.brows || "up";
    function lid(x, k) {
      var tilt = 0;
      if (brow === "worried") { tilt = (x === e1 ? -1 : 1) * dir * 0.07 * R; }
      if (brow === "angry") { tilt = (x === e1 ? -1 : 1) * dir * -0.07 * R; }
      return "M " + (x - bw2) + " " + (by + 0.03 * R - tilt) + " Q " + x + " " + (by - 0.08 * R) + " " + (x + bw2) + " " + (by + 0.03 * R + tilt);
    }
    if (!o.lens) {
      if (o.browColor) { CU.path(rh, lid(e1) + " " + lid(e2), { stroke: ink, sw: sw * 2.6, name: "browsOutline" }); CU.path(rh, lid(e1) + " " + lid(e2), { stroke: o.browColor, sw: sw * 1.7, name: "brows" }); }
      else { CU.path(rh, lid(e1) + " " + lid(e2), { stroke: ink, sw: sw * 0.7, name: "brows" }); }
    }
    if (o.wrinkles) { // forehead lines above the brows
      var wx = hx + dir * 0.34 * R, wd = "", wq;
      for (wq = 0; wq < 3; wq++) { var wy = by - (0.16 + wq * 0.1) * R, ww = (0.26 - wq * 0.05) * R; wd += "M " + (wx - ww) + " " + wy + " Q " + (wx - ww / 2) + " " + (wy - 0.04 * R) + " " + wx + " " + wy + " Q " + (wx + ww / 2) + " " + (wy + 0.04 * R) + " " + (wx + ww) + " " + wy + " "; }
      CU.path(rh, wd, { stroke: ink, sw: sw * 0.5, name: "wrinkles" });
    }
    // mouth: closed and open variants driven by talk windows
    var mx = hx + dir * 0.36 * R, my = hy + 0.4 * R, mood = o.mouth || "smile";
    var closedD;
    if (mood === "flat") { closedD = "M " + (mx - 0.12 * R) + " " + my + " L " + (mx + 0.12 * R) + " " + (my + 0.01 * R); }
    else if (mood === "frown") { closedD = "M " + (mx - 0.14 * R) + " " + (my + 0.06 * R) + " Q " + mx + " " + (my - 0.06 * R) + " " + (mx + 0.14 * R) + " " + (my + 0.06 * R); }
    else { closedD = "M " + (mx - 0.2 * R) + " " + (my - 0.04 * R) + " Q " + mx + " " + (my + 0.12 * R) + " " + (mx + 0.22 * R) + " " + (my - 0.06 * R); }
    var mc = CU.path(rh, closedD, { stroke: ink, sw: sw * 0.85, name: "mouthClosed" });
    var openD = "M " + (mx - 0.2 * R) + " " + (my - 0.06 * R) + " Q " + mx + " " + (my - 0.02 * R) + " " + (mx + 0.22 * R) + " " + (my - 0.08 * R) + " Q " + (mx + 0.16 * R) + " " + (my + 0.28 * R) + " " + (mx - 0.02 * R) + " " + (my + 0.24 * R) + " Q " + (mx - 0.2 * R) + " " + (my + 0.18 * R) + " " + (mx - 0.2 * R) + " " + (my - 0.06 * R) + " Z";
    if (mood === "frown" || mood === "flat") { openD = "M " + (mx - 0.17 * R) + " " + (my + 0.12 * R) + " Q " + mx + " " + (my - 0.1 * R) + " " + (mx + 0.17 * R) + " " + (my + 0.12 * R) + " Q " + mx + " " + (my + 0.2 * R) + " " + (mx - 0.17 * R) + " " + (my + 0.12 * R) + " Z"; }
    var mo = CU.path(rh, openD, { fill: "#6e2f2c", stroke: ink, sw: sw * 0.8, name: "mouthOpen" });
    var moUnused = CU.path(rh, "M " + (mx - 0.2 * R) + " " + (my - 0.06 * R) + " Q " + mx + " " + (my - 0.02 * R) + " " + (mx + 0.22 * R) + " " + (my - 0.08 * R) + " Q " + (mx + 0.16 * R) + " " + (my + 0.28 * R) + " " + (mx - 0.02 * R) + " " + (my + 0.24 * R) + " Q " + (mx - 0.2 * R) + " " + (my + 0.18 * R) + " " + (mx - 0.2 * R) + " " + (my - 0.06 * R) + " Z", { fill: "#6e2f2c", stroke: ink, sw: 0, name: "mouthUnused" });
    rh.property("mouthUnused").remove();
    if (o.teeth) { CU.rect(rh, mx - 0.07 * R, my + 0.01 * R, 0.07 * R, 0.09 * R, 0, { fill: "#ffffff", stroke: ink, sw: sw * 0.5, name: "teeth" }); CU.rect(rh, mx, my + 0.01 * R, 0.07 * R, 0.09 * R, 0, { fill: "#ffffff", stroke: ink, sw: sw * 0.5, name: "teeth2" }); }
    if (o.beard) {
      var jaw = "M " + (hx + dir * 0.02 * R) + " " + (hy + 0.25 * R) + " Q " + (hx + dir * 0.05 * R) + " " + (hy + 0.85 * R) + " " + (mx) + " " + (hy + 0.92 * R) +
        " Q " + (hx + dir * 0.72 * R) + " " + (hy + 0.82 * R) + " " + (hx + dir * 0.74 * R) + " " + (hy + 0.3 * R) +
        " Q " + (mx + dir * 0.22 * R) + " " + (my + 0.3 * R) + " " + mx + " " + (my + 0.26 * R) + " Q " + (mx - dir * 0.22 * R) + " " + (my + 0.3 * R) + " " + (hx + dir * 0.02 * R) + " " + (hy + 0.25 * R) + " Z";
      CU.path(rh, jaw, { fill: o.beard, stroke: ink, sw: sw * 0.6, name: "beard" });
      CU.path(rh, "M " + (mx - 0.3 * R) + " " + (my - 0.02 * R) + " Q " + (mx - 0.15 * R) + " " + (my - 0.2 * R) + " " + mx + " " + (my - 0.1 * R) + " Q " + (mx + 0.15 * R) + " " + (my - 0.2 * R) + " " + (mx + 0.3 * R) + " " + (my - 0.02 * R) + " Q " + mx + " " + (my - 0.02 * R) + " " + (mx - 0.3 * R) + " " + (my - 0.02 * R) + " Z", { fill: o.beard, stroke: ink, sw: sw * 0.6, name: "moustache" });
    }
    var te = CU.talkExpr(o.talk);
    var smileOpen = o.openAt ? "|| (time>=" + o.openAt[0] + " && time<" + o.openAt[1] + ")" : "";
    rh.property("mouthOpen").property("ADBE Vector Transform Group").property("ADBE Vector Group Opacity").expression = te + "(open " + smileOpen + ")?100:0;";
    rh.property("mouthClosed").property("ADBE Vector Transform Group").property("ADBE Vector Group Opacity").expression = te + "(open " + smileOpen + ")?0:100;";
    if (o.glasses) {
      var gc = o.lens || "none";
      var gw = 0.34 * R, gh = 0.22 * R;
      var G = CU.grp(rh, "glasses"); CU.top(rh.property(G.propertyIndex)); var gcn = CU.inner(rh.property(1));
      if (o.glasses === "round") {
        gw = 0.3 * R; gh = 0.3 * R;
        CU.ell(gcn, e1, eyY, gw, gh, { stroke: ink, sw: sw * 0.7, fill: o.lens || null });
        CU.ell(gcn, e2, eyY, gw, gh, { stroke: ink, sw: sw * 0.7, fill: o.lens || null });
      } else if (o.glasses === "big") {
        gw = 0.38 * R; gh = 0.38 * R;
        CU.ell(gcn, e1, eyY, gw, gh, { stroke: ink, sw: sw * 0.9, fill: "#ffffff", fo: 60 });
        CU.ell(gcn, e2, eyY, gw, gh, { stroke: ink, sw: sw * 0.9, fill: "#ffffff", fo: 60 });
        CU.ell(gcn, e1 + dir * 0.03 * R, eyY, 0.12 * R, 0.16 * R, { fill: ink }); CU.ell(gcn, e2 + dir * 0.03 * R, eyY, 0.12 * R, 0.16 * R, { fill: ink });
      } else {
        CU.rect(gcn, e1 - gw / 2, eyY - gh / 2, gw, gh, 0.05 * R, { stroke: ink, sw: sw * 0.7, fill: o.lens || null });
        CU.rect(gcn, e2 - gw / 2, eyY - gh / 2, gw, gh, 0.05 * R, { stroke: ink, sw: sw * 0.7, fill: o.lens || null });
      }
      CU.path(gcn, "M " + (e1 + dir * gw / 2) + " " + eyY + " L " + (e2 - dir * gw / 2) + " " + eyY, { stroke: ink, sw: sw * 0.6 });
      CU.path(gcn, "M " + (e1 - dir * gw / 2) + " " + (eyY - 0.02 * R) + " L " + (hx - dir * (o.backlit ? 0.97 : 0.75) * R) + " " + (eyY - 0.04 * R), { stroke: ink, sw: sw * 0.6 });
      if (o.backlit) { CU.path(gcn, "M " + (e2 + dir * gw / 2) + " " + (eyY - 0.02 * R) + " L " + (hx + dir * 0.98 * R) + " " + (eyY - 0.05 * R), { stroke: ink, sw: sw * 0.6 }); }
    }
  }
  if (o.rimHead) {
    CU.path(rh, CU.arc(hx, hy, R - 2, dir > 0 ? -60 : 150, dir > 0 ? 30 : 240, true), { stroke: o.rimHead, sw: sw * 1.4 });
  }
  layers.push(Hd);
  Hd.parent = B;
  if (HbG) { HbG.parent = Hd; }
  // head motion: nod while talking, optional turn keys
  var hte = CU.talkExpr(o.talk);
  CU.rot(Hd).expression = hte + "var w2=" + CU.windowsExpr(o.talk || []) + "; var on2=false; for (var j=0;j<w2.length;j++){ if (time>=w2[j][0] && time<w2[j][1]) on2=true; } " +
    "(on2 ? 2.2*Math.sin(time*7) : 1.4*Math.sin(time*1.7 + " + (o.phase || 0) + ")) + " + (o.tilt || 0) + " + value;";
  if (o.headKeys) { var hk = [], h; for (h = 0; h < o.headKeys.length; h++) { hk.push([o.headKeys[h][0], o.headKeys[h][1]]); } CU.keys(CU.rot(Hd), hk, 60); }

  // arms on top of the body
  var sides = [["l", -1], ["r", 1]], k;
  for (k = 0; k < 2; k++) {
    var key = sides[k][0], s = sides[k][1];
    if (o.arms === false) { break; }
    var poses = (o.arms && o.arms[key]) ? o.arms[key] : [[0, "down"]];
    var A = CU.layer(c, "arm " + key), ra = CU.root(A);
    var ag = CU.path(ra, CU.armPose(poses[0][1], s, bx, top, R, dir), { stroke: ink, sw: sw * 1.7, name: "arm" });
    var pp = CU.inner(ra.property(1)).property(1).property("ADBE Vector Shape"), q;
    if (poses.length > 1) {
      for (q = 0; q < poses.length; q++) { pp.setValueAtTime(poses[q][0], CU.parse(CU.armPose(poses[q][1], s, bx, top, R, dir))[0]); }
      CU.ease(pp, 60);
    }
    var shX = bx + s * 0.6 * R * 1.0, shY = top + 0.32 * R;
    CU.anc(A).setValue([shX, shY]); CU.pos(A).setValue([shX, shY]);
    if (o.walk && o.prop === "books") { CU.pos(A).expression = CU.walkGate(o) + "value + [0, " + (0.03 * R) + "*Math.abs(Math.sin(time*" + (o.walk * 2 * Math.PI) + "))*on]"; }
    else if (o.walk) { CU.rot(A).expression = CU.walkGate(o) + (-s * 8) + "*Math.sin(time*" + (o.walk * 2 * Math.PI) + ")*on"; }
    A.parent = B;
    layers.push(A);
  }
  var Pp = null;
  if (o.prop && o.part !== "body") {
    Pp = CU.layer(c, "prop"), rp = CU.root(Pp), hr = CU.armPts((o.arms && o.arms.r) ? o.arms.r[0][1] : "down", 1, bx, top, R, dir)[2];
    if (o.prop === "book") { // book held up in front of the chest, cover toward camera
      var pw = (o.propScale || 1) * 0.95 * R, ph = (o.propScale || 1) * 0.7 * R, px = bx - pw / 2, py = top + 0.35 * R - ((o.propScale || 1) - 1) * 0.55 * R;
      CU.rect(rp, px, py, pw, ph, 4, { fill: o.propColor || "#3f7a4a", stroke: ink, sw: sw * 0.9 });
      CU.path(rp, "M " + bx + " " + py + " L " + bx + " " + (py + ph), { stroke: ink, sw: sw * 0.7 });
      CU.path(rp, CU.squiggle(px + 12, py + ph * 0.35, pw * 0.35, 3, 4) + CU.squiggle(px + 12, py + ph * 0.6, pw * 0.3, 3, 5) + CU.squiggle(bx + 10, py + ph * 0.45, pw * 0.3, 3, 6), { stroke: "#dfe8d8", sw: sw * 0.5 });
    } else if (o.prop === "openbook") { // an open book held up in front of the lower face, pages turned toward the reader
      var bl4 = CU.armPts("read", -1, bx, top, R, dir)[2], br4 = CU.armPts("read", 1, bx, top, R, dir)[2], gx = (bl4[0] + br4[0]) / 2;
      var y0 = hy + 0.18 * R, y1 = Math.max(bl4[1], br4[1]) + 0.04 * R, cov = o.propColor || "#9a4a3a", pg = "#eadcc0";
      CU.path(rp, "M " + (bl4[0] - 0.06 * R) + " " + (y0 + 0.02 * R) + " L " + gx + " " + (y0 + 0.1 * R) + " L " + (br4[0] + 0.06 * R) + " " + (y0 + 0.02 * R) + " L " + (br4[0] + 0.05 * R) + " " + (y1 + 0.04 * R) + " L " + gx + " " + (y1 + 0.1 * R) + " L " + (bl4[0] - 0.05 * R) + " " + (y1 + 0.04 * R) + " Z", { fill: cov, stroke: ink, sw: sw * 0.9 });
      // the reader faces the pages: the camera sees the two outside covers in a V, the spine in the middle, page edges on top
      var halves = [[bl4[0], gx], [gx, br4[0]]], pq;
      for (pq = 0; pq < 2; pq++) {
        var xo = pq ? halves[pq][1] : halves[pq][0], xi = gx;
        CU.path(rp, "M " + xo + " " + (y0 - 0.06 * R) + " Q " + ((xo + xi) / 2) + " " + (y0 - 0.1 * R) + " " + xi + " " + (y0 + 0.02 * R) + " L " + xi + " " + (y0 + 0.07 * R) + " Q " + ((xo + xi) / 2) + " " + (y0 - 0.04 * R) + " " + xo + " " + y0 + " Z", { fill: pg, stroke: ink, sw: sw * 0.6 });
        CU.path(rp, "M " + xo + " " + y0 + " Q " + ((xo + xi) / 2) + " " + (y0 - 0.04 * R) + " " + xi + " " + (y0 + 0.07 * R) + " L " + xi + " " + (y1 + 0.08 * R) + " Q " + ((xo + xi) / 2) + " " + (y1 + 0.02 * R) + " " + xo + " " + (y1 + 0.02 * R) + " Z", { fill: pq ? CU.shade(cov, 0.86) : cov, stroke: ink, sw: sw * 0.8 });
        var e2 = CU.lerp([xo, y0 + 0.05 * R], [xi, y0 + 0.12 * R], 0.15), f2 = CU.lerp([xo, y1 - 0.02 * R], [xi, y1 + 0.04 * R], 0.15);
        CU.path(rp, "M " + e2[0] + " " + e2[1] + " L " + f2[0] + " " + f2[1], { stroke: CU.shade(cov, 0.7), sw: sw * 0.5 });
      }
      CU.path(rp, "M " + gx + " " + (y0 + 0.05 * R) + " L " + gx + " " + (y1 + 0.1 * R), { stroke: ink, sw: sw * 1.1 });
      var hk4; for (hk4 = 0; hk4 < 2; hk4++) { var hp4 = hk4 ? br4 : bl4; CU.ell(rp, hp4[0], hp4[1], 0.2 * R, 0.24 * R, { fill: skin, stroke: ink, sw: sw * 0.8 }); }
    } else if (o.prop === "books") { // carried stack, held out in front with both hands on its sides
      var cols = o.propColors || ["#3f6b4c", "#8a3a3c", "#3f6b4c", "#7a2f3a"], labels = o.propLabels || ["", "PHYSICS", "", "QUANTUM"], q2;
      var hl3 = CU.armPts("hug", -1, bx, top, R, dir)[2], hr3 = CU.armPts("hug", 1, bx, top, R, dir)[2];
      var bxl = hl3[0] - 0.02 * R, bxr = hr3[0] + 0.02 * R, bh = 0.3 * R, by0 = top + 0.45 * R, dp = 0.12 * R;
      CU.path(rp, "M " + (bxl + 0.02 * R) + " " + by0 + " L " + (bxl + dir * dp + 0.02 * R) + " " + (by0 - dp) + " L " + (bxr + dir * dp - 0.02 * R) + " " + (by0 - dp - 0.01 * R) + " L " + (bxr - 0.02 * R) + " " + (by0 - 0.01 * R) + " Z", { fill: CU.shade(cols[0], 1.25), stroke: ink, sw: sw * 0.8 });
      for (q2 = 0; q2 < 4; q2++) {
        var yy = by0 + q2 * bh, jx = (q2 % 2 ? -1 : 1) * 0.03 * R;
        CU.path(rp, "M " + (bxl + jx) + " " + yy + " L " + (bxr + jx) + " " + (yy - 0.01 * R) + " L " + (bxr + jx + 0.01 * R) + " " + (yy + bh) + " L " + (bxl + jx - 0.01 * R) + " " + (yy + bh + 0.01 * R) + " Z", { fill: cols[q2 % cols.length], stroke: ink, sw: sw * 0.8 });
        CU.path(rp, "M " + (bxl + jx + 0.1 * R) + " " + (yy + 0.03 * R) + " L " + (bxl + jx + 0.16 * R) + " " + (yy + bh - 0.03 * R), { stroke: "#e8e2d2", sw: sw * 1.4 });
        if (labels[q2]) { var LB = CU.text(c, labels[q2], { size: 0.16 * R, color: "#e8e2d2", x: (bxl + bxr) / 2 + jx, y: yy + bh * 0.68, center: true, name: "book label " + q2 }); LB.parent = Pp; layers.push(LB); }
      }
      var hk2; for (hk2 = 0; hk2 < 2; hk2++) { var hp2 = hk2 ? hr3 : hl3; CU.ell(rp, hp2[0], hp2[1], 0.2 * R, 0.24 * R, { fill: skin, stroke: ink, sw: sw * 0.8 }); }
    } else if (o.prop === "stick") {
      var pk = o.propSide === "l" ? "l" : "r", sp3 = CU.armPts((o.arms && o.arms[pk]) ? o.arms[pk][0][1] : "point", pk === "l" ? -1 : 1, bx, top, R, dir), ex3 = sp3[2][0] - sp3[1][0], ey3 = sp3[2][1] - sp3[1][1], el3 = Math.sqrt(ex3 * ex3 + ey3 * ey3);
      CU.path(rp, "M " + (sp3[2][0] - ex3 / el3 * 0.1 * R) + " " + (sp3[2][1] - ey3 / el3 * 0.1 * R) + " L " + (sp3[2][0] + ex3 / el3 * 1.6 * R) + " " + (sp3[2][1] + ey3 / el3 * 1.6 * R), { stroke: "#b48a52", sw: sw * 1.8 });
    } else if (o.prop === "pencil") {
      CU.ell(rp, hr[0] + dir * 0.03 * R, hr[1] - 0.02 * R, 0.2 * R, 0.17 * R, { fill: skin, stroke: ink, sw: sw * 0.7 });   // the fist around the pencil
      var Pc = CU.grp(rp, "pencil"); var pcn = CU.inner(rp.property(1));
      CU.path(pcn, "M " + hr[0] + " " + hr[1] + " L " + (hr[0] + dir * 0.12 * R) + " " + (hr[1] - 0.35 * R), { stroke: "#e2b04a", sw: sw * 2 });
      CU.path(pcn, "M " + hr[0] + " " + hr[1] + " L " + (hr[0] + dir * 0.12 * R) + " " + (hr[1] - 0.35 * R), { stroke: ink, sw: sw * 0.5, so: 60 });
      var pxf = CU.xf(rp.property(1)); pxf.property("ADBE Vector Anchor").setValue(hr); pxf.property("ADBE Vector Position").setValue(hr);
      pxf.property("ADBE Vector Rotation").expression = "4*Math.sin(time*9 + 0.6)";   // the pencil tilts in the fingers
    }
    Pp.parent = B;
    if (o.prop === "openbook") { CU.rot(Pp).expression = "1.2*Math.sin(time*2.2)"; CU.anc(Pp).setValue([bx, top + 0.3 * R]); CU.pos(Pp).setValue([bx, top + 0.3 * R]); }
    if (o.prop === "books" && o.walk) { CU.pos(Pp).expression = CU.walkGate(o) + "value + [0, " + (0.03 * R) + "*Math.abs(Math.sin(time*" + (o.walk * 2 * Math.PI) + "))*on]"; }
    if (o.prop === "pencil") { // writing: the hand moves (the arm turns a little at the shoulder) and the pencil goes with it
      var arR = null, aq; for (aq = 1; aq <= c.numLayers; aq++) { if (c.layer(aq).name === "arm r") { arR = c.layer(aq); } }
      if (arR) { CU.rot(arR).expression = "5*Math.sin(time*9) + 2.5*Math.sin(time*17)"; Pp.parent = arR; }
    }
  }
  if (o.thread && o.part !== "body") { // sewing thread from the right hand to a point (moves with the arm keys)
    var Th = CU.layer(c, "thread"), rt = CU.root(Th);
    var tposes = o.arms.r, tq;
    CU.path(rt, "M " + o.thread[0] + " " + o.thread[1] + " L " + CU.armPts(tposes[0][1], 1, bx, top, R, dir)[2][0] + " " + CU.armPts(tposes[0][1], 1, bx, top, R, dir)[2][1], { stroke: "#efe3b5", sw: 2 });
    var tp = CU.inner(rt.property(1)).property(1).property("ADBE Vector Shape");
    for (tq = 0; tq < tposes.length; tq++) { var hp = CU.armPts(tposes[tq][1], 1, bx, top, R, dir)[2]; tp.setValueAtTime(tposes[tq][0], CU.parse("M " + o.thread[0] + " " + o.thread[1] + " L " + hp[0] + " " + hp[1])[0]); }
    CU.ease(tp, 60);
    Th.parent = B;
  }
  if (o.crouch) { // the body (and everything parented to it) drops with the bend
    var bq, bp = CU.pos(B), b0 = bp.value;
    for (bq = 0; bq < o.crouch.length; bq++) { bp.setValueAtTime(o.crouch[bq][0], [b0[0], b0[1] + o.crouch[bq][1] * 0.55 * legLen]); }
    CU.ease(bp, 60);
  }
  if (o.prop === "books" && Pp) { // the arms go behind the stack; the hands, drawn with the books, grip its sides
    Pp.moveToBeginning(); var ai2, lbs = []; for (ai2 = 1; ai2 <= c.numLayers; ai2++) { if (c.layer(ai2).name.indexOf("book label") === 0) { lbs.push(c.layer(ai2)); } }
    for (ai2 = 0; ai2 < lbs.length; ai2++) { lbs[ai2].moveToBeginning(); } }
  // breathing / bob
  CU.scl(B).expression = "[100, 100 + " + (o.breathe === undefined ? 1.2 : o.breathe) + "*Math.sin(time*3 + " + (o.phase || 0) + ")]";
  var i2;
  for (i2 = 0; i2 < layers.length; i2++) { if (layers[i2].parent === null) { layers[i2].parent = root; } }
  CU.rot(root).expression = (o.sway === undefined ? 1.0 : o.sway) + "*Math.sin(time*1.3 + " + (o.phase || 0) + ")";
  if (o.walk) { CU.pos(root).expression = CU.walkGate(o) + "value - [0, " + (0.06 * R) + "*Math.abs(Math.sin(time*" + (o.walk * 2 * Math.PI) + "))*on]"; }
  if (o.rise) { // [t0, t1, dy]: rises into frame from dy below
    CU.keys(CU.pos(root), [[o.rise[0], [fx, fy + o.rise[2]]], [o.rise[1], [fx, fy]]], 70);
  }
  CU.HANDY = null;
  o.arms = armsSave;
  if (o.part === "arms") { // only arms, props and thread stay visible; the rest still drives them as parents
    var li2; for (li2 = 1; li2 <= c.numLayers; li2++) { var ly2 = c.layer(li2); if (!/^(arm |prop|thread|ROOT)/.test(ly2.name)) { ly2.enabled = false; } }
    CU.META[c.name] = { armsOf: "P " + o.name };
    root.moveToBeginning();
    return c;
  }
  var hairTop = { curly: 1.2, "short": 1.08, bob: 1.12, "long": 1.12, cap: 1.25, sides: 1.05, granny: 1.18 }[o.hair] || 1.0; if (o.hat === "hard") { hairTop = 1.45; }
  CU.META[c.name] = { skin: o.skin || "#efc8aa", hairTop: hairTop, R: R, legLen: legLen, bodyH: bodyH, dir: dir, walk: o.walk, walkWindow: o.walkWindow, legs: legLen > 0, thread: o.thread, arms: o.arms, prop: o.prop, propSide: o.propSide, handY: o.handY };
  root.moveToBeginning();
  return c;
};

// Robot presenter (helmet, visor with glowing eyes, mic, hoodie with a spark logo).
CU.robot = function (o) {
  var c = CU.comp("P " + o.name, o.dur, CU.PW, CU.PH);
  var R = o.R || 100, fx = CU.FEET[0], fy = CU.FEET[1], ink = CU.INK, sw = CU.SW;
  var legLen = 1.5 * R, bodyH = 1.7 * R, top = fy - legLen - bodyH, bx = fx, hx = bx + 0.05 * R, hy = top - 0.6 * R;
  var root = CU.nul(c, "ROOT", [fx, fy]);
  var Lg = CU.layer(c, "legs"), rl = CU.root(Lg);
  CU.path(rl, "M " + (bx - 0.2 * R) + " " + (top + bodyH - 8) + " L " + (bx - 0.28 * R) + " " + fy, { stroke: ink, sw: sw * 1.7 });
  CU.path(rl, "M " + (bx + 0.25 * R) + " " + (top + bodyH - 8) + " L " + (bx + 0.22 * R) + " " + fy, { stroke: ink, sw: sw * 1.7 });
  var B = CU.layer(c, "body", [bx, top + bodyH]), rb = CU.root(B);
  CU.path(rb, "M " + (bx - 0.6 * R) + " " + (top + 0.2 * R) + " C " + (bx - 0.6 * R) + " " + (top - 0.1 * R) + " " + (bx + 0.6 * R) + " " + (top - 0.1 * R) + " " + (bx + 0.6 * R) + " " + (top + 0.2 * R) +
    " C " + (bx + 0.8 * R) + " " + (top + 0.8 * R) + " " + (bx + 0.78 * R) + " " + (top + bodyH) + " " + (bx + 0.5 * R) + " " + (top + bodyH) + " L " + (bx - 0.5 * R) + " " + (top + bodyH) +
    " C " + (bx - 0.78 * R) + " " + (top + bodyH) + " " + (bx - 0.8 * R) + " " + (top + 0.8 * R) + " " + (bx - 0.6 * R) + " " + (top + 0.2 * R) + " Z", { fill: "#6d7178", stroke: ink, sw: sw });
  CU.path(rb, "M " + (bx - 0.62 * R) + " " + (top + 0.4 * R) + " C " + (bx - 0.8 * R) + " " + (top + 1.0 * R) + " " + (bx - 0.7 * R) + " " + (top + bodyH - 6) + " " + (bx - 0.45 * R) + " " + (top + bodyH - 6) + " L " + (bx - 0.25 * R) + " " + (top + bodyH - 6) + " C " + (bx - 0.4 * R) + " " + (top + 1.0 * R) + " " + (bx - 0.35 * R) + " " + (top + 0.6 * R) + " " + (bx - 0.62 * R) + " " + (top + 0.4 * R) + " Z", { fill: "#55595f" });
  CU.path(rb, "M " + (bx - 0.6 * R) + " " + (top + bodyH - 0.3 * R) + " L " + (bx + 0.62 * R) + " " + (top + bodyH - 0.3 * R), { stroke: ink, sw: sw * 0.8 });
  // spark logo on the chest
  var sp = "", j, scx = bx + 0.15 * R, scy = top + 0.7 * R;
  for (j = 0; j < 10; j++) { var a = j * 36 * Math.PI / 180; sp += "M " + scx + " " + scy + " L " + (scx + 0.17 * R * Math.cos(a)) + " " + (scy + 0.17 * R * Math.sin(a)) + " "; }
  CU.path(rb, sp, { stroke: "#d9573a", sw: sw * 0.9 });
  var Hd = CU.layer(c, "head", [hx, hy + 0.8 * R]), rh = CU.root(Hd);
  CU.path(rh, "M " + (hx - 0.82 * R) + " " + (hy + 0.2 * R) + " C " + (hx - 0.9 * R) + " " + (hy - 0.9 * R) + " " + (hx + 0.9 * R) + " " + (hy - 0.9 * R) + " " + (hx + 0.82 * R) + " " + (hy + 0.2 * R) +
    " C " + (hx + 0.8 * R) + " " + (hy + 0.75 * R) + " " + (hx - 0.8 * R) + " " + (hy + 0.75 * R) + " " + (hx - 0.82 * R) + " " + (hy + 0.2 * R) + " Z", { fill: "#5e626a", stroke: ink, sw: sw });
  CU.path(rh, "M " + (hx - 0.25 * R) + " " + (hy - 0.62 * R) + " L " + (hx + 0.25 * R) + " " + (hy - 0.62 * R) + " L " + (hx + 0.2 * R) + " " + (hy - 0.38 * R) + " L " + (hx - 0.2 * R) + " " + (hy - 0.38 * R) + " Z", { fill: "#7b8088", stroke: ink, sw: sw * 0.8 });
  CU.path(rh, "M " + (hx - 0.62 * R) + " " + (hy - 0.05 * R) + " C " + (hx - 0.62 * R) + " " + (hy - 0.3 * R) + " " + (hx + 0.62 * R) + " " + (hy - 0.3 * R) + " " + (hx + 0.62 * R) + " " + (hy - 0.05 * R) +
    " C " + (hx + 0.62 * R) + " " + (hy + 0.28 * R) + " " + (hx - 0.62 * R) + " " + (hy + 0.28 * R) + " " + (hx - 0.62 * R) + " " + (hy - 0.05 * R) + " Z", { fill: "#2a2e35", stroke: ink, sw: sw });
  var EY = CU.layer(c, "eyes glow", [hx, hy + 0.8 * R]); var rey = CU.root(EY);
  var eyes = CU.grp(rey, "eyes"); var ec = CU.inner(rey.property(1));
  CU.rect(ec, hx - 0.38 * R, hy - 0.13 * R, 0.16 * R, 0.24 * R, 0.08 * R, { fill: "#5fe3ff" });
  CU.rect(ec, hx + 0.2 * R, hy - 0.13 * R, 0.16 * R, 0.24 * R, 0.08 * R, { fill: "#5fe3ff" });
  var exf = CU.xf(rey.property(1));
  exf.property("ADBE Vector Anchor").setValue([hx, hy]); exf.property("ADBE Vector Position").setValue([hx, hy]);
  exf.property("ADBE Vector Scale").expression = "var b=[" + (o.blinks || []).join(",") + "]; var s=100; for (var i=0;i<b.length;i++){ var d=time-b[i]; if (d>=0 && d<0.1) s=10; } [100,s];";
  // mic boom
  if (o.mic) { CU.ell(rh, hx + 0.48 * R, hy + 0.23 * R, 0.24 * R, 0.24 * R, { fill: "#1d1f24", stroke: ink, sw: sw * 0.8 }); }
  Hd.parent = B;
  CU.rot(Hd).expression = "var w=" + CU.windowsExpr(o.talk || []) + "; var on=false; for (var i=0;i<w.length;i++){ if (time>=w[i][0] && time<w[i][1]) on=true; } (on ? 3*Math.sin(time*6) : 1.2*Math.sin(time*1.5)) + value;";
  if (o.headKeys) { CU.keys(CU.rot(Hd), o.headKeys, 60); }
  // eye glow pulse when talking
  var poses = o.arms || [[0, "down"]];
  var A = CU.layer(c, "arm l"), ra = CU.root(A);
  CU.path(ra, CU.armPose(poses[0][1], -1, bx, top, R * 0.95, 1), { stroke: ink, sw: sw * 1.6 });
  var pp = CU.inner(ra.property(1)).property(1).property("ADBE Vector Shape"), q;
  if (poses.length > 1) {
    for (q = 0; q < poses.length; q++) { pp.setValueAtTime(poses[q][0], CU.parse(CU.armPose(poses[q][1], -1, bx, top, R * 0.95, 1))[0]); }
    CU.ease(pp, 60);
  }
  A.parent = B;
  var A2 = CU.layer(c, "arm r"); CU.path(CU.root(A2), CU.armPose("hold", 1, bx, top, R, 1), { stroke: ink, sw: sw * 1.6 }); A2.parent = B;
  CU.scl(B).expression = "[100, 100 + 1.0*Math.sin(time*3)]";
  Lg.parent = root; B.parent = root;
  CU.rot(root).expression = "1.2*Math.sin(time*1.4)";
  EY.parent = Hd; CU.glow(EY, 10, 1.5, 20);
  CU.META[c.name] = { R: R, legLen: legLen, bodyH: bodyH, dir: 1, legs: true };
  root.moveToBeginning();
  return c;
};
