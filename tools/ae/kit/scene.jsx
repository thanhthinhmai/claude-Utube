// Shared After Effects kit of the studio (specs/031). Moved from films/ae-crayon-test/ae/scene.jsx on 2026-11-23.
// Paths come from CU.WORK (the folder the entry script runs in); film data lives in CU.WORK/data/.
// scene.jsx: staging declarations and automatic logic checks (prototype).
// A shot declares its floor, props with boxes and anchor points, how each person is supported, who speaks each
// bubble or caption, and roles; CU.sceneCheck() samples the timeline and reports broken staging rules.

CU.META = {};      // person comp name -> rig geometry (filled by CU.person / CU.robot)
CU.SC = null;      // the scene being declared
CU.CHECKS = [];    // all issues of the build: [shot, rule, detail]

CU.sceneBegin = function (comp, shot, o) {
  o = o || {};
  CU.SC = { comp: comp, shot: shot, floor: null, persons: [], props: {}, pointers: [], attach: [], rests: [], roles: o.roles || null, standing: o.standing || {} };
};
CU.floor = function (top, horizon) { if (CU.SC) { CU.SC.floor = { top: top, horizon: horizon }; } };
// prop: {box:[x0,y0,x1,y1], layer, kind:'occluder'|'surface'|'seat', top (surface y), seat:[x,y]}
CU.prop = function (name, o) { if (CU.SC) { CU.SC.props[name] = o; } };
CU.support = function (person, spec) { var p = CU.findP(person); if (p) { p.support = spec; } };
CU.role = function (person, role) { var p = CU.findP(person); if (p) { p.role = role; } };
CU.pointer = function (kind, pt, speaker, t0, t1, space) { if (CU.SC) { CU.SC.pointers.push({ kind: kind, pt: pt, speaker: speaker, t0: t0, t1: t1, space: space || "scene" }); } };
CU.attachTo = function (what, pt, propName, space, person) { if (CU.SC) { CU.SC.attach.push({ what: what, pt: pt, prop: propName, space: space || "scene", person: person }); } };
CU.restsOn = function (what, bottom, x, propName) { if (CU.SC) { CU.SC.rests.push({ what: what, bottom: bottom, x: x, prop: propName }); } };
CU.fits = function (what, layer, box) { if (CU.SC) { CU.SC.fits = CU.SC.fits || []; CU.SC.fits.push({ what: what, layer: layer, box: box }); } };
CU.handsAt = function (p, t) { // scene positions of both hands at time t (arm pose keys, rig geometry)
  var m = p.meta, out = [], sides = [["l", -1], ["r", 1]], k, g = CU.geo(p, t), top = CU.FEET[1] - m.legLen - m.bodyH;
  for (k = 0; k < 2; k++) {
    var list = (m.arms && m.arms[sides[k][0]]) ? m.arms[sides[k][0]] : [[0, "down"]], pose = list[0][1], j;
    for (j = 0; j < list.length; j++) { if (list[j][0] <= t) { pose = list[j][1]; } }
    CU.HANDY = m.handY;
    var h = CU.armPts(pose, sides[k][1], CU.FEET[0], top, m.R, m.dir)[2];
    CU.HANDY = null;
    out.push({ side: sides[k][0], pose: pose, pt: [g.feet[0] + (h[0] - CU.FEET[0]) * g.s, g.feet[1] + (h[1] - CU.FEET[1]) * g.s] });
  }
  return out;
};
CU.findP = function (name) {
  var i; if (!CU.SC) { return null; }
  for (i = 0; i < CU.SC.persons.length; i++) { if (CU.SC.persons[i].name === name) { return CU.SC.persons[i]; } }
  return null;
};
CU.issue = function (rule, detail) { CU.CHECKS.push([CU.SC.shot, rule, detail]); CU.say("CHECK " + CU.SC.shot + " " + rule + " " + detail); };

// scene (pre-camera) position of a layer at time t
CU.scenePos = function (L, t) {
  var v = L.property("ADBE Transform Group").property("ADBE Position").valueAtTime(t, false);
  if (L.parent && L.parent.name === "CAM") {
    var a = L.parent.property("ADBE Transform Group").property("ADBE Anchor Point").value;
    return [v[0] - a[0] + L.containingComp.width / 2, v[1] - a[1] + L.containingComp.height / 2];
  }
  return [v[0], v[1]];
};
CU.camAt = function (comp, t) {
  var i;
  for (i = 1; i <= comp.numLayers; i++) {
    if (comp.layer(i).name === "CAM") {
      var L = comp.layer(i);
      return { p: L.property("ADBE Transform Group").property("ADBE Position").valueAtTime(t, false), s: L.property("ADBE Transform Group").property("ADBE Scale").valueAtTime(t, false)[0] / 100 };
    }
  }
  return { p: [comp.width / 2, comp.height / 2], s: 1 };
};
CU.toScreen = function (comp, pt, t) { var c = CU.camAt(comp, t); return [c.p[0] + c.s * (pt[0] - comp.width / 2), c.p[1] + c.s * (pt[1] - comp.height / 2)]; };
CU.inView = function (comp, sp) { var x0 = comp.width / 2 - 960; return sp[0] >= x0 && sp[0] <= x0 + 1920 && sp[1] >= 0 && sp[1] <= 1080; };

CU.geo = function (p, t) { // feet, head centre, head radius in scene coordinates
  var m = p.meta, pos = CU.scenePos(p.layer, t), s = p.layer.property("ADBE Transform Group").property("ADBE Scale").valueAtTime(t, false)[0] / 100;
  var up = (m.legLen + m.bodyH + 0.62 * m.R) * s;
  return { feet: pos, head: [pos[0] + m.dir * 0.06 * m.R * s, pos[1] - up], r: m.R * s, s: s, body: [pos[1] - (m.legLen + m.bodyH) * s, pos[1] - m.legLen * s] };
};
CU.inBox = function (pt, b, pad) { pad = pad || 0; return pt[0] >= b[0] - pad && pt[0] <= b[2] + pad && pt[1] >= b[1] - pad && pt[1] <= b[3] + pad; };
CU.above = function (La, Lb) { return La.index < Lb.index; }; // AE: a lower index draws on top

// Layout snap: corrections measured against the reference ([dx, dy, ratio] on screen at time t), applied to the
// person's keys before the camera is attached. CU.SNAPS = {"S7": {"aud0": [dx, dy, ratio, t], ...}, ...}
CU.SNAPS = null;
CU.applySnaps = function (comp, frames) {
  if (!CU.SC || CU.SC.comp !== comp) { return; }
  if (CU.SNAPS === null) { var f = new File(CU.WORK + "/data/snaps.json"); CU.SNAPS = f.exists ? CU.readJSON(f.fsName) : {}; }
  var sn = CU.SNAPS["S" + CU.CUR_SHOT], i, cam = CU.camLinear(frames);
  if (!sn) { return; }
  for (i = 0; i < CU.SC.persons.length; i++) {
    var p = CU.SC.persons[i], c2 = sn[p.name]; if (!c2) { continue; }
    var z = cam(c2[3])[2], m = p.meta, L = p.layer, sP = CU.scl(L), s0 = sP.value[0] / 100, s1 = s0 * c2[2];
    var up0 = (m.legLen + m.bodyH + 0.62 * m.R) * s0, up1 = (m.legLen + m.bodyH + 0.62 * m.R) * s1;
    // contact beats layout: people standing, sitting or hidden behind furniture keep their feet/hips; only people cut by
    // the frame (no contact on screen) take the vertical correction
    var sup = p.support || (m.legs ? "floor" : "none"), keepFeet = c2[4] || sup !== "offscreen";
    var dx = c2[0] / z, dy = keepFeet ? 0 : c2[1] / z + (up1 - up0), pos = CU.pos(L), k;
    if (CU.SC.attach) { var q3; for (q3 = 0; q3 < CU.SC.attach.length; q3++) { if (CU.SC.attach[q3].person === p.name) { dx = 0; } } } // tied to a prop: stay
    sP.setValue([s1 * 100, s1 * 100]);
    if (pos.numKeys > 0) { for (k = 1; k <= pos.numKeys; k++) { var v = pos.keyValue(k); pos.setValueAtKey(k, [v[0] + dx, v[1] + dy]); } }
    else { var v2 = pos.value; pos.setValue([v2[0] + dx, v2[1] + dy]); }
    if (p.armsLayer) { CU.scl(p.armsLayer).setValue([s1 * 100, s1 * 100]); var pa = CU.pos(p.armsLayer); if (pa.numKeys > 0) { for (k = 1; k <= pa.numKeys; k++) { var va = pa.keyValue(k); pa.setValueAtKey(k, [va[0] + dx, va[1] + dy]); } } else { var vb = pa.value; pa.setValue([vb[0] + dx, vb[1] + dy]); } }
    CU.say("snap S" + CU.CUR_SHOT + " " + p.name + " d=(" + Math.round(c2[0]) + "," + Math.round(c2[1]) + ") x" + c2[2].toFixed(2));
  }
};
CU.exportHeads = function () { // on-screen head of every person at 3 moments -> heads_S<n>.json (for the snap tool)
  var S = CU.SC, c = S.comp, D = c.duration, T = [D * 0.12, D * 0.5, D * 0.88], out = [], i, k;
  for (i = 0; i < S.persons.length; i++) {
    var p = S.persons[i], rows = [];
    for (k = 0; k < T.length; k++) { var g = CU.geo(p, T[k]), h = CU.toScreen(c, g.head, T[k]), z = CU.camAt(c, T[k]).s; rows.push([T[k], h[0] - (c.width / 2 - 960), h[1], g.r * z]); }
    out.push('{"name":"' + p.name + '","skin":"' + (p.meta.skin || "") + '","tracked":' + (p.tracked ? "true" : "false") + ',"heads":[' + rows.join("],[").replace(/^/, "[") + ']]}');
  }
  var f = new File(CU.WORK + "/data/heads/S" + CU.CUR_SHOT + ".json"); f.encoding = "UTF-8"; f.open("w"); f.write("[" + out.join(",") + "]"); f.close();
};
CU.sceneCheck = function () {
  try { CU.exportHeads(); } catch (eh) { CU.say("export heads failed: " + eh.toString()); }
  var S = CU.SC, c = S.comp, D = c.duration, T = [0.05, D / 2, D - 0.05], i, k;
  var depth = [];
  for (i = 0; i < S.persons.length; i++) {
    var p = S.persons[i], m = p.meta, sup = p.support || (m.legs ? "floor" : "none");
    for (k = 0; k < T.length; k++) {
      var g = CU.geo(p, T[k]), tag = p.name + " @" + T[k].toFixed(1) + "s";
      if (sup === "none") { CU.issue("support", tag + ": no legs and no declared support (floating body)"); break; }
      if (sup === "floor") {
        if (!S.floor) { CU.issue("support", tag + ": stands on a floor the set never declares"); break; }
        if (!m.legs) { CU.issue("support", tag + ": declared on the floor but has no legs"); break; }
        if (g.feet[1] < S.floor.top - 6) { CU.issue("support", tag + ": feet at y=" + Math.round(g.feet[1]) + " above the floor line " + S.floor.top + " (floating)"); break; }
      } else if (sup.indexOf("hidden:") === 0 || sup.indexOf("seat:") === 0 || sup.indexOf("on:") === 0) {
        var pn = sup.split(":")[1], pr = S.props[pn];
        if (!pr) { CU.issue("support", tag + ": support prop '" + pn + "' is not declared"); break; }
        if (sup.indexOf("hidden:") === 0) {
          var hip = [g.feet[0], g.body[1]];
          if (!CU.inView(c, CU.toScreen(c, g.head, T[k]))) { continue; }   // not on screen yet: nothing to hide
          if (!CU.inBox(hip, pr.box, 8)) { CU.issue("occlusion", tag + ": body bottom (" + Math.round(hip[0]) + "," + Math.round(hip[1]) + ") is not behind '" + pn + "' " + pr.box.join(",")); break; }
          if (pr.layer && !CU.above(pr.layer, p.layer)) { CU.issue("occlusion", tag + ": '" + pn + "' is drawn behind the person, so it cannot hide the body"); break; }
        } else if (sup.indexOf("seat:") === 0) {
          if (Math.abs(g.body[1] - pr.seat[1]) > 0.4 * g.r || Math.abs(g.feet[0] - pr.seat[0]) > pr.seatW) { CU.issue("seat", tag + ": body bottom y=" + Math.round(g.body[1]) + " is not on the seat of '" + pn + "' (y=" + pr.seat[1] + ")"); break; }
        } else {
          if (Math.abs(g.feet[1] - pr.top) > 8) { CU.issue("support", tag + ": feet y=" + Math.round(g.feet[1]) + " but the top of '" + pn + "' is y=" + Math.round(pr.top) + (g.feet[1] > pr.top ? " (sunk into it)" : " (floating above it)")); break; }
        }
      } else if (sup === "offscreen") {
        var sp = CU.toScreen(c, [g.feet[0], g.body[1]], T[k]);
        if (sp[1] < 1080 - 4) { CU.issue("support", tag + ": declared cut by the frame but the body bottom is visible at screen y=" + Math.round(sp[1]) + " (floating)"); break; }
      }
      var hs = CU.toScreen(c, g.head, T[k]);
      if (k === 1 && !CU.inView(c, hs) && !p.offstage) { CU.issue("framing", tag + ": head centre is outside the frame"); }
    }
    if (sup === "floor" && S.floor && S.floor.horizon !== undefined) {
      var g0 = CU.geo(p, D / 2); depth.push([p.name, g0.s / Math.max(1, g0.feet[1] - S.floor.horizon)]);
    }
    // walking: legs move only while the person travels, and in the facing direction
    if (m.walk) {
      var steps = 6, moving = 0, still = 0, j, w0 = m.walkWindow ? m.walkWindow[0] : 0, w1 = m.walkWindow ? Math.min(D, m.walkWindow[1]) : D;
      for (j = 0; j < steps; j++) {
        var ta = w0 + (w1 - w0) * j / steps, tb = w0 + (w1 - w0) * (j + 1) / steps, dx = CU.scenePos(p.layer, tb)[0] - CU.scenePos(p.layer, ta)[0];
        if (Math.abs(dx) < 4 && !p.inPlaceOk) { still++; } else if (dx * m.dir < 0) { CU.issue("direction", p.name + ": walks backwards between " + ta.toFixed(1) + "s and " + tb.toFixed(1) + "s (moonwalk)"); break; } else { moving++; }
      }
      if (still > 0 && !p.inPlaceOk) { CU.issue("walk", p.name + ": legs keep walking while standing still in " + still + "/" + steps + " of the shot"); }
    }
  }
  // hands: never inside another person's head; a hand holding a prop must not be hidden behind furniture
  for (i = 0; i < S.persons.length; i++) {
    for (k = 0; k < T.length; k++) {
      var hs2 = CU.handsAt(S.persons[i], T[k]), h2, z2;
      for (h2 = 0; h2 < hs2.length; h2++) {
        for (z2 = 0; z2 < S.persons.length; z2++) {
          if (z2 === i) { continue; }
          var go = CU.geo(S.persons[z2], T[k]);
          if (Math.sqrt(Math.pow(hs2[h2].pt[0] - go.head[0], 2) + Math.pow(hs2[h2].pt[1] - go.head[1], 2)) < go.r * 1.05) { CU.issue("limb", S.persons[i].name + " " + hs2[h2].side + " hand (" + hs2[h2].pose + ") reaches into " + S.persons[z2].name + "'s head @" + T[k].toFixed(1) + "s"); }
        }
        var hp2 = hs2[h2].pose, holding = (S.persons[i].meta.prop === "pencil" || S.persons[i].meta.prop === "stick") && (hs2[h2].side === (S.persons[i].meta.propSide || "r"));
        if (holding || hp2 === "desk" || hp2 === "write" || hp2.indexOf("to:") === 0) {
          var pn3;
          for (pn3 in S.props) {
            if (!S.props.hasOwnProperty(pn3)) { continue; }
            var oc = S.props[pn3];
            if (oc.layer && CU.above(oc.layer, S.persons[i].armsLayer || S.persons[i].layer) && CU.inBox(hs2[h2].pt, oc.box, -2)) { CU.issue("grip", S.persons[i].name + " " + hs2[h2].side + " hand (" + hp2 + (holding ? ", holding a " + S.persons[i].meta.prop : "") + ") is covered by '" + pn3 + "' at (" + Math.round(hs2[h2].pt[0]) + "," + Math.round(hs2[h2].pt[1]) + ")"); }
          }
        }
      }
    }
  }
  // people standing in front of furniture must not be drawn behind it
  var pn2;
  for (i = 0; i < S.persons.length; i++) {
    var pf = S.persons[i]; if ((pf.support || (pf.meta.legs ? "floor" : "none")) !== "floor") { continue; }
    var gf = CU.geo(pf, D - 0.05), bw3 = gf.r * 0.95;
    for (pn2 in S.props) {
      if (!S.props.hasOwnProperty(pn2)) { continue; }
      var pb = S.props[pn2];
      if (!pb.layer || !CU.above(pb.layer, pf.layer)) { continue; }
      if (gf.feet[0] + bw3 > pb.box[0] && gf.feet[0] - bw3 < pb.box[2] && gf.body[0] < pb.box[3] && gf.feet[1] > pb.box[3] - 25) { CU.issue("layering", pf.name + " stands level with the front of '" + pn2 + "' (feet y=" + Math.round(gf.feet[1]) + ") but the furniture is drawn over the body"); }
    }
  }
  // people hidden by the same seat sit at the same height
  var bySeat = {};
  for (i = 0; i < S.persons.length; i++) { var su = S.persons[i].support || ""; if ((su.indexOf("hidden:") === 0 || su.indexOf("seat:") === 0) && S.props[su.split(":")[1]] && S.props[su.split(":")[1]].seat) { (bySeat[su] = bySeat[su] || []).push(S.persons[i]); } }
  for (pn2 in bySeat) {
    if (!bySeat.hasOwnProperty(pn2) || bySeat[pn2].length < 2) { continue; }
    var ys = [], z3; for (z3 = 0; z3 < bySeat[pn2].length; z3++) { ys.push([bySeat[pn2][z3].name, CU.geo(bySeat[pn2][z3], D / 2).body[1]]); }
    ys.sort(function (a1, b1) { return a1[1] - b1[1]; });
    if (ys[ys.length - 1][1] - ys[0][1] > 30) { CU.issue("seat", ys[0][0] + " sits " + Math.round(ys[ys.length - 1][1] - ys[0][1]) + " px higher than " + ys[ys.length - 1][0] + " on the same seat"); }
  }
  // labels must fit inside their sign or banner
  if (S.fits) {
    for (i = 0; i < S.fits.length; i++) {
      var ft = S.fits[i], rc = ft.layer.sourceRectAtTime(0, false), lp = CU.scenePos(ft.layer, 0);
      var tx0 = lp[0] + rc.left, tx1 = tx0 + rc.width, ty0 = lp[1] + rc.top, ty1 = ty0 + rc.height;
      if (tx0 < ft.box[0] - 2 || tx1 > ft.box[2] + 2 || ty0 < ft.box[1] - 2 || ty1 > ft.box[3] + 2) { CU.issue("text-fit", ft.what + ": text spans x " + Math.round(tx0) + "-" + Math.round(tx1) + ", y " + Math.round(ty0) + "-" + Math.round(ty1) + " outside its box " + ft.box.join(",")); }
    }
  }
  // nearer people (feet lower on the floor) must be drawn over farther ones when they overlap
  var fl = [];
  for (i = 0; i < S.persons.length; i++) { var pp = S.persons[i]; if ((pp.support || (pp.meta.legs ? "floor" : "none")) === "floor") { fl.push(pp); } }
  for (i = 0; i < fl.length; i++) {
    for (k = 0; k < fl.length; k++) {
      if (i === k) { continue; }
      var gi = CU.geo(fl[i], D / 2), gk = CU.geo(fl[k], D / 2);
      if (gi.feet[1] > gk.feet[1] + 10 && Math.abs(gi.feet[0] - gk.feet[0]) < (gi.r + gk.r) * 1.2 && !CU.above(fl[i].layer, fl[k].layer)) {
        CU.issue("layering", fl[i].name + " stands nearer than " + fl[k].name + " but is drawn behind it");
      }
    }
  }
  // people must not merge into one shape (heads or bodies overlapping heavily)
  for (i = 0; i < S.persons.length; i++) {
    for (k = i + 1; k < S.persons.length; k++) {
      var hit = 0, tt2;
      for (tt2 = 0; tt2 < 8; tt2++) {
        var tm = D * (tt2 + 0.5) / 8, ga = CU.geo(S.persons[i], tm), gb = CU.geo(S.persons[k], tm);
        if (CU.opa(S.persons[i].layer).valueAtTime(tm, false) < 1 || CU.opa(S.persons[k].layer).valueAtTime(tm, false) < 1) { continue; } // hidden at this moment
        var dxh = Math.abs(ga.head[0] - gb.head[0]), dyh = Math.abs(ga.head[1] - gb.head[1]);
        if (dxh < (ga.r + gb.r) * 0.8 && dyh < (ga.r + gb.r) * 0.9) { hit++; }
      }
      if (hit >= 2) { CU.issue("crowding", S.persons[i].name + " and " + S.persons[k].name + " overlap into one shape in " + hit + "/8 of the shot"); }
    }
  }
  // people standing on the same floor: size must follow depth
  if (depth.length > 1) {
    var lo = depth[0], hi = depth[0];
    for (i = 1; i < depth.length; i++) { if (depth[i][1] < lo[1]) { lo = depth[i]; } if (depth[i][1] > hi[1]) { hi = depth[i]; } }
    if (hi[1] / lo[1] > 1.15) { CU.issue("depth", hi[0] + " is " + (hi[1] / lo[1]).toFixed(2) + "x too big for its depth next to " + lo[0] + " (sizes do not follow the floor perspective)"); }
  }
  // bubble tails and caption ticks: end above the speaker's head and over it
  for (i = 0; i < S.pointers.length; i++) {
    var q = S.pointers[i], sp2 = CU.findP(q.speaker);
    if (!sp2) { CU.issue("pointer", q.kind + ": speaker '" + q.speaker + "' is not in the shot"); continue; }
    var tq = Math.min(D - 0.05, q.t0 + 0.3), gq = CU.geo(sp2, tq), hd = gq.head, rr = gq.r;
    if (q.space === "screen") { hd = CU.toScreen(c, gq.head, tq); rr = gq.r * CU.camAt(c, tq).s; }
    var ht = sp2.meta.hairTop || 1;
    var dTip = Math.sqrt(Math.pow(q.pt[0] - hd[0], 2) + Math.pow((q.pt[1] - hd[1]) / ht, 2));
    if (dTip < rr * 1.02) { CU.issue("pointer", q.kind + " for " + q.speaker + ": the tip (" + Math.round(q.pt[0]) + "," + Math.round(q.pt[1]) + ") pokes into the head or hair"); }
    else if (q.pt[1] > hd[1]) { CU.issue("pointer", q.kind + " for " + q.speaker + ": the tip points below the head centre (y=" + Math.round(q.pt[1]) + ")"); }
    else if (Math.abs(q.pt[0] - hd[0]) > 1.6 * rr) { CU.issue("pointer", q.kind + " for " + q.speaker + ": points to x=" + Math.round(q.pt[0]) + ", not over the speaker (head x=" + Math.round(hd[0]) + ")"); }
    if (q.box) {
      var hb = [hd[0] - rr * 1.1, hd[1] - rr * ht, hd[0] + rr * 1.1, hd[1] + rr];
      if (q.tickStart && (q.tickStart[0] < q.box[0] - 30 || q.tickStart[0] > q.box[2] + 30 || q.tickStart[1] < q.box[1] || q.tickStart[1] > q.box[3] + 30)) { CU.issue("pointer", q.kind + ": its tick starts at (" + Math.round(q.tickStart[0]) + "," + Math.round(q.tickStart[1]) + "), away from its own text " + q.box.join(",")); }
      if (q.box[0] < hb[2] && q.box[2] > hb[0] && q.box[1] < hb[3] && q.box[3] > hb[1]) { CU.issue("pointer", q.kind + " for " + q.speaker + ": the text box covers the speaker's head"); }
    }
  }
  // speech bubbles and captions stay inside the frame while they are shown
  var bb = S.bubbles || [], tb;
  for (i = 0; i < bb.length; i++) {
    for (tb = 0; tb < 3; tb++) {
      var tt = bb[i].t0 + (D - bb[i].t0) * (0.1 + 0.4 * tb), bl = null, q8;
      for (q8 = 1; q8 <= c.numLayers; q8++) { if (c.layer(q8).name === bb[i].name) { bl = c.layer(q8); } }
      if (bl && (tt < bl.inPoint || tt >= bl.outPoint || CU.opa(bl).valueAtTime(tt, false) < 1)) { continue; }   // hidden at this moment
      var a1 = CU.toScreen(c, [bb[i].box[0], bb[i].box[1]], tt), a2 = CU.toScreen(c, [bb[i].box[2], bb[i].box[3]], tt), x0f = c.width / 2 - 960;
      if (a1[0] < x0f - 2 || a1[1] < -2 || a2[0] > x0f + 1922 || a2[1] > 1082) { CU.issue("frame", "bubble " + bb[i].name + " is cut by the frame edge @" + tt.toFixed(1) + "s"); break; }
    }
  }
  for (i = 0; i < S.pointers.length; i++) {
    var pq = S.pointers[i];
    if (pq.space === "screen" && pq.box && (pq.box[0] < -2 || pq.box[1] < -2 || pq.box[2] > 1922 || pq.box[3] > 1082)) { CU.issue("frame", pq.kind + ": text runs past the frame edge"); }
  }
  // attachments: the point must lie on the prop it belongs to
  for (i = 0; i < S.attach.length; i++) {
    var a = S.attach[i], pr2 = S.props[a.prop], pt = a.pt;
    if (a.space === "person") { var gp = CU.findP(a.person), gg = CU.geo(gp, 0.05); pt = [gg.feet[0] + (a.pt[0] - CU.FEET[0]) * gg.s, gg.feet[1] + (a.pt[1] - CU.FEET[1]) * gg.s]; }
    if (!pr2) { CU.issue("attach", a.what + ": prop '" + a.prop + "' is not declared"); continue; }
    if (!CU.inBox(pt, pr2.box, 6)) { CU.issue("attach", a.what + ": anchored at (" + Math.round(pt[0]) + "," + Math.round(pt[1]) + "), not on '" + a.prop + "' " + pr2.box.join(",") + " (hanging in the air)"); }
  }
  // props resting on surfaces
  for (i = 0; i < S.rests.length; i++) {
    var rs = S.rests[i], sf = S.props[rs.prop];
    if (!sf) { CU.issue("rest", rs.what + ": surface '" + rs.prop + "' is not declared"); continue; }
    if (rs.bottom < sf.box[1] - 4 || rs.bottom > sf.top + 6 || rs.x < sf.box[0] || rs.x > sf.box[2]) { CU.issue("rest", rs.what + ": bottom y=" + Math.round(rs.bottom) + " is not on the top face of '" + rs.prop + "' (y " + sf.box[1] + "-" + sf.top + ")"); }
  }
  // roles keep their left-to-right order across the sequence (screen direction)
  if (S.roles) {
    var xs = [], r;
    for (r = 0; r < S.roles.length; r++) { var pr3 = null, z; for (z = 0; z < S.persons.length; z++) { if (S.persons[z].role === S.roles[r]) { pr3 = S.persons[z]; } } if (pr3) { xs.push([S.roles[r], CU.geo(pr3, D - 0.05).feet[0]]); } }
    for (r = 1; r < xs.length; r++) { if (xs[r][1] < xs[r - 1][1]) { CU.issue("continuity", xs[r][0] + " is left of " + xs[r - 1][0] + " (screen order " + S.roles.join(" < ") + " broken)"); } }
  }
  CU.say("CHECKED " + S.shot + " persons=" + S.persons.length + " pointers=" + S.pointers.length);
  CU.SC = null;
};
