// ball.jsx, rig ball@3 (specs/040, 2026-11-28): the sphere-head people re-drawn to the measured proportions of the
// what-if reference set (references/whatif-long/analysis/rig-measure.json: 20 figures, 15 frames, 7 videos).
// Head R 200 in the 1000 x 1400 person comp (feet 500, 1360); kid and adult 3.15 heads tall, toddler 2.14; straight
// capsule limbs (arm 0.20, leg 0.22 head widths) with a thin dark outline (6 px here = ~1.5 px at 720p) and a hard
// darker band on the screen-right side; elbows and knees are two capsules meeting at a corner (no ball joints);
// black ball hands over darker cuffs; dome shoes; hoodie with a collar ring, two drawstrings, a pocket.
// The head precomp is ball@2's (glossy, no dark outline) at 87 %, with a lighter crown and a rim wider on the right.
// LOCKED in tools/ae/rigs.lock once approved: never edit then; a change that alters a picture is a new folder v4/.
// Films call it through CU.char(id, o) or CU.rig("ball@3").make(o); o.age = "kid" (default) | "adult" | "toddler".
CU.RIGS = CU.RIGS || {};
CU.RIGS["ball@3"] = function (CU) {
  var K = {};

  K.BW = 1000; K.BH = 1400; K.BFX = 500; K.BFY = 1360;
  K.BALL = { R: 230 };            // the head precomp is drawn at R 230 and placed at HS = 200 / 230
  K.HR = 200; K.HS = 200 / 230; K.LINE = 6;
  // body geometry per age (person-comp px): head centre, torso, shoulders, hips, limb lengths and widths
  K.AGES = {
    kid: { hc: 300, tt: 470, tw: 224, tb: 892, shY: 548, shX: 90, arm: 330, hipY: 872, hipX: 46, leg: 428, aw: 70, lw: 74, hand: 84, shoe: 144, shoeH: 84 },
    adult: { hc: 300, tt: 470, tw: 268, tb: 932, shY: 552, shX: 110, arm: 350, hipY: 912, hipX: 54, leg: 388, aw: 74, lw: 78, hand: 88, shoe: 144, shoeH: 84 },
    toddler: { hc: 704, tt: 874, tw: 200, tb: 1104, shY: 940, shX: 78, arm: 200, hipY: 1090, hipX: 46, leg: 210, aw: 70, lw: 74, hand: 84, shoe: 140, shoeH: 82 }
  };
  K.geo = function (age) { return K.AGES[age] || K.AGES.kid; };

  K.num = function (v) { return Math.round(v * 100) / 100; };
  K.arr = function (a) { var s = "[", i; for (i = 0; i < a.length; i++) { s += (i ? "," : "") + (a[i] instanceof Array ? K.arr(a[i]) : (typeof a[i] === "string" ? "\"" + a[i] + "\"" : K.num(a[i]))); } return s + "]"; };
  K.ink = function (col) { return CU.shade(col, 0.32); };   // outline: near-black tinted toward the fill

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
    // measured (specs/040 R2): lighter crown, darker chin, no dark outline on the head
    var sh = CU.layer(c, "sphere shade"), rs = CU.root(sh);
    CU.ell(rs, cx - 50, cy - 140, 1.9 * R, 1.3 * R, { fill: "#4c4c55", fo: 70 });
    CU.ell(rs, cx + 30, cy + 170, 2.0 * R, 1.2 * R, { fill: "#060608", fo: 85 });
    CU.blur(sh, 80); sh.preserveTransparency = true;
    var gl = CU.layer(c, "glint"), rg = CU.root(gl);
    var rotE = function (ex, ey, rx, ry, ang) { var pts = [], a = ang * Math.PI / 180, q; for (q = 0; q < 24; q++) { var u = q / 24 * 2 * Math.PI, x = rx * Math.cos(u), y = ry * Math.sin(u); pts.push([ex + x * Math.cos(a) - y * Math.sin(a), ey + x * Math.sin(a) + y * Math.cos(a)]); } return CU.smooth(pts, true, 1); };
    CU.path(rg, rotE(cx + 0.5 * R, cy - 0.56 * R, 0.3 * R, 0.15 * R, 40), { fill: "#ffffff", fo: 55 });
    CU.path(rg, rotE(cx + 0.56 * R, cy - 0.6 * R, 0.13 * R, 0.07 * R, 40), { fill: "#ffffff", fo: 95 });
    CU.blur(gl, 5); gl.preserveTransparency = true;
    // thin brown-grey rim, wider on the screen-right side (an offset ring clipped to the sphere)
    var rim = CU.layer(c, "rim"), rr = CU.root(rim);
    CU.ell(rr, cx, cy, 2 * R - 4, 2 * R - 4, { stroke: o.rimColor || "#7a6c66", sw: 6, so: 80 });
    CU.ell(rr, cx - 8, cy, 2 * R, 2 * R, { stroke: o.rimColor || "#7a6c66", sw: 12, so: 85 });   // left of it falls outside
    CU.blur(rim, 1.5); rim.preserveTransparency = true;
    if (o.view === "back") { return { comp: c }; }

    // face: eyes, pupils, blush, mouth on one layer that slides with "look"
    var fy = cy + 6, ex = 64;
    var face = CU.layer(c, "face", [cx, fy]), rf = CU.root(face);
    var bl = CU.grp(rf, "blush");
    CU.ell(CU.inner(bl), cx - 118, fy + 78, 70, 34, { fill: "#d0607a", fo: 40 });
    CU.ell(CU.inner(bl), cx + 118, fy + 78, 70, 34, { fill: "#d0607a", fo: 40 });
    CU.xf(bl).property("ADBE Vector Group Opacity").setValue(o.blush ? 100 : 0);
    CU.opa(face).setValue(100);
    // mouth shapes: one group each; opacity picks one by time (mouth keys + talking flaps)
    var mk = o.mouth || [[0, "smile"]], my = fy + 92;
    var shapes = {
      smile: "M " + (cx - 34) + " " + my + " Q " + cx + " " + (my + 24) + " " + (cx + 34) + " " + my,
      flat: "M " + (cx - 26) + " " + (my + 8) + " L " + (cx + 26) + " " + (my + 8),
      frown: "M " + (cx - 30) + " " + (my + 16) + " Q " + cx + " " + (my - 4) + " " + (cx + 30) + " " + (my + 16),
      grin: "M " + (cx - 58) + " " + (my - 8) + " Q " + cx + " " + (my + 62) + " " + (cx + 58) + " " + (my - 8) + " Z",
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
      else if (nm === "grin" || nm === "open") { CU.path(gi, shapes[nm], { fill: "#5a1e2a" }); var ty = my + (nm === "grin" ? 34 : 26), tw = nm === "grin" ? 30 : 16;   // the tongue: a pink patch at the bottom (a stroke read as a frown at small sizes)
        CU.path(gi, "M " + (cx - tw) + " " + ty + " Q " + cx + " " + (ty - 14) + " " + (cx + tw) + " " + ty + " Q " + cx + " " + (ty + 14) + " " + (cx - tw) + " " + ty + " Z", { fill: "#e07a8a" }); }
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
      CU.ell(ei, exx, fy, 112, 126, { fill: "#f3f2f5", stroke: "#8f8d9b", sw: 7 });
      CU.ell(ei, exx + 6, fy + 22, 90, 80, { fill: "#dcdae4", fo: 45 });
      var pg = CU.grp(ei, "pupil"), pi = CU.inner(pg);
      CU.ell(pi, exx, fy + 6, 66, 74, { fill: "#101012" });
      CU.ell(pi, exx + 14, fy - 10, 22, 22, { fill: "#ffffff" });
      var pxf = CU.xf(pg);
      pxf.property("ADBE Vector Position").expression = pupilE + "v;";
      CU.top(ei.property(pg.propertyIndex));   // pupils over the eye white
      var exf = CU.xf(eg);
      exf.property("ADBE Vector Anchor").setValue([exx, fy + 30]); exf.property("ADBE Vector Position").setValue([exx, fy + 30]);
      exf.property("ADBE Vector Scale").expression = blinkE + "[e, s*e/100*lid/100];";
    }
    if (!o.brows) { // calm brows: short arcs above the eyes
      var cb = CU.grp(rf, "brows"), cbi = CU.inner(cb);
      CU.path(cbi, "M " + (cx - 104) + " " + (fy - 84) + " Q " + (cx - 66) + " " + (fy - 98) + " " + (cx - 30) + " " + (fy - 86), { stroke: "#cfccd8", sw: 9, cap: 2 });
      CU.path(cbi, "M " + (cx + 104) + " " + (fy - 84) + " Q " + (cx + 66) + " " + (fy - 98) + " " + (cx + 30) + " " + (fy - 86), { stroke: "#cfccd8", sw: 9, cap: 2 });
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

  // ---------------------------------------------------------------- limbs
  // One shape layer per limb: outline, fill, two shade bands (one per segment, offset to the screen-right/down side)
  // and a cuff, all on the same two-segment path A -> joint -> B (len split in half; bend picks the joint side).
  K.LIMB_HEAD = function (aExpr, bCode, len, bend) {
    return "var A=" + aExpr + "; var Bp=(function(){ " + bCode + " })(); " +
      "var d=length(A,Bp); var m=mul(add(A,Bp),0.5); var v=normalize(sub(Bp,A)); var n=[-v[1],v[0]]; " +
      "var P=" + K.arr(bend) + "; var sg=(n[0]*P[0]+n[1]*P[1])>=0?1:-1; var l=" + len + "/2; " +
      "var h=Math.sqrt(Math.max(0,l*l-d*d/4))*sg; var Cj=add(m,mul(n,h)); ";
  };
  K.SIDE = "function sd(p,q){ var u=normalize(sub(q,p)); var w=[-u[1],u[0]]; if (w[0]+0.6*w[1]<0) { w=[-w[0],-w[1]]; } return w; } ";
  K.limb = function (L, aExpr, bCode, len, bend, col, w, cuff) {
    var rt = CU.root(L), head = K.LIMB_HEAD(aExpr, bCode, len, bend);
    var mk = function (st, body) {
      var p = CU.inner(CU.path(rt, "M 0 0 L 0 100", st)).property(1).property("ADBE Vector Shape");
      p.expression = head + K.SIDE + body;
    };
    mk({ stroke: K.ink(col), sw: w + 2 * K.LINE, cap: 2 }, "createPath([A,Cj,Bp],[],[],false);");
    mk({ stroke: col, sw: w, cap: 2 }, "createPath([A,Cj,Bp],[],[],false);");
    var bw = Math.round(w * 0.28), off = K.num(w * 0.36);
    mk({ stroke: CU.shade(col, 0.72), sw: bw, cap: 2 }, "var o=mul(sd(A,Cj)," + off + "); createPath([add(A,o),add(Cj,o)],[],[],false);");
    mk({ stroke: CU.shade(col, 0.72), sw: bw, cap: 2 }, "var o=mul(sd(Cj,Bp)," + off + "); createPath([add(Cj,o),add(Bp,o)],[],[],false);");
    if (cuff) {   // darker cuff just above the hand
      mk({ stroke: CU.shade(col, 0.68), sw: w + 2, cap: 2 }, "var u=normalize(sub(Cj,Bp)); createPath([add(Bp,mul(u,10)),add(Bp,mul(u,34))],[],[],false);");
    }
  };

  // ---------------------------------------------------------------- the person
  // o: {name, dur, dir:+1|-1, view:'front'|'back', age, hoodie, pants, shoes, hat:{kind,color}, mouth, talk, look, eyes,
  //     pupils, brows, walk:[[t0,t1,stepsPerSec,stride]], keys:[[t,{pose,HL,HR,FL,FR,lean,crouch}]], seed, hood, item}
  K.ball = function (o) {
    var age = K.AGES[o.age] ? o.age : "kid", G = K.geo(age), dir = o.dir || 1, fx = K.BFX, fy = K.BFY;
    var c = CU.comp("B " + o.name, o.dur, K.BW, K.BH);
    var hood = CU.hex(o.hoodie || "#d9534f"), hoodDk = CU.shade(hood, 0.78);
    var pants = CU.hex(o.pants || "#2b3044");
    var shoes = CU.hex(o.shoes || (age === "adult" ? "#3b2a22" : "#f4f4f6")), sole = age === "adult" ? CU.shade(shoes, 0.7) : CU.hex("#a9a9b4");
    var tt = G.tt, tb = G.tb, tw = G.tw, hipY = G.hipY;

    // controls
    var C = CU.nul(c, "CTRL", [0, 0]);
    var rest = K.ballPose("down", dir, age);
    K.ptCtl(C, "HL", rest.HL); K.ptCtl(C, "HR", rest.HR);
    K.ptCtl(C, "FL", [fx - G.hipX - 6, fy - 60]); K.ptCtl(C, "FR", [fx + G.hipX + 6, fy - 60]);
    K.slCtl(C, "lean", 0); K.slCtl(C, "crouch", 0);
    var walkW = K.arr(o.walk || []);
    var walkE = "var W=" + walkW + "; var on=0, ph=0, st=0; for (var i=0;i<W.length;i++){ var a=W[i][0], b=W[i][1]; if (time>a-0.2 && time<b+0.2){ on=Math.max(0,Math.min(1,(time-a)/0.2+1,(b-time)/0.2+1)); on=Math.min(on,1); ph=(time-a)*W[i][2]*Math.PI; st=W[i][3]; } } ";
    var Bd = CU.nul(c, "BODY", [fx, hipY]);
    CU.pos(Bd).expression = walkE + "var C=thisComp.layer('CTRL'); var cr=C.effect('crouch')(1); " +
      "[value[0], value[1] + cr*" + Math.round(G.leg * 0.28) + " - on*Math.abs(Math.sin(ph))*18 + (1-on)*Math.sin(time*2.1)*3];";
    CU.rot(Bd).expression = walkE + "thisComp.layer('CTRL').effect('lean')(1) + on*Math.sin(ph)*2.5;";
    // soft contact shadow under the shoes
    var Sd = CU.layer(c, "shadow"); CU.ell(CU.root(Sd), fx, fy - 4, G.tw * 1.5, 46, { fill: "#000000", fo: 30 }); CU.blur(Sd, 14);

    // legs and dome shoes
    var legs = [["L", -1], ["R", 1]], li;
    for (li = 0; li < 2; li++) {
      var side = legs[li][0], sg = legs[li][1];
      var footE = walkE + "var F=thisComp.layer('CTRL').effect('F" + side + "')(1); var s=" + (sg < 0 ? 0 : "Math.PI") + "; " +
        "F=[F[0] + on*st*Math.sin(ph+s)*" + dir + ", F[1] - on*Math.max(0,Math.cos(ph+s))*40];";
      var Lg = CU.layer(c, "leg " + side);
      K.limb(Lg, "(function(){var Bd=thisComp.layer('BODY'); return Bd.toComp(add(Bd.transform.anchorPoint,[" + (sg * G.hipX) + ",-10]));})()",
        footE + "return F;", G.leg, [dir, -0.1], pants, G.lw, false);
      var Sh = CU.layer(c, "shoe " + side), rsh = CU.root(Sh), sw2 = G.shoe / 2, sh2 = G.shoeH;
      var dome = "M " + (-sw2 + 8) + " 0 C " + (-sw2 + 4) + " " + (-sh2 * 1.05) + " " + (sw2 + 4) + " " + (-sh2 * 1.1) + " " + (sw2 + 10) + " -6 L " + (sw2 + 10) + " 4 L " + (-sw2 + 8) + " 4 Z";
      CU.path(rsh, dome, { fill: shoes, stroke: K.ink(shoes), sw: K.LINE });
      CU.rect(rsh, -sw2 + 6, -10, G.shoe + 6, 16, 8, { fill: sole, stroke: K.ink(shoes), sw: K.LINE * 0.8 });
      CU.path(rsh, "M " + (-sw2 * 0.5) + " " + (-sh2 * 0.72) + " Q " + (sw2 * 0.1) + " " + (-sh2 * 0.95) + " " + (sw2 * 0.55) + " " + (-sh2 * 0.6), { stroke: "#ffffff", sw: 8, cap: 2, so: age === "adult" ? 35 : 70 });
      CU.anc(Sh).setValue([0, 0]);
      CU.pos(Sh).expression = footE + "F + [" + (dir * 8) + ", 58];";
      CU.scl(Sh).setValue([dir * 100, 100]);
    }

    // torso (hoodie or top) on the body null
    var T = CU.layer(c, "torso"), rt = CU.root(T), tw2 = tw * 0.47, tb2 = tw / 2;
    var tD = "M " + (fx - tw2) + " " + (tt + 70) + " C " + (fx - tw2) + " " + (tt - 6) + " " + (fx + tw2) + " " + (tt - 6) + " " + (fx + tw2) + " " + (tt + 70) +
      " L " + (fx + tb2) + " " + (tb - 26) + " Q " + (fx + tb2) + " " + tb + " " + (fx + tb2 - 26) + " " + tb + " L " + (fx - tb2 + 26) + " " + tb + " Q " + (fx - tb2) + " " + tb + " " + (fx - tb2) + " " + (tb - 26) + " Z";
    CU.path(rt, tD, { fill: hood, stroke: K.ink(hood), sw: K.LINE });
    CU.rect(rt, fx - tb2 + 3, tb - 34, tw - 6, 30, 12, { fill: hoodDk });                       // waistband
    if (o.view !== "back") {
      if (o.hood !== false) {
        var py = tt + (tb - tt) * 0.58, ph2 = (tb - tt) * 0.3;
        CU.path(rt, "M " + (fx - tw * 0.3) + " " + (py + ph2) + " L " + (fx - tw * 0.24) + " " + py + " L " + (fx + tw * 0.24) + " " + py + " L " + (fx + tw * 0.3) + " " + (py + ph2) + " Z",
          { fill: hoodDk, fo: 55, stroke: K.ink(hood), sw: K.LINE * 0.6, so: 50 });                // pocket
        var sy0 = G.hc + K.HR * 0.92, sl = Math.round((tb - tt) * 0.32), si;
        for (si = -1; si <= 1; si += 2) {                                                           // drawstrings
          CU.path(rt, "M " + (fx + si * 24) + " " + sy0 + " L " + (fx + si * 28) + " " + (sy0 + sl), { stroke: "#f6f6f6", sw: 8, cap: 2 });
          CU.ell(rt, fx + si * 28, sy0 + sl + 6, 13, 18, { fill: "#d6d6dc" });
        }
      }
    } else {
      CU.path(rt, "M " + (fx - tw * 0.36) + " " + (tt + 14) + " Q " + fx + " " + (tt + (tb - tt) * 0.5) + " " + (fx + tw * 0.36) + " " + (tt + 14) + " Z", { fill: hoodDk, stroke: K.ink(hood), sw: K.LINE * 0.6 });
    }
    // soft gradient top-left light to bottom-right dark, clipped to the torso
    var Tg = CU.layer(c, "torso shade"), rtg = CU.root(Tg);
    CU.ell(rtg, fx + tw * 0.45, tb, tw * 1.1, (tb - tt) * 0.9, { fill: CU.shade(hood, 0.7), fo: 70 });
    CU.ell(rtg, fx - tw * 0.4, tt + 30, tw * 0.8, (tb - tt) * 0.5, { fill: CU.shade(hood, 1.12), fo: 60 });
    CU.blur(Tg, 40);
    try { Tg.setTrackMatte(T, TrackMatteType.ALPHA); T.enabled = true; } catch (eM) { Tg.remove(); Tg = null; }   // clipped to the torso only
    T.parent = Bd; if (Tg) { Tg.parent = Bd; }
    if (o.hood !== false && o.view !== "back") {   // collar ring behind the chin (drawn before the head, over the torso)
      var Cr = CU.layer(c, "collar"); CU.ell(CU.root(Cr), fx, G.hc + K.HR * 0.86, K.HR * 1.3, K.HR * 0.42, { fill: hoodDk, stroke: K.ink(hood), sw: K.LINE });
      Cr.parent = Bd;
    }

    // head precomp on the body (no neck: the head overlaps the torso)
    var hd = K.ballHead({ name: o.name, dur: o.dur, view: o.view, mouth: o.mouth, talk: o.talk, look: o.look, eyes: o.eyes, pupils: o.pupils, brows: o.brows, blush: o.blush, seed: o.seed, headColor: o.headColor, rimColor: o.rimColor });
    var Hd = c.layers.add(hd.comp); Hd.name = "head";
    CU.anc(Hd).setValue([300, 300 + K.BALL.R]); CU.pos(Hd).setValue([fx, G.hc + K.HR]); CU.scl(Hd).setValue([K.HS * 100, K.HS * 100]);
    Hd.parent = Bd;
    CU.rot(Hd).expression = walkE + "var k=" + K.arr(o.headRot || [[0, 0]]) + "; var v=k[0][1]; for (var j=0;j<k.length;j++){ if (time>=k[j][0]) { var p=Math.min(1,(time-k[j][0])/0.4); p=p*p*(3-2*p); var a=j?k[j-1][1]:k[0][1]; v=a+(k[j][1]-a)*p; } } " +
      "v + on*Math.sin(ph+0.6)*2 + (1-on)*Math.sin(time*1.3+" + (o.seed || 1) + ")*1.6;";
    if (o.hat && o.hat.kind) {
      var Ht = CU.layer(c, "hat"); K.ballHat(CU.root(Ht), o.hat.kind, o.hat.color, fx, G.hc, K.HR, dir, o.view);
      Ht.parent = Hd;
    }
    // arms with cuffs and ball hands, over the torso
    var arms = [["L", -1], ["R", 1]], ai;
    for (ai = 0; ai < 2; ai++) {
      var as = arms[ai][0], asg = arms[ai][1];
      var Ar = CU.layer(c, "arm " + as);
      var handE = walkE + "var H=thisComp.layer('CTRL').effect('H" + as + "')(1); H=[H[0]+on*Math.sin(ph+" + (asg < 0 ? "Math.PI" : "0") + ")*30*" + dir + ", H[1]];";
      K.limb(Ar, "(function(){var Bd=thisComp.layer('BODY'); return Bd.toComp(add(Bd.transform.anchorPoint,[" + (asg * G.shX) + "," + (G.shY - hipY) + "]));})()",
        handE + "return H;", G.arm, [asg * 0.8, 0.6], hood, G.aw, true);
      var Hn = CU.layer(c, "hand " + as), rh = CU.root(Hn);
      CU.ell(rh, 0, 0, G.hand, G.hand, { fill: "#141418", stroke: "#050506", sw: K.LINE * 0.6 });
      CU.ell(rh, G.hand * 0.17, -G.hand * 0.2, G.hand * 0.3, G.hand * 0.2, { fill: "#ffffff", fo: 70 });
      var it = o.item && o.item[as];
      if (it === "pencil") {
        var pg = CU.grp(rh, "pencil"), pin = CU.inner(pg);
        CU.rect(pin, -9, -120, 18, 128, 3, { fill: "#f2c230", stroke: K.ink("#f2c230"), sw: 4 }); CU.path(pin, "M -9 8 L 9 8 L 0 34 Z", { fill: "#e9c9a0" }); CU.rect(pin, -9, -134, 18, 16, 4, { fill: "#e88a9a" });
        CU.xf(pg).property("ADBE Vector Rotation").setValue(-28 * dir); CU.top(rh.property(pg.propertyIndex));
      }
      CU.anc(Hn).setValue([0, 0]);
      CU.pos(Hn).expression = handE + "H;";
    }
    // keys
    var i, fk;
    for (fk in (o.fx || {})) { if (o.fx.hasOwnProperty(fk)) { C.property("ADBE Effect Parade").property(fk).property(1).expression = "add(value, (function(){ " + o.fx[fk] + " })());"; } }
    for (i = 0; o.keys && i < o.keys.length; i++) { K.bk({ ctrl: C, dir: dir, age: age }, o.keys[i][0], o.keys[i][1]); }
    return { comp: c, ctrl: C, body: Bd, head: Hd, dir: dir, age: age };
  };

  // standard hand poses in person-comp coordinates (screen left = HL), from ball@2's table scaled to the age's arm
  K.ballPose = function (name, dir, age) {
    var G = K.geo(age), fx = K.BFX, sy = G.shY, sx = G.shX, u = G.arm / 340, hc = G.hc, hs = K.HR / 230;
    var L = function (dx, dy) { return [fx - sx - dx * u, sy + dy * u]; };
    var R = function (dx, dy) { return [fx + sx + dx * u, sy + dy * u]; };
    var M = function (dx, dy) { return [fx + dx * u, sy + dy * u]; };
    var Hh = function (dx, dy) { return [fx + dx * hs, hc + dy * hs]; };
    var P = {
      down: { HL: L(8, 326), HR: R(8, 326) },        // arms hang almost straight
      hips: { HL: L(70, 220), HR: R(70, 220) },
      wave: { HL: L(20, 300), HR: R(230, -200) },
      waveL: { HL: L(160, -240), HR: R(20, 300) },
      raise: { HL: L(20, 300), HR: R(50, -330) },
      raiseL: { HL: L(50, -330), HR: R(20, 300) },
      both: { HL: L(180, -220), HR: R(180, -220) },
      pointR: { HL: L(20, 300), HR: R(300, 10) },
      pointL: { HL: L(300, 10), HR: R(20, 300) },
      chest: { HL: M(-60, 170), HR: M(60, 170) },
      desk: { HL: M(-120, 230), HR: M(120, 230) },
      write: { HL: M(-130, 240), HR: M(90, 250) },
      shrug: { HL: L(170, 60), HR: R(170, 60) },
      chin: { HL: L(20, 300), HR: Hh(50, 200) },
      yawn: { HL: L(20, 300), HR: Hh(10, 120) },
      stretch: { HL: L(70, -420), HR: R(70, -420) },
      watch: { HL: M(-40, 120), HR: M(30, 150) },
      hold: { HL: M(-95, 200), HR: M(95, 200) },
      guitar: { HL: L(150, 120), HR: M(50, 230) },
      eager: { HL: M(-40, 200), HR: R(40, -380) },
      lap: { HL: M(-90, 260), HR: M(90, 260) }
    };
    return P[name] || P.down;
  };

  // key a pose: v = {pose:'name', HL, HR, FL, FR, lean, crouch}
  K.bk = function (P, t, v) {
    var C = P.ctrl, e = C.property("ADBE Effect Parade"), k;
    if (v.pose) { var ps = K.ballPose(v.pose, P.dir, P.age); if (!v.HL) { v.HL = ps.HL; } if (!v.HR) { v.HR = ps.HR; } }
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
        try { pp.setTemporalEaseAtKey(j, [new KeyframeEase(0, 70)], [new KeyframeEase(0, 70)]); } catch (e1) { }
      }
    }
  };

  // place a person comp in a shot: x, y = feet on screen, s = scale
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

  K.EXPR = {
    smile: { mouth: [[0, "smile"]] }, grin: { mouth: [[0, "grin"]], blush: true }, flat: { mouth: [[0, "flat"]] },
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
  K.VIEW = { front: {}, back: { view: "back" }, "34": { look: [[0, 0.75]], headRot: [[0, 4]] } };

  var size = { w: K.BW, h: K.BH, fx: K.BFX, fy: K.BFY, headY: K.AGES.kid.hc, R: K.HR };
  return {
    id: "ball@3",
    size: size,
    sizeOf: function (spec) { var g = K.geo(spec && spec.age); return { w: K.BW, h: K.BH, fx: K.BFX, fy: K.BFY, headY: g.hc, R: K.HR }; },
    make: K.ball, pose: K.ballPose, key: K.bk, place: K.place, carry: K.carry,
    expression: function (k) { return K.EXPR[k] || null; },
    view: function (k) { return K.VIEW[k] || null; }
  };
};
