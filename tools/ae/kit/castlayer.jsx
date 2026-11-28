// castlayer.jsx: the cast layers of Blender shots (specs/038 T043, research R6). tools/ae/castpass.py writes
// data/layers.json ({fps, jobs: [{name, shot, layer, char, member, view, frames, size, track}]}) and entry.jsx calls
// CU.castLayers(plan): each job is one comp holding only the character's rig on a transparent ground, square
// size × size, feet at 98 % of the height, the character 85 % of it (CU.LAYER_FILL; tools/blender/kit/cards.py makes
// the card height / 0.85 to match). The render queue writes each comp as <name>.avi with the "Lossless with Alpha"
// template (AE 2027 refuses PNG through setSettings, T040); castpass.py turns the AVIs into PNG frames.
// Log lines: START, layer <shot> <char> <view> ok, ERR …, DONE.
CU.LAYER_FILL = 0.85;
CU.LAYER_FEET = 0.98;
CU.LAYER_TEMPLATE = "Lossless with Alpha";

CU.castLayers = function (plan) {
  app.beginSuppressDialogs();
  CU.log = new File(CU.WORK + "/log.txt"); CU.log.encoding = "UTF-8"; CU.log.open("w"); CU.say("START");
  try {
    // a project left changed (a script stopped half way) makes newProject() ask "Save As" and wait: close it first
    try { if (app.project) { app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES); } } catch (e0) { }
    app.newProject();
    var rq = app.project.renderQueue, i, queued = [];
    for (i = rq.numItems; i >= 1; i--) { rq.item(i).remove(); }
    for (i = 0; i < plan.jobs.length; i++) {
      var job = plan.jobs[i];
      try {
        var c = CU.layerComp(job);
        var it = rq.items.add(c);
        try { it.applyTemplate("Best Settings"); } catch (e1) { }
        var om = it.outputModule(1);
        om.applyTemplate(CU.LAYER_TEMPLATE);
        om.file = new File(CU.WORK + "/" + job.name + ".avi");
        queued.push({ job: job, om: om });
        CU.say("comp " + job.shot + " " + (job.layer || job.char) + " " + job.view);
      } catch (e2) { CU.say("ERR layer " + job.shot + " " + (job.layer || job.char) + " " + job.view + ": " + e2.toString() + (e2.line ? " line " + e2.line : "")); }
    }
    if (queued.length) {
      CU.say("render " + queued.length + " layers");
      rq.render();
    }
    for (i = 0; i < queued.length; i++) {
      var q = queued[i];
      if (q.om.file.exists) { CU.say("layer " + q.job.shot + " " + (q.job.layer || q.job.char) + " " + q.job.view + " ok"); }
      else { CU.say("ERR render: After Effects wrote no " + q.job.name + ".avi"); }
    }
  } catch (e) { CU.say("ERR " + e.toString() + (e.line ? " line " + e.line : "")); }
  try { app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES); } catch (e4) { }   // After Effects stays open
  try { app.purge(PurgeTarget.ALL_CACHES); } catch (e5) { }
  app.endSuppressDialogs(false);
  CU.say("DONE"); CU.log.close();
};

// rig options of one job: the view, then poses, expressions and walking from the track (frame numbers from 1)
CU.layerOptions = function (rig, job) {
  var dur = job.frames / CU.FPS, o = { name: job.name, dur: dur, seed: 3 + (job.member || 0), dir: 1 }, k, i;
  var view = rig.view(job.view);
  if (!view) { throw new Error("the rig has no view " + job.view); }
  for (k in view) { if (view.hasOwnProperty(k)) { o[k] = view[k]; } }
  var keys = [], lastPose = null, walk = [], w0 = null, tr = job.track || [], mine = {};
  for (i = 0; i < tr.length; i++) {
    var e = tr[i], t = (e.f - 1) / CU.FPS;
    var pose = e.pose || "down";
    if (pose !== lastPose) { keys.push([t, { pose: pose }]); lastPose = pose; }
    if (e.expr) {
      var src = rig.expression(e.expr);
      if (!src) { throw new Error("the rig has no expression " + e.expr); }
      for (k in src) {
        if (!src.hasOwnProperty(k) || k === "pose") { continue; }
        if (src[k] instanceof Array) {                     // timed lists: [[t, value…], …] from this frame on
          var row = src[k][0].slice(0); row[0] = t;
          if (!mine[k]) { o[k] = []; mine[k] = true; }    // the first expression replaces what the view set
          o[k].push(row);
        } else { o[k] = src[k]; }
      }
    }
    if (e.walk && w0 === null) { w0 = t; }
    if (!e.walk && w0 !== null) { walk.push([w0, t, 2, 46]); w0 = null; }
  }
  if (w0 !== null) { walk.push([w0, dur + 0.5, 2, 46]); }
  if (walk.length) { o.walk = walk; }
  var ch0 = CU.CAST[job.char]; if (ch0 && ch0.kind !== "group" && ch0.spec && ch0.spec.age) { o.age = ch0.spec.age; }   // ball@3 poses per age
  if (keys.length) { o.keys = CU.layerLife(rig, keys, dur, o); }
  if (job.member === null || job.member === undefined) {   // a lead is never quite still (measured 2026-11-27)
    var h0 = (o.headRot && o.headRot.length) ? o.headRot[0][1] : 0, hr = [[0, h0]], ht;
    for (ht = 0.9, i = 0; ht < dur - 0.3; ht += 1.3 + 0.4 * ((i * 7) % 3) / 2, i++) { hr.push([ht, h0 + (i % 2 ? -3 : 3)]); }
    if (!o.headRot || o.headRot.length < 2) { o.headRot = hr; }
  }
  return o;
};

// the pen moves while a character writes (the reference's judge writes all through her shots)
CU.layerLife = function (rig, keys, dur, o) {
  var out = [], i, t;
  for (i = 0; i < keys.length; i++) {
    out.push(keys[i]);
    if (keys[i][1].pose !== "write") { continue; }
    var p = rig.pose ? rig.pose("write", o.dir || 1, o.age) : null, end = i + 1 < keys.length ? keys[i + 1][0] : dur, n = 0;
    if (!p || !p.HR) { continue; }
    for (t = keys[i][0] + 0.35; t < end - 0.2; t += 0.22, n++) {
      out.push([t, { HR: [p.HR[0] + (n % 2 ? 30 : -22), p.HR[1] + (n % 3 === 0 ? 10 : -8)] }]);
    }
  }
  return out;
};

// the reference way of acting (charisma-30, 2026-11-27): hold still between moves, each move anticipates, overshoots, settles
CU.punchKeys = function (rig, keys, dir, age) {   // age: ball@3 (specs/040); older rigs ignore it
  var out = [], prev = null, lastT = -1, i, k;
  var mix = function (a, b, u) { return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u]; };
  for (i = 0; i < (keys || []).length; i++) {
    var t = keys[i][0], v = keys[i][1], ps = v.pose ? rig.pose(v.pose, dir, age) : null, p = ps ? { HL: v.HL || ps.HL, HR: v.HR || ps.HR } : null;
    if (prev && p && t - 0.14 > lastT + 0.04) {
      out.push([t - 0.14, { HL: mix(prev.HL, p.HL, -0.15), HR: mix(prev.HR, p.HR, -0.15), crouch: 0.07 }]);
      out.push([t, { HL: mix(prev.HL, p.HL, 1.12), HR: mix(prev.HR, p.HR, 1.12), crouch: -0.03 }]);
      var fin = {}; for (k in v) { if (v.hasOwnProperty(k) && k !== "pose") { fin[k] = v[k]; } }
      fin.HL = p.HL; fin.HR = p.HR; if (fin.crouch === undefined) { fin.crouch = 0; }
      out.push([t + 0.14, fin]); lastT = t + 0.14;
    } else { out.push(keys[i]); lastT = t; }
    if (p) { prev = p; }
  }
  return out;
};
CU.holdStill = function (P) {   // strips the rig's idle breathing and head sway (ball rig expressions)
  var b = P.body, h = P.head;
  if (b && CU.pos(b).expression) { CU.pos(b).expression = CU.pos(b).expression.replace("(1-on)*Math.sin(time*2.1)*3", "0"); }
  if (h && CU.rot(h).expression) { CU.rot(h).expression = CU.rot(h).expression.replace(/\(1-on\)\*Math\.sin\(time\*1\.3\+[^)]*\)\*1\.6/, "0"); }
  return P;
};

CU.layerComp = function (job) {
  var id = job.char, ch = CU.CAST[id];
  if (!ch) { throw new Error("no character " + id + " in cast/cast.json"); }
  var rig = CU.rig(ch.rig), sz = rig.size, S = job.size;
  var o = CU.layerOptions(rig, job);
  if (job.member !== null && job.member !== undefined) { o.member = job.member; }
  var act = job.idle !== true && rig.pose;           // job.idle: true keeps the rig's idle sway (the old way)
  if (act && o.keys) { o.keys = CU.punchKeys(rig, o.keys, o.dir || 1, ch.kind === "group" ? null : (ch.spec || {}).age); }
  var P = CU.char(id, o);
  if (act) { CU.holdStill(P); }
  var c = app.project.items.addComp("L " + job.name, S, S, 1, job.frames / CU.FPS, CU.FPS);
  var L = c.layers.add(P.comp); L.name = "B " + job.name;
  var s = CU.LAYER_FILL * S / (sz.fy - (sz.headY - sz.R));
  CU.anc(L).setValue([sz.fx, sz.fy]); CU.pos(L).setValue([S / 2, S * CU.LAYER_FEET]);
  CU.scl(L).setValue([s * 100, s * 100]);
  try { L.collapseTransformation = true; } catch (e) { }   // vectors stay sharp at any size
  return c;
};
