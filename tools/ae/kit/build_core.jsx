// Shared After Effects kit of the studio (specs/031). Moved from films/ae-crayon-test/ae/build_core.jsx on 2026-11-23.
// Paths come from CU.WORK (the folder the entry script runs in); film data lives in CU.WORK/data/.
// build_core.jsx: builds the listed shots into a MASTER comp, writes shot marks and saves CU.PROJ in CU.WORK.
// Log lines: START, shot … ok, CHECK …, ERR …, master …, DONE.
if (!CU.NO_MOTION) { CU.NO_MOTION = {}; }   // film files may list shots that skip the measured camera move
CU.build = function (list) {
  app.beginSuppressDialogs();
  CU.log = new File(CU.WORK + "/log.txt"); CU.log.encoding = "UTF-8"; CU.log.open("w"); CU.say("START");
  try {
    app.newProject();
    var shots = [], total = 0, i;
    for (i = 0; i < list.length; i++) {
      var t0 = new Date().getTime();
      CU.CUR_SHOT = list[i];
      try { var sc = CU["shot" + list[i]](); shots.push(sc); total += sc.duration; CU.say("shot " + list[i] + " ok " + (new Date().getTime() - t0) + " ms");
        if (CU.SC) { try { CU.sceneCheck(); } catch (e3) { CU.say("ERR check " + list[i] + ": " + e3.toString() + " line " + e3.line); CU.SC = null; } } }
      catch (e) { CU.say("ERR shot " + list[i] + ": " + e.toString() + " line " + e.line); }
    }
    var M = CU.comp("MASTER", total), t = 0;
    for (i = 0; i < shots.length; i++) {
      var L = M.layers.add(shots[i]); L.startTime = t; t += shots[i].duration;
    }
    // shot marks for the app's Shots section (specs/029 contracts/files.md): [t0, t1, set, id] per shot, source "ae"
    var rows = [], tt = 0;
    for (i = 0; i < shots.length; i++) { rows.push("[" + tt.toFixed(4) + ", " + (tt + shots[i].duration).toFixed(4) + ", \"\", \"S" + list[i] + "\"]"); tt += shots[i].duration; }
    var sj = new File(CU.WORK + "/shots_" + (CU.PROJ || "build.aep").replace(/\.aep$/, "") + ".json");
    sj.encoding = "UTF-8"; sj.open("w");
    sj.write("{\"version\": 1, \"video\": \"\", \"duration\": " + tt.toFixed(4) + ", \"fps\": " + CU.FPS + ", \"source\": \"ae\", \"shots\": [" + rows.join(", ") + "]}");
    sj.close();
    // person precomps: collapse transformations so vectors stay sharp when scaled
    for (i = 1; i <= app.project.numItems; i++) {
      var it = app.project.item(i);
      if (it instanceof CompItem) {
        var j;
        for (j = 1; j <= it.numLayers; j++) {
          var ly = it.layer(j);
          if (ly.source && ly.source instanceof CompItem && ly.source.name.indexOf("P ") === 0) { try { ly.collapseTransformation = true; } catch (e2) { } }
        }
      }
    }
    app.project.save(new File(CU.WORK + "/" + (CU.PROJ || "build.aep")));
    CU.say("master " + total.toFixed(3) + " s");
    if (CU.RENDER) { CU.renderMaster(M, CU.RENDER); }
  } catch (e) { CU.say("ERR " + e.toString() + " line " + e.line); }
  try { app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES); } catch (e4) { }   // After Effects stays open for the next build
  try { app.purge(PurgeTarget.ALL_CACHES); } catch (e5) { }                       // and gives its memory back
  app.endSuppressDialogs(false);
  CU.say("DONE"); CU.log.close();
};

// Render MASTER inside After Effects with its render queue (specs/031): no aerender, so After Effects never has to be
// closed between builds (a forced close leaves it on a start-up dialog, and a cold start takes 1.5-4 minutes).
CU.OM_TEMPLATE = "H.264 - Match Render Settings - 40 Mbps";
CU.renderMaster = function (M, name) {
  var rq = app.project.renderQueue, i;
  for (i = rq.numItems; i >= 1; i--) { rq.item(i).remove(); }
  var it = rq.items.add(M);
  try { it.applyTemplate("Best Settings"); } catch (e1) { }
  var om = it.outputModule(1);
  om.applyTemplate(CU.OM_TEMPLATE);
  om.file = new File(CU.WORK + "/" + name);
  CU.say("render " + name);
  var t0 = new Date().getTime();
  rq.render();
  if (!om.file.exists) { CU.say("ERR render: After Effects wrote no " + name); return; }
  CU.say("rendered " + (new Date().getTime() - t0) + " ms");
};
