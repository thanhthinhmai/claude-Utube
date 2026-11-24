// A fake After Effects for tests and the GitHub Actions smoke run (specs/031 T006a): the runners have no AE.
//   node fake-ae.mjs afterfx -r <entry.jsx>                       like AfterFX.exe -r: runs a bundle's entry
//   node fake-ae.mjs aerender -project <p.aep> -comp MASTER -output <out.mp4>
// afterfx reads bundle.json next to the entry and writes log.txt (START, shot … ok, DONE), shots_<proj>.json
// (2 s per shot) and the project file. aerender writes a clip as long as the project's shots (ffmpeg testsrc when
// ffmpeg is on PATH, else the 2 s clip in vectors/).
// afterfx also renders master.mp4 like CU.renderMaster (After Effects' render queue; aerender is not used any more).
// FAKE_AE_MODE: hang (no log, sleeps), noscript (exits without a log), err (ERR line), norender (no master.mp4), slowrender
// FAKE_AE_LOCK=<file>: counts runs that overlap (a second afterfx/aerender while one is running) into <file>.overlap
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const [tool, ...args] = process.argv.slice(2);
const opt = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const mode = process.env.FAKE_AE_MODE || "";
const sleep = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
const lock = process.env.FAKE_AE_LOCK;

function enter() {
  if (!lock) return;
  if (fs.existsSync(lock)) fs.appendFileSync(lock + ".overlap", "x");
  fs.writeFileSync(lock, String(process.pid));
}
function leave() { if (lock) { try { fs.unlinkSync(lock); } catch { /* gone */ } } }

/** A clip of `dur` seconds: ffmpeg testsrc when ffmpeg is on PATH, else the 2 s clip in vectors/. */
function clip(out, dur) {
  const r = spawnSync("ffmpeg", ["-v", "error", "-y", "-f", "lavfi", "-i", `testsrc=size=320x180:rate=30:duration=${dur}`,
    "-c:v", "libx264", "-pix_fmt", "yuv420p", out]);
  if (r.status !== 0) fs.copyFileSync(path.join(HERE, "vectors", "fake-shot.mp4"), out);
}

if (tool === "afterfx") {
  const entry = opt("-r");
  if (!entry) { console.error("usage: afterfx -r <entry.jsx>"); process.exit(2); }
  const dir = path.dirname(entry);
  enter();
  try {
    if (mode === "noscript") process.exit(0);
    if (mode === "hang") { sleep(600000); process.exit(0); }
    const meta = JSON.parse(fs.readFileSync(path.join(dir, "bundle.json"), "utf8"));
    const log = [];
    log.push("START");
    const rows = [];
    let t = 0;
    for (const s of meta.shots) { rows.push([t, t + 2, "", s]); t += 2; log.push(`shot ${s.slice(1)} ok 5 ms`); }
    if (mode === "err") log.push("ERR shot " + meta.shots[0].slice(1) + ": ReferenceError: CU.nothing is undefined line 3");
    if (mode === "check") log.push("CHECK floor " + meta.shots[0] + ": person floats 12 px above the floor");
    const proj = meta.proj || "build.aep";
    fs.writeFileSync(path.join(dir, `shots_${proj.replace(/\.aep$/, "")}.json`),
      JSON.stringify({ version: 1, video: "", duration: t, fps: meta.fps || 30, source: "ae", shots: rows }));
    fs.writeFileSync(path.join(dir, proj), "fake aep");
    sleep(Number(process.env.FAKE_AE_BUILD_MS || 50));
    log.push(`master ${t.toFixed(3)} s`);
    if (rows.length && mode !== "norender") {          // like CU.renderMaster: AE renders MASTER in its render queue
      log.push("render master.mp4");
      fs.writeFileSync(path.join(dir, "log.txt"), log.join("\n") + "\n");   // AE writes its log as it goes
      sleep(400);
      clip(path.join(dir, "master.mp4"), t);
      log.push("rendered 5 ms");
    }
    log.push("DONE");
    fs.writeFileSync(path.join(dir, "log.txt"), log.join("\n") + "\n");
  } finally { leave(); }
} else if (tool === "aerender") {
  const proj = opt("-project"), out = opt("-output");
  if (!proj || !out) { console.error("usage: aerender -project <p> -comp <c> -output <o>"); process.exit(2); }
  enter();
  try {
    if (mode === "slowrender") sleep(600000);
    if (!fs.existsSync(proj)) { console.log("aerender ERROR: No project"); process.exit(1); }
    const marks = path.join(path.dirname(proj), `shots_${path.basename(proj).replace(/\.aep$/, "")}.json`);
    let dur = 2;
    try { dur = JSON.parse(fs.readFileSync(marks, "utf8")).duration || 2; } catch { /* default */ }
    clip(out, dur);
    sleep(Number(process.env.FAKE_AE_RENDER_MS || 50));
    console.log("PROGRESS: Total Time Elapsed: 1 Seconds");
  } finally { leave(); }
} else {
  console.error("usage: fake-ae.mjs afterfx|aerender …");
  process.exit(2);
}
