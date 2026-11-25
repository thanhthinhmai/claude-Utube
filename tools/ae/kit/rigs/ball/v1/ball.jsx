// ball.jsx, rig ball@1 (specs/034 contracts/rig.md): ball-head cartoon people (flat 2D look: glossy dark sphere head,
// big white eyes, soft-shaded hoodie, rubber-hose limbs, ball hands). Moved from films/ae-sleepless-test/ae/ballchar.jsx
// on 2026-11-25. This folder is LOCKED in tools/ae/rigs.lock: never edit it; a change that alters a picture is a new
// folder v2/ and `sh bin/studio ae rigs --lock ball@2`.
// A person is a comp "B <name>" (1000 x 1400, feet at 500, 1360) drawn at 2x. Limbs follow point controls on the CTRL
// null: HL, HR (hands), FL, FR (feet). Films call it through CU.char(id, o) or CU.rig("ball@1").make(o).
CU.RIGS = CU.RIGS || {};
CU.RIGS["ball@1"] = function (CU) {
  var K = {};

  K.BW = 1000; K.BH = 1400; K.BFX = 500; K.BFY = 1360;
  K.BALL = { R: 230, headY: 330, torsoTop: 540, torsoBot: 880, shY: 600, shX: 150, arm: 340, leg: 470, hipX: 62 };

  K.num = function (v) { return Math.round(v * 100) / 100; };
  K.arr = function (a) { var s = "[", i; for (i = 0; i < a.length; i++) { s += (i ? "," : "") + (a[i] instanceof Array ? K.arr(a[i]) : (typeof a[i] === "string" ? "\"" + a[i] + "\"" : K.num(a[i]))); } return s + "]"; };

  K.ptCtl = function (L, name, v) {
    var e = L.property("ADBE Effect Parade").addProperty("ADBE Point Control"); e.name = name;
    e.property(1).setValue(v); return e.property(1);
  };
  K.slCtl = function (L, name, v) {
    var e = L.property("ADBE Effect Parade").addProperty("ADBE Slider Control"); e.name = name;
    e.property(1).setValue(v); return e.property(1);
  };

  // blink times: every 2.2-4.2 s, seeded
  K.blinks = function (dur, seed) {
    var r = CU.rand(seed || 3), t = 0.6 + r() * 1.5, out = [];
    while (t < dur) { out.push(K.num(t)); t += 2.2 + r() * 2.0; }
    return out;
  };

  // ---------------------------------------------------------------- head (own precomp, 600 x 600, centre 300,300)
  K.ballHead = function (o) {
    var c = CU.comp("BH " + o.name, o.dur, 600, 600), R = K.BALL.R, cx = 300, cy = 300;
    var base = CU.layer(c, "sphere"); CU.ell(CU.root(base), cx, cy, 2 * R, 2 * R, { fill: o.headColor || "#17171b" });
    if (o.view !== "back") {
      // soft bounce light low on the sphere and a darker crown, clipped to the sphere (preserve transparency)
      var sh = CU.layer(c, "sphere shade"), rs = CU.root(sh);
      CU.ell(rs, cx - 40, cy + 150, 2.0 * R, 1.3 * R, { fill: "#55555c", fo: 60 });
      CU.ell(rs, cx + 70, cy - 120, 1.6 * R, 1.2 * R, { fill: "#08080a", fo: 80 });
      CU.blur(sh, 70); sh.preserveTransparency = true;
    } else {
      var sb = CU.layer(c, "sphere shade"), rsb = CU.root(sb);
      CU.ell(rsb, cx - 30, cy + 160, 2.0 * R, 1.2 * R, { fill: "#4a4a50", fo: 60 });
      CU.blur(sb, 70); sb.preserveTransparency = true;
    }
    var gl = CU.layer(c, "glint"), rg = CU.root(gl);
    CU.ell(rg, cx + 0.52 * R, cy - 0.58 * R, 0.24 * R, 0.16 * R, { fill: "#ffffff", fo: 85 });
    CU.rot(gl).setValue(0); CU.blur(gl, 4); gl.preserveTransparency = true;
    // rim of light around the silhouette (the look's soft edge light)
    var rim = CU.layer(c, "rim"), rr = CU.root(rim);
    CU.ell(rr, cx, cy, 2 * R - 6, 2 * R - 6, { stroke: o.rimColor || "#6d6a80", sw: 10, so: 55 });
    CU.blur(rim, 6); rim.preserveTransparency = true;
    if (o.view === "back") { return { comp: c }; }

    // face: eyes, pupils, blush, mouth on one layer that slides with "look"
    var fy = cy + 6, ex = 64;
    var face = CU.layer(c, "face", [cx, fy]), rf = CU.root(face);
    var bl = CU.grp(rf, "blush");
    CU.ell(CU.inner(bl), cx - 118, fy + 78, 70, 34, { fill: "#d0607a", fo: 40 });
    CU.ell(CU.inner(bl), cx + 118, fy + 78, 70, 34, { fill: "#d0607a", fo: 40 });
    CU.opa(face).setValue(100);
    // mouth shapes: one group each; opacity picks one by time (mouth keys + talking flaps)
    var mk = o.mouth || [[0, "smile"]], my = fy + 92;
    var shapes = {
      smile: "M " + (cx - 34) + " " + my + " Q " + cx + " " + (my + 24) + " " + (cx + 34) + " " + my,
      flat: "M " + (cx - 26) + " " + (my + 8) + " L " + (cx + 26) + " " + (my + 8),
      frown: "M " + (cx - 30) + " " + (my + 16) + " Q " + cx + " " + (my - 4) + " " + (cx + 30) + " " + (my + 16),
      grin: "M " + (cx - 46) + " " + (my - 6) + " Q " + cx + " " + (my + 50) + " " + (cx + 46) + " " + (my - 6) + " Z",
      open: "M " + (cx - 26) + " " + my + " Q " + cx + " " + (my + 46) + " " + (cx + 26) + " " + my + " Z",
      o: ""
    };
    var talkE = "var w=" + K.arr(o.talk || []) + "; var on=false; for (var i=0;i<w.length;i++){ if (time>=w[i][0] && time<w[i][1]) on=true; } " +
      "var f=Math.floor(time*11); var flap = on && (Math.sin(f*2.3)+Math.sin(f*1.7+1))>-0.3; ";
    var keyE = "var k=" + K.arr(mk) + "; var cur=k[0][1]; for (var j=0;j<k.length;j++){ if (time>=k[j][0]) cur=k[j][1]; } ";
    var names = ["smile", "flat", "frown", "grin", "open", "o"], ni;
    for (ni = 0; ni < names.length; ni++) {
      var nm = names[ni], g = CU.grp(rf, "mouth " + nm), gi = CU.inner(g);
      if (nm === "o") { CU.ell(gi, cx, my + 14, 34, 40, { fill: "#5a1e2a" }); }
      else if (nm === "grin" || nm === "open") { CU.path(gi, shapes[nm], { fill: "#5a1e2a" }); CU.path(gi, "M " + (cx - 20) + " " + (my + (nm === "grin" ? 26 : 22)) + " Q " + cx + " " + (my + 12) + " " + (cx + 20) + " " + (my + (nm === "grin" ? 26 : 22)), { stroke: "#e07a8a", sw: 10, cap: 2 }); }
      else { CU.path(gi, shapes[nm], { stroke: "#d9d4dc", sw: 9, cap: 2 }); }
      var show = nm === "open" ? "(flap && cur!='grin')" : "(!flap || cur=='grin') && cur=='" + nm + "'";
      CU.xf(g).property("ADBE Vector Group Opacity").expression = talkE + keyE + "(" + show + ") ? 100 : 0;";
    }
    // eyes (white, pupils, catchlights) in one group per eye; blink squashes them
    var eyeKeys = o.eyes || [[0, 100]];
    var blinkE = "var b=" + K.arr(K.blinks(o.dur, o.seed)) + "; var s=100; for (var i=0;i<b.length;i++){ var u=(time-b[i])/0.16; if (u>0 && u<1) s=100*(1-0.93*Math.sin(Math.PI*u)); } " +
      "var k=" + K.arr(eyeKeys) + "; var e=k[0][1], lid=k[0].length>2?k[0][2]:100; for (var j=0;j<k.length;j++){ if (time>=k[j][0]) { var p=Math.min(1,(time-k[j][0])/0.2); var prev=j?k[j-1]:k[0]; e=prev[1]+(k[j][1]-prev[1])*p; var la=prev.length>2?prev[2]:100, lb=k[j].length>2?k[j][2]:100; lid=la+(lb-la)*p; } } ";
    var pupilE = "var k=" + K.arr(o.pupils || [[0, [0, 0]]]) + "; var v=k[0][1]; for (var j=0;j<k.length;j++){ if (time>=k[j][0]) { var p=Math.min(1,(time-k[j][0])/0.18); var a=j?k[j-1][1]:k[0][1]; v=[a[0]+(k[j][1][0]-a[0])*p, a[1]+(k[j][1][1]-a[1])*p]; } } ";
    var sides = [-1, 1], si;
    for (si = 0; si < 2; si++) {
      var exx = cx + sides[si] * ex, eg = CU.grp(rf, "eye " + si), ei = CU.inner(eg);
      CU.ell(ei, exx, fy, 104, 120, { fill: "#f3f2f5" });
      CU.ell(ei, exx + 6, fy + 22, 90, 80, { fill: "#dcdae4", fo: 45 });
      var pg = CU.grp(ei, "pupil"), pi = CU.inner(pg);
      CU.ell(pi, exx, fy + 6, 60, 68, { fill: "#101012" });
      CU.ell(pi, exx + 13, fy - 9, 18, 18, { fill: "#ffffff" });
      var pxf = CU.xf(pg);
      pxf.property("ADBE Vector Position").expression = pupilE + "v;";
      CU.top(ei.property(pg.propertyIndex));   // pupils over the eye white
      var exf = CU.xf(eg);
      exf.property("ADBE Vector Anchor").setValue([exx, fy + 30]); exf.property("ADBE Vector Position").setValue([exx, fy + 30]);
      exf.property("ADBE Vector Scale").expression = blinkE + "[e, s*e/100*lid/100];";
    }
    if (o.brows) { // angry or worried brows
      var bg = CU.grp(rf, "brows"), bi = CU.inner(bg), dy = o.brows === "angry" ? 1 : -1;
      CU.path(bi, "M " + (cx - 110) + " " + (fy - 80 - dy * 14) + " L " + (cx - 30) + " " + (fy - 70 + dy * 14), { stroke: "#d9d4dc", sw: 10, cap: 2 });
      CU.path(bi, "M " + (cx + 110) + " " + (fy - 80 - dy * 14) + " L " + (cx + 30) + " " + (fy - 70 + dy * 14), { stroke: "#d9d4dc", sw: 10, cap: 2 });
    }
    // look: -1 .. 1 slides the face toward the side the person turns to (3/4 view)
    var lookE = "var k=" + K.arr(o.look || [[0, 0]]) + "; var v=k[0][1]; for (var j=0;j<k.length;j++){ if (time>=k[j][0]) { var p=Math.min(1,(time-k[j][0])/0.25); p=p*p*(3-2*p); var a=j?k[j-1][1]:k[0][1]; v=a+(k[j][1]-a)*p; } } ";
    CU.pos(face).expression = lookE + "[value[0]+v*70, value[1]];";
    CU.scl(face).expression = lookE + "[100-Math.abs(v)*14, 100];";
    return { comp: c, face: face };
  };

  // ---------------------------------------------------------------- hats and hair (drawn in the person comp, on the head)
  K.ballHat = function (rt, kind, col, hx, hy, R, dir, view) {
    hy = hy - R * 0.32;   // brim above the eyes
    var c = CU.hex(col || "#3f6d4e"), dk = CU.shade(c, 0.78), lt = CU.shade(c, 1.18);
    if (kind === "beanie") {
      CU.path(rt, "M " + (hx - R * 1.04) + " " + (hy - R * 0.18) + " C " + (hx - R * 1.06) + " " + (hy - R * 1.32) + " " + (hx + R * 1.06) + " " + (hy - R * 1.32) + " " + (hx + R * 1.04) + " " + (hy - R * 0.18) + " Z", { fill: c });
      CU.path(rt, "M " + (hx - R * 0.6) + " " + (hy - R * 0.95) + " C " + (hx - R * 0.3) + " " + (hy - R * 1.08) + " " + (hx + R * 0.1) + " " + (hy - R * 1.1) + " " + (hx + R * 0.35) + " " + (hy - R * 1.02), { stroke: lt, sw: 14, cap: 2, so: 60 });
      CU.rect(rt, hx - R * 1.08, hy - R * 0.36, R * 2.16, R * 0.3, R * 0.12, { fill: dk });
      var i; for (i = -6; i <= 6; i++) { CU.path(rt, "M " + (hx + i * R * 0.15) + " " + (hy - R * 0.33) + " L " + (hx + i * R * 0.15) + " " + (hy - R * 0.1), { stroke: CU.shade(c, 0.66), sw: 5, so: 60 }); }
      CU.ell(rt, hx, hy - R * 1.02, R * 0.22, R * 0.22, { fill: dk });
    } else if (kind === "cap") {
      CU.path(rt, "M " + (hx - R * 1.0) + " " + (hy - R * 0.3) + " C " + (hx - R * 1.0) + " " + (hy - R * 1.25) + " " + (hx + R * 1.0) + " " + (hy - R * 1.25) + " " + (hx + R * 1.0) + " " + (hy - R * 0.3) + " Z", { fill: c });
      if (view !== "back") {
        CU.path(rt, "M " + (hx - R * 0.95 * dir) + " " + (hy - R * 0.32) + " Q " + (hx + R * 0.4 * dir) + " " + (hy - R * 0.5) + " " + (hx + R * 1.45 * dir) + " " + (hy - R * 0.26) + " Q " + (hx + R * 1.5 * dir) + " " + (hy - R * 0.12) + " " + (hx + R * 1.2 * dir) + " " + (hy - R * 0.1) + " Q " + (hx + R * 0.2 * dir) + " " + (hy - R * 0.2) + " " + (hx - R * 0.95 * dir) + " " + (hy - R * 0.2) + " Z", { fill: dk });
      }
      CU.ell(rt, hx, hy - R * 1.0, R * 0.16, R * 0.1, { fill: dk });
      CU.path(rt, "M " + hx + " " + (hy - R * 1.0) + " L " + hx + " " + (hy - R * 0.32), { stroke: dk, sw: 5, so: 70 });
    } else if (kind === "curly" || kind === "puffs") {
      var pts = [], n = 18, k;
      for (k = 0; k <= n; k++) { var a = (192 + 156 * k / n) * Math.PI / 180, rr = R * (k % 2 ? 1.16 : 1.06); pts.push([hx + rr * Math.cos(a), hy - R * 0.05 + rr * Math.sin(a)]); }
      pts.push([hx + R * 0.95, hy - R * 0.1]); pts.push([hx + R * 0.7, hy - R * 0.55]); pts.push([hx, hy - R * 0.75]); pts.push([hx - R * 0.7, hy - R * 0.55]); pts.push([hx - R * 0.95, hy - R * 0.1]);
      CU.path(rt, CU.smooth(pts, true, 1), { fill: c });
      if (kind === "puffs") { CU.ell(rt, hx - R * 1.05, hy - R * 0.85, R * 0.6, R * 0.6, { fill: c }); CU.ell(rt, hx + R * 1.05, hy - R * 0.85, R * 0.6, R * 0.6, { fill: c }); }
    } else if (kind === "bun") {
      CU.path(rt, "M " + (hx - R * 1.02) + " " + (hy - R * 0.05) + " C " + (hx - R * 1.1) + " " + (hy - R * 1.3) + " " + (hx + R * 1.1) + " " + (hy - R * 1.3) + " " + (hx + R * 1.02) + " " + (hy - R * 0.05) + " C " + (hx + R * 0.7) + " " + (hy - R * 0.75) + " " + (hx - R * 0.7) + " " + (hy - R * 0.75) + " " + (hx - R * 1.02) + " " + (hy - R * 0.05) + " Z", { fill: c });
      CU.ell(rt, hx, hy - R * 1.2, R * 0.62, R * 0.55, { fill: c });
    }
  };

  // ---------------------------------------------------------------- the person
  // o: {name, dur, dir:+1|-1, view:'front'|'back', hoodie, pants, shoes, hat:{kind,color}, mouth, talk, look, eyes,
  //     pupils, brows, walk:[[t0,t1,stepsPerSec,stride]], keys:[[t,{HL,HR,FL,FR,lean,crouch}]], seed, stripe, hood}
  K.ball = function (o) {
    var B = K.BALL, R = B.R, dir = o.dir || 1, fx = K.BFX, fy = K.BFY;
    var c = CU.comp("B " + o.name, o.dur, K.BW, K.BH);
    var hood = CU.hex(o.hoodie || "#d9534f"), hoodDk = CU.shade(hood, 0.8), hoodLt = CU.shade(hood, 1.15);
    var pants = o.pants || "#262b3d", shoes = o.shoes || "#f2f2f2";
    var hipY = B.torsoBot - 20;

    // controls
    var C = CU.nul(c, "CTRL", [0, 0]);
    var rest = K.ballPose("down", dir);
    K.ptCtl(C, "HL", rest.HL); K.ptCtl(C, "HR", rest.HR);
    K.ptCtl(C, "FL", [fx - 70, fy - 30]); K.ptCtl(C, "FR", [fx + 70, fy - 30]);
    K.slCtl(C, "lean", 0); K.slCtl(C, "crouch", 0);
    var walkW = K.arr(o.walk || []);
    // walk phase helper (shared text): ph = phase, on = 0..1
    var walkE = "var W=" + walkW + "; var on=0, ph=0, st=0; for (var i=0;i<W.length;i++){ var a=W[i][0], b=W[i][1]; if (time>a-0.2 && time<b+0.2){ on=Math.max(0,Math.min(1,(time-a)/0.2+1,(b-time)/0.2+1)); on=Math.min(on,1); ph=(time-a)*W[i][2]*Math.PI; st=W[i][3]; } } ";
    // body null: hips centre; bob while walking, breathe while idle, crouch and lean from sliders
    var Bd = CU.nul(c, "BODY", [fx, hipY]);
    CU.pos(Bd).expression = walkE + "var C=thisComp.layer('CTRL'); var cr=C.effect('crouch')(1); " +
      "[value[0], value[1] + cr*120 - on*Math.abs(Math.sin(ph))*22 + (1-on)*Math.sin(time*2.1)*3];";
    CU.rot(Bd).expression = walkE + "thisComp.layer('CTRL').effect('lean')(1) + on*Math.sin(ph)*2.5;";
    // contact shadow
    var Sd = CU.layer(c, "shadow"); CU.ell(CU.root(Sd), fx, fy - 6, 360, 50, { fill: "#000000", fo: 28 }); CU.blur(Sd, 12);

    // legs (rubber hose from hips to feet) and shoes
    var legs = [["L", -1], ["R", 1]], li;
    for (li = 0; li < 2; li++) {
      var side = legs[li][0], sg = legs[li][1];
      var Lg = CU.layer(c, "leg " + side), rl = CU.root(Lg);
      var lp = CU.inner(CU.path(rl, "M 0 0 L 0 100", { stroke: pants, sw: 40, cap: 2 })).property(1).property("ADBE Vector Shape");
      var footE = walkE + "var F=thisComp.layer('CTRL').effect('F" + side + "')(1); var s=" + (sg < 0 ? 0 : "Math.PI") + "; " +
        "F=[F[0] + on*st*Math.sin(ph/2*2+s)*" + dir + ", F[1] - on*Math.max(0,Math.cos(ph/2*2+s))*44];";
      K.ballLimbPath(lp, "(function(){var Bd=thisComp.layer('BODY'); return Bd.toComp(add(Bd.transform.anchorPoint,[" + (sg * B.hipX) + ",0]));})()", footE + "F", B.leg, [dir, -0.1], Lg);
      var Sh = CU.layer(c, "shoe " + side), rsh = CU.root(Sh);
      CU.path(rsh, "M -38 0 C -40 -34 10 -36 28 -18 C 52 -14 64 -4 62 8 L -38 8 Z", { fill: shoes });
      CU.rect(rsh, -40, 2, 104, 12, 6, { fill: "#9a9aa6" });
      CU.anc(Sh).setValue([0, 0]);
      CU.pos(Sh).expression = footE + "F + [0, 22];";
      CU.scl(Sh).setValue([dir * 100, 100]);
    }
    // torso (hoodie) on the body null
    var T = CU.layer(c, "torso"), rt = CU.root(T), tw = 340, tb = 370, tt = B.torsoTop, tbo = B.torsoBot;
    var tD = "M " + (fx - tw / 2) + " " + (tt + 60) + " C " + (fx - tw / 2) + " " + (tt - 10) + " " + (fx + tw / 2) + " " + (tt - 10) + " " + (fx + tw / 2) + " " + (tt + 60) +
      " L " + (fx + tb / 2) + " " + (tbo - 30) + " Q " + (fx + tb / 2) + " " + tbo + " " + (fx + tb / 2 - 30) + " " + tbo + " L " + (fx - tb / 2 + 30) + " " + tbo + " Q " + (fx - tb / 2) + " " + tbo + " " + (fx - tb / 2) + " " + (tbo - 30) + " Z";
    CU.path(rt, tD, { fill: hood });
    CU.rect(rt, fx - tb / 2, tbo - 44, tb, 44, 18, { fill: hoodDk });                      // waistband
    if (o.view !== "back") {
      if (o.stripe) { CU.rect(rt, fx - 22, tt + 20, 44, tbo - tt - 64, 0, { fill: o.stripe }); }
      if (o.tie) { CU.path(rt, "M " + (fx - 50) + " " + (tt + 6) + " L " + fx + " " + (tt + 120) + " L " + (fx + 50) + " " + (tt + 6) + " Z", { fill: "#f1f1f1" }); CU.path(rt, "M " + (fx - 14) + " " + (tt + 30) + " L " + (fx + 14) + " " + (tt + 30) + " L " + (fx + 18) + " " + (tt + 150) + " L " + fx + " " + (tt + 172) + " L " + (fx - 18) + " " + (tt + 150) + " Z", { fill: o.tie }); }
      if (o.hood !== false && !o.tie) {
        CU.path(rt, "M " + (fx - 130) + " " + (tt + 24) + " Q " + fx + " " + (tt + 120) + " " + (fx + 130) + " " + (tt + 24), { stroke: hoodDk, sw: 22, cap: 2 });   // hood rim
        CU.path(rt, "M " + (fx - 36) + " " + (tt + 70) + " L " + (fx - 42) + " " + (tt + 170) + " M " + (fx + 36) + " " + (tt + 70) + " L " + (fx + 42) + " " + (tt + 170), { stroke: "#f3f3f3", sw: 9, cap: 2 });
        CU.path(rt, "M " + (fx - 105) + " " + (tbo - 44) + " L " + (fx - 80) + " " + (tbo - 150) + " L " + (fx + 80) + " " + (tbo - 150) + " L " + (fx + 105) + " " + (tbo - 44), { stroke: hoodDk, sw: 7, so: 70 }); // pocket
      }
    } else {
      CU.path(rt, "M " + (fx - 120) + " " + (tt + 10) + " Q " + fx + " " + (tt + 200) + " " + (fx + 120) + " " + (tt + 10) + " Z", { fill: hoodDk });   // hood down the back
    }
    CU.path(rt, "M " + (fx + dir * tw / 2 - dir * 16) + " " + (tt + 70) + " L " + (fx + dir * tb / 2 - dir * 14) + " " + (tbo - 50), { stroke: hoodLt, sw: 12, cap: 2, so: 70 }); // light edge
    T.parent = Bd;

    // head precomp on the body
    var hx = fx, hy = B.headY;
    var hd = K.ballHead({ name: o.name, dur: o.dur, view: o.view, mouth: o.mouth, talk: o.talk, look: o.look, eyes: o.eyes, pupils: o.pupils, brows: o.brows, seed: o.seed, headColor: o.headColor, rimColor: o.rimColor });
    var Hd = c.layers.add(hd.comp); Hd.name = "head";
    CU.anc(Hd).setValue([300, 300 + R]); CU.pos(Hd).setValue([hx, hy + R]);
    Hd.parent = Bd;
    CU.rot(Hd).expression = walkE + "var k=" + K.arr(o.headRot || [[0, 0]]) + "; var v=k[0][1]; for (var j=0;j<k.length;j++){ if (time>=k[j][0]) { var p=Math.min(1,(time-k[j][0])/0.4); p=p*p*(3-2*p); var a=j?k[j-1][1]:k[0][1]; v=a+(k[j][1]-a)*p; } } " +
      "v + on*Math.sin(ph+0.6)*2 + (1-on)*Math.sin(time*1.3+" + (o.seed || 1) + ")*1.6;";
    if (o.hat && o.hat.kind) {
      var Ht = CU.layer(c, "hat"); K.ballHat(CU.root(Ht), o.hat.kind, o.hat.color, hx, hy, R, dir, o.view);
      Ht.parent = Hd;
    }
    // arms (rubber hose from shoulders to hands) and ball hands, over the torso
    var arms = [["L", -1], ["R", 1]], ai;
    for (ai = 0; ai < 2; ai++) {
      var as = arms[ai][0], asg = arms[ai][1];
      var Ar = CU.layer(c, "arm " + as), ra = CU.root(Ar);
      var ap = CU.inner(CU.path(ra, "M 0 0 L 0 100", { stroke: hood, sw: 54, cap: 2 })).property(1).property("ADBE Vector Shape");
      var handE = walkE + "var H=thisComp.layer('CTRL').effect('H" + as + "')(1); H=[H[0] + on*" + (-asg * 0) + "+on*Math.sin(ph+" + (asg < 0 ? "Math.PI" : "0") + ")*34*" + dir + ", H[1]];";
      K.ballLimbPath(ap, "(function(){var Bd=thisComp.layer('BODY'); return Bd.toComp(add(Bd.transform.anchorPoint,[" + (asg * B.shX) + "," + (B.shY - hipY) + "]));})()", handE + "H", B.arm, [asg * 0.8, 0.6], Ar, true);
      var Hn = CU.layer(c, "hand " + as), rh = CU.root(Hn);
      CU.ell(rh, 0, 0, 92, 92, { fill: "#16161a" });
      CU.ell(rh, 14, -16, 26, 18, { fill: "#ffffff", fo: 55 });
      var it = o.item && o.item[as];
      if (it === "pencil") {
        var pg = CU.grp(rh, "pencil"), pin = CU.inner(pg);
        CU.rect(pin, -9, -120, 18, 128, 3, { fill: "#f2c230" }); CU.path(pin, "M -9 8 L 9 8 L 0 34 Z", { fill: "#e9c9a0" }); CU.rect(pin, -9, -134, 18, 16, 4, { fill: "#e88a9a" });
        CU.xf(pg).property("ADBE Vector Rotation").setValue(-28 * dir); CU.top(rh.property(pg.propertyIndex));
      }
      CU.anc(Hn).setValue([0, 0]);
      CU.pos(Hn).expression = handE + "H;";
    }
    // overall soft shade: lighter top, darker feet (multiply, clipped to the person)
    var G = CU.solid(c, "grade", "#ffffff");
    CU.ramp(G, [fx, 300], "#ffffff", [fx, fy], "#a8a29c", false);
    G.blendingMode = BlendingMode.MULTIPLY; CU.opa(G).setValue(40); G.preserveTransparency = true;
    // keys
    var i, fk;
    for (fk in (o.fx || {})) { if (o.fx.hasOwnProperty(fk)) { C.property("ADBE Effect Parade").property(fk).property(1).expression = "add(value, (function(){ " + o.fx[fk] + " })());"; } }
    for (i = 0; o.keys && i < o.keys.length; i++) { K.bk({ ctrl: C, dir: dir }, o.keys[i][0], o.keys[i][1]); }
    return { comp: c, ctrl: C, body: Bd, head: Hd, dir: dir };
  };

  // limb path expression: rubber hose from point A to point B of length len; bend sign picks the side of the elbow/knee.
  K.ballLimbPath = function (pathProp, aExpr, bExpr, len, bend, layer, sleeve) {
    var e = "var A=" + aExpr + "; " + bExpr.replace(/(F|H)$/, "var Bp=$1;") +
      " var d=length(A,Bp); var m=(A+Bp)/2; var v=normalize(sub(Bp,A)); var n=[-v[1],v[0]]; " +
      "var P=" + K.arr(bend) + "; var sg=(n[0]*P[0]+n[1]*P[1])>=0?1:-1; var h=Math.sqrt(Math.max(0," + len + "*" + len + "-d*d))*0.5*sg; var cc=add(m, mul(n,h*2)); " +
      "createPath([A,Bp],[[0,0],mul(sub(cc,Bp),2/3)],[mul(sub(cc,A),2/3),[0,0]],false);";
    pathProp.expression = e.replace("var m=(A+Bp)/2;", "var m=mul(add(A,Bp),0.5);");
  };

  // standard hand poses in person-comp coordinates (screen left = HL)
  K.ballPose = function (name, dir) {
    var B = K.BALL, fx = K.BFX, sy = B.shY, sx = B.shX;
    var P = {
      down: { HL: [fx - sx - 40, sy + 320], HR: [fx + sx + 40, sy + 320] },
      hips: { HL: [fx - sx - 70, sy + 220], HR: [fx + sx + 70, sy + 220] },
      wave: { HL: [fx - sx - 40, sy + 320], HR: [fx + sx + 230, sy - 200] },
      waveL: { HL: [fx - sx - 160, sy - 240], HR: [fx + sx + 40, sy + 320] },
      raise: { HL: [fx - sx - 40, sy + 320], HR: [fx + sx + 50, sy - 330] },
      raiseL: { HL: [fx - sx - 50, sy - 330], HR: [fx + sx + 40, sy + 320] },
      both: { HL: [fx - sx - 180, sy - 220], HR: [fx + sx + 180, sy - 220] },
      pointR: { HL: [fx - sx - 40, sy + 320], HR: [fx + sx + 300, sy + 10] },
      pointL: { HL: [fx - sx - 300, sy + 10], HR: [fx + sx + 40, sy + 320] },
      chest: { HL: [fx - 60, sy + 170], HR: [fx + 60, sy + 170] },
      desk: { HL: [fx - 120, sy + 230], HR: [fx + 120, sy + 230] },
      write: { HL: [fx - 130, sy + 240], HR: [fx + 90, sy + 250] },
      shrug: { HL: [fx - sx - 170, sy + 60], HR: [fx + sx + 170, sy + 60] },
      chin: { HL: [fx - sx - 40, sy + 320], HR: [fx + 50, B.headY + 200] },
      yawn: { HL: [fx - sx - 40, sy + 320], HR: [fx + 10, B.headY + 120] },
      stretch: { HL: [fx - sx - 70, sy - 420], HR: [fx + sx + 70, sy - 420] },
      watch: { HL: [fx - 40, sy + 120], HR: [fx + 30, sy + 150] },
      hold: { HL: [fx - 95, sy + 200], HR: [fx + 95, sy + 200] },
      guitar: { HL: [fx - sx - 150, sy + 120], HR: [fx + 50, sy + 230] },
      eager: { HL: [fx - 40, sy + 200], HR: [fx + sx + 40, sy - 380] },
      lap: { HL: [fx - 90, sy + 260], HR: [fx + 90, sy + 260] }
    };
    return P[name] || P.down;
  };

  // key a pose: v = {pose:'name', HL, HR, FL, FR, lean, crouch}
  K.bk = function (P, t, v) {
    var C = P.ctrl, e = C.property("ADBE Effect Parade"), k;
    if (v.pose) { var ps = K.ballPose(v.pose, P.dir); if (!v.HL) { v.HL = ps.HL; } if (!v.HR) { v.HR = ps.HR; } }
    var map = ["HL", "HR", "FL", "FR", "lean", "crouch"];
    for (k = 0; k < map.length; k++) {
      if (v[map[k]] !== undefined) {
        var pr = e.property(map[k]).property(1);
        var idx = pr.addKey(t); pr.setValueAtKey(idx, v[map[k]]);
      }
    }
    for (k = 0; k < map.length; k++) {
      var pp = e.property(map[k]).property(1), j;
      for (j = 1; j <= pp.numKeys; j++) {
        var dim = pp.value instanceof Array ? 1 : 1;
        try { pp.setTemporalEaseAtKey(j, [new KeyframeEase(0, 70)], [new KeyframeEase(0, 70)]); } catch (e1) { }
      }
    }
  };

  // place a person comp in a shot: x, y = feet on screen, s = scale (0.5 = the person is 680 px tall)
  K.place = function (comp, P, x, y, s, moves) {
    var L = comp.layers.add(P.comp); L.name = P.comp.name;
    CU.anc(L).setValue([K.BFX, K.BFY]); CU.pos(L).setValue([x, y]); CU.scl(L).setValue([s * 100, s * 100]);
    if (moves) { CU.keys(CU.pos(L), moves, 0); }
    return L;
  };

  // a shape layer drawn in the person comp's coordinates and carried by the person layer (props held in the hands)
  K.carry = function (comp, personLayer, name) {
    var L = CU.layer(comp, name); L.setParentWithJump(personLayer);
    CU.anc(L).setValue([0, 0]); CU.pos(L).setValue([0, 0]); CU.scl(L).setValue([100, 100]);
    return L;
  };

  // expression presets of the cast sheet (keys of catalog.json "expressions"): options merged into make(o)
  K.EXPR = {
    smile: { mouth: [[0, "smile"]] }, grin: { mouth: [[0, "grin"]] }, flat: { mouth: [[0, "flat"]] },
    frown: { mouth: [[0, "frown"]] }, open: { mouth: [[0, "open"]] }, o: { mouth: [[0, "o"]] },
    wide: { mouth: [[0, "o"]], eyes: [[0, 125]], pupils: [[0, [0, -4]]] },
    yawn: { mouth: [[0, "o"]], eyes: [[0, 100, 30]], pose: "yawn" },
    sleepy: { mouth: [[0, "flat"]], eyes: [[0, 100, 45]] },
    angry: { mouth: [[0, "frown"]], brows: "angry" },
    worried: { mouth: [[0, "frown"]], brows: "worried", pupils: [[0, [0, 6]]] },
    surprised: { mouth: [[0, "o"]], eyes: [[0, 120]] },
    lookleft: { look: [[0, -0.8]], pupils: [[0, [-12, 0]]] },
    lookright: { look: [[0, 0.8]], pupils: [[0, [12, 0]]] }
  };
  // views: front, back, 34 (face slid toward the turn, head turned a little)
  K.VIEW = { front: {}, back: { view: "back" }, "34": { look: [[0, 0.75]], headRot: [[0, 4]] } };

  return {
    id: "ball@1",
    size: { w: K.BW, h: K.BH, fx: K.BFX, fy: K.BFY, headY: K.BALL.headY, R: K.BALL.R },
    make: K.ball, pose: K.ballPose, key: K.bk, place: K.place, carry: K.carry,
    expression: function (k) { return K.EXPR[k] || null; },
    view: function (k) { return K.VIEW[k] || null; }
  };
};
