// A fake Blender for tests and the GitHub Actions smoke run (specs/038 T003): the runners have no Blender or GPU.
//   node fake-blender.mjs -b --factory-startup -P <kit/entry.py> -- <request.json>
// Reads request.json (contracts/bridge-api.md) and writes log.txt next to it like tools/blender/kit/entry.py:
//   START, VERSION, GPU <renderer> <backend>, frame S<n> i/N, shot S<n> ok, DONE (or ERR <code> <msg>).
// kind render: PNG frames <run>/<shot>/f0001.png… (ffmpeg testsrc); frames already there are kept (resume).
// kind plan: <run>/<shot>/plan.json (no characters, card angle 0). kind plate: <run>/<shot>/plate.png. kind probe: log only.
// FAKE_BLENDER_MODE: gpu_software (ERR gpu_software, exit 3, no frames), hang (sleeps), err (ERR script), slow (100 ms a frame)
// FAKE_BLENDER_STOP=<n>: stop after n new frames without DONE (exit 1), like a machine that went off mid-shot
// FAKE_BLENDER_LOCK=<file>: counts overlapping runs into <file>.overlap
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";

const argv = process.argv.slice(2);
const dash = argv.indexOf("--");
const reqPath = dash >= 0 ? argv[dash + 1] : null;
if (!argv.includes("-b") || !argv.includes("-P") || !reqPath) {
  console.error("usage: fake-blender -b --factory-startup -P <entry.py> -- <request.json>");
  process.exit(2);
}
const mode = process.env.FAKE_BLENDER_MODE || "";
const stopAfter = Number(process.env.FAKE_BLENDER_STOP || 0);
const lock = process.env.FAKE_BLENDER_LOCK;
const sleep = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
const dir = path.dirname(reqPath);
const logFile = path.join(dir, "log.txt");
const log = (line) => fs.appendFileSync(logFile, line + "\n");

if (lock) {
  if (fs.existsSync(lock)) fs.appendFileSync(lock + ".overlap", "x");
  fs.writeFileSync(lock, String(process.pid));
}
const leave = (code) => { if (lock) { try { fs.unlinkSync(lock); } catch { /* gone */ } } process.exit(code); };

if (mode === "hang") { sleep(600000); leave(0); }
const req = JSON.parse(fs.readFileSync(reqPath, "utf8"));
const [W, H] = req.size || [320, 180];
const scale = req.quarter ? 4 : 1;
const w = Math.max(16, Math.round(W / scale / 2) * 2), h = Math.max(16, Math.round(H / scale / 2) * 2);
log("START");
log("VERSION 5.2.5 (fake)");
if (mode === "gpu_software") { log("GPU llvmpipe (LLVM 15.0.7, 256 bits) OPENGL"); log("ERR gpu_software llvmpipe"); leave(3); }
log("GPU Fake GPU OPENGL");
if (mode === "err") { log(`ERR script ${req.shots?.[0]?.id || "S1"}: NameError: name 'k2' is not defined line 3`); leave(1); }

let made = 0;
for (const s of req.shots || []) {
  const out = path.join(dir, s.id);
  fs.mkdirSync(out, { recursive: true });
  if (req.kind === "plan") {
    fs.writeFileSync(path.join(out, "plan.json"), JSON.stringify({ shot: s.id, frames: s.frames, chars: [], card_angle_max: 0 }));
  } else if (req.kind === "plate") {
    spawnSync("ffmpeg", ["-v", "error", "-y", "-f", "lavfi", "-i", `testsrc=size=${w}x${h}`, "-frames:v", "1", path.join(out, "plate.png")]);
  } else if (req.kind === "render") {
    const have = fs.readdirSync(out).filter((f) => /^f\d{4}\.png$/.test(f)).length;
    let todo = s.frames - have;
    if (stopAfter && todo > stopAfter - made) todo = Math.max(0, stopAfter - made);
    if (todo > 0) {
      const r = spawnSync("ffmpeg", ["-v", "error", "-y", "-f", "lavfi", "-i", `testsrc=size=${w}x${h}:rate=${req.fps || 24}`,
        "-frames:v", String(todo), "-start_number", String(have + 1), path.join(out, "f%04d.png")]);
      if (r.status !== 0) { log(`ERR script ffmpeg failed for ${s.id}`); leave(1); }
      if (mode === "slow") sleep(100 * todo);
      made += todo;
      log(`frame ${s.id} ${have + todo}/${s.frames}`);
    }
    if (have + todo < s.frames) leave(1);   // stopped mid-shot: no "shot ok", no DONE
  }
  log(`shot ${s.id} ok`);
}
log("DONE");
leave(0);
