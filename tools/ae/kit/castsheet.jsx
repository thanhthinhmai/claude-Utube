// castsheet.jsx: the cast sheet of a film (specs/034 contracts/rig.md). tools/ae/sheet.py plans the pictures
// (data/cast_sheet.json) and entry.jsx calls CU.build(CU.castSheet(plan)): every picture is one shot of one frame
// (the walk loop is 75 frames), on a flat #ecebf0 ground, so the render queue writes them all into master.mp4 and
// sheet.py cuts them out with ffmpeg. A picture the rig cannot draw stays empty and logs "CHECK missing <n> <why>"
// (the shot itself never throws, so the frame count always matches the plan).
CU.SHEET_BG = "#ecebf0";

CU.castSheet = function (plan) {
  var ids = [], i;
  CU.SHEET_PLAN = plan;
  for (i = 0; i < plan.frames.length; i++) {
    (function (n, fr) {
      CU["shot" + n] = function () { return CU.sheetFrame(n, fr); };
    })(i + 1, plan.frames[i]);
    ids.push(String(i + 1));
  }
  return ids;
};

CU.sheetFrame = function (n, fr) {
  var dur = (fr.len || 1) / CU.FPS;
  var c = CU.comp("K" + n + " " + fr.character + " " + fr.key, dur);
  CU.solid(c, "ground", CU.SHEET_BG);
  try {
    if (fr.kind === "group") { CU.sheetGroup(c, fr, dur); }
    else { CU.sheetOne(c, fr, dur); }
  } catch (e) {
    var k; for (k = c.numLayers; k >= 1; k--) { if (c.layer(k).name !== "ground") { c.layer(k).remove(); } }
    CU.say("CHECK missing " + n + " " + fr.character + " " + fr.key + ": " + e.toString() + (e.line ? " line " + e.line : ""));
  }
  return c;
};

// options of one picture for the rig's make(): view, expression preset, pose, walk
CU.sheetOptions = function (rig, fr, dur) {
  var o = { name: fr.character + "-" + fr.key, dur: dur, seed: 3 }, k, src;
  var view = rig.view(fr.view || "front");
  if (!view) { throw new Error("the rig has no view " + fr.view); }
  for (k in view) { if (view.hasOwnProperty(k)) { o[k] = view[k]; } }
  if (fr.expr) {
    src = rig.expression(fr.expr);
    if (!src) { throw new Error("the rig has no expression " + fr.expr); }
    for (k in src) { if (src.hasOwnProperty(k) && k !== "pose") { o[k] = src[k]; } }
    if (src.pose) { o.keys = [[0, { pose: src.pose }]]; }
  }
  if (fr.pose) { o.keys = [[0, { pose: fr.pose }]]; }
  if (fr.kind === "walk") { o.walk = [[0, dur + 0.5, 2, 46]]; o.keys = null; }
  return o;
};

CU.sheetOne = function (c, fr, dur) {
  var ch = CU.CAST[fr.character];
  var rig = CU.rig(ch.rig), sz = rig.size, spec = ch.spec || {};
  var P = CU.char(fr.character, CU.sheetOptions(rig, fr, dur));
  var L = c.layers.add(P.comp); L.name = "B " + fr.character;
  var sc = spec.scale || 1;
  if (fr.kind === "expr") {                      // head close-up
    CU.anc(L).setValue([sz.fx, sz.headY + 60]); CU.pos(L).setValue([CU.W / 2, CU.H * 0.52]);
    CU.scl(L).setValue([125, 125]);
  } else {                                       // whole body: 80 % of the frame, feet at 92 %
    var s = 0.8 * CU.H / (sz.fy - (sz.headY - sz.R) + 40) * sc;
    CU.anc(L).setValue([sz.fx, sz.fy]); CU.pos(L).setValue([CU.W / 2, CU.H * 0.92]);
    CU.scl(L).setValue([s * 100, s * 100]);
  }
  if (fr.kind === "walk") { CU.sheetFloor(c); }
};

// a moving floor under a walk in place
CU.sheetFloor = function (c) {
  var F = CU.layer(c, "floor"), rt = CU.root(F), y = CU.H * 0.92 + 6, i;
  CU.rect(rt, 0, y, CU.W, 4, 0, { fill: "#cfcdd6" });
  for (i = -2; i < 14; i++) { CU.rect(rt, i * 180, y + 18, 90, 6, 3, { fill: "#d9d7df" }); }
  CU.pos(F).expression = "[value[0] - (time*260) % 180, value[1]];";
  F.moveToEnd(); c.layer("ground").moveToEnd();
};

CU.sheetGroup = function (c, fr, dur) {
  var ch = CU.CAST[fr.character], rig = CU.rig(ch.rig), sz = rig.size, n = ch.members.length, i;
  var s = 0.62 * CU.H / (sz.fy - (sz.headY - sz.R) + 40), gap = CU.W / (n + 1);
  for (i = 0; i < n; i++) {
    var o = CU.sheetOptions(rig, { character: fr.character, key: "m" + i, view: "front" }, dur);
    o.member = i; o.name = fr.character + "-m" + i; o.seed = 3 + i;
    var P = CU.char(fr.character, o);
    var L = c.layers.add(P.comp); L.name = "B " + fr.character + " " + i;
    var ms = ch.members[i].scale || 1;
    CU.anc(L).setValue([sz.fx, sz.fy]); CU.pos(L).setValue([gap * (i + 1), CU.H * 0.92]);
    CU.scl(L).setValue([s * ms * 100, s * ms * 100]);
  }
};
