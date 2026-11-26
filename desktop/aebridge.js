// @ts-check
// The After Effects bridge of the desktop app (specs/032 T016, research R1–R4). The core (in WSL or on this Mac)
// keeps a queue of build requests; this app pulls one at a time, runs After Effects and aerender on this machine,
// and sends progress, the rendered clip and the result back. No Electron here, so `node --test` covers it.
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");

const IDLE_POLL_MS = 5_000;
const BUSY_POLL_MS = 1_000;
const HELLO_MS = 10_000;
const BEAT_MS = 10_000;
const START_TIMEOUT_S = 240;          // a cold After Effects start took ~90 s (2026-11-24)
const SHOT_TIMEOUT_S = 300;
const MIN_FREE = 2 * 1024 ** 3;
const OM_TEMPLATE = "H.264 - Match Render Settings - 40 Mbps";

/** @typedef {{afterfx?: string|string[], aerender?: string|string[], work?: string, shotTimeoutSec?: number,
 *   startTimeoutSec?: number}} AeConfig */
/** @typedef {{afterfx: string|string[], aerender: string|string[], version: string}} Found */

// ---------- finding After Effects (R4) ----------
/** Year of an "Adobe After Effects 2027" folder name, else 0. @param {string} name */
function aeYear(name) {
  const m = /Adobe After Effects (?:CC )?(\d{4})/.exec(name);
  return m ? Number(m[1]) : 0;
}

/** The newest After Effects in the default install places, or null.
 * @param {string} platform @param {{readdir: (d: string) => string[], exists: (p: string) => boolean}} io
 * @param {Record<string, string|undefined>} env @returns {Found|null} */
function findAE(platform, io, env = process.env) {
  /** @param {string} d */
  const list = (d) => { try { return io.readdir(d); } catch { return []; } };
  if (platform === "win32") {
    const roots = [env.ProgramFiles || "C:\\Program Files"].map((r) => path.win32.join(r, "Adobe"));
    const found = [];
    for (const root of roots) {
      for (const name of list(root)) {
        const sup = path.win32.join(root, name, "Support Files");
        const fx = path.win32.join(sup, "AfterFX.exe");
        if (aeYear(name) && io.exists(fx)) found.push({ afterfx: fx, aerender: path.win32.join(sup, "aerender.exe"), version: name, y: aeYear(name) });
      }
    }
    found.sort((a, b) => b.y - a.y);
    return found.length ? { afterfx: found[0].afterfx, aerender: found[0].aerender, version: found[0].version } : null;
  }
  if (platform === "darwin") {
    const found = [];
    for (const name of list("/Applications")) {
      if (!aeYear(name)) continue;
      const dir = path.posix.join("/Applications", name);
      const app = path.posix.join(dir, `${name}.app`);
      if (io.exists(app)) found.push({ afterfx: app, aerender: path.posix.join(dir, "aerender"), version: name, y: aeYear(name) });
    }
    found.sort((a, b) => b.y - a.y);
    return found.length ? { afterfx: found[0].afterfx, aerender: found[0].aerender, version: found[0].version } : null;
  }
  return null;
}

/** Paths in use: the user's choice in config.json → ae, else the default places.
 * @param {AeConfig|undefined} cfg @param {Found|null} found */
function settings(cfg, found) {
  const c = cfg || {};
  return {
    afterfx: c.afterfx || (found ? found.afterfx : ""),
    aerender: c.aerender || (found ? found.aerender : ""),
    version: found ? found.version : "",
    work: c.work || "",
    shotTimeoutSec: Number(c.shotTimeoutSec) || SHOT_TIMEOUT_S,
    startTimeoutSec: Number(c.startTimeoutSec) || START_TIMEOUT_S,
  };
}

/** @param {string|string[]} v */
const argv = (v) => (Array.isArray(v) ? [...v] : [v]);
/** Windows only: a running After Effects silently ignores `-r` on a script whose path has a space (found in T031).
 * @param {string} platform @param {ReturnType<typeof settings>} s @returns {string} the reason, or "" when fine */
function workProblem(platform, s) {
  if (platform !== "win32" || isFake(s.afterfx) || !/\s/.test(String(s.work || ""))) return "";
  return `the work folder "${s.work}" has a space in its path, and After Effects ignores scripts there; ` +
    "choose a folder without spaces in the tray menu → After Effects… (for example E:\\claude-utube-ae)";
}

/** @param {string|string[]} v */
const isFake = (v) => Array.isArray(v);

// ---------- commands (R3) ----------
/** {file, args} that hands entry.jsx to After Effects. @param {string} platform @param {ReturnType<typeof settings>} s @param {string} entry */
function scriptCommand(platform, s, entry) {
  if (platform === "darwin" && !isFake(s.afterfx)) {
    const app = String(s.afterfx).replace(/"/g, '\\"');
    const file = entry.replace(/"/g, '\\"');
    return { file: "/usr/bin/osascript", args: ["-e", `tell application "${app}" to DoScriptFile "${file}"`] };
  }
  const a = argv(s.afterfx);
  return { file: a[0], args: [...a.slice(1), "-r", entry] };
}

/** @param {ReturnType<typeof settings>} s @param {string} aep @param {string} out */
function renderCommand(s, aep, out) {
  const a = argv(s.aerender);
  return { file: a[0], args: [...a.slice(1), "-project", aep, "-comp", "MASTER", "-OMtemplate", OM_TEMPLATE, "-output", out] };
}

/** Commands that close After Effects so aerender can open the project (Windows: a GUI holding it makes aerender
 *  fail with "connection forcibly closed" or hang). @param {string} platform @param {ReturnType<typeof settings>} s */
function killCommands(platform, s) {
  if (platform !== "win32" || isFake(s.afterfx)) return [];
  return ["AfterFX.exe", "AfterFX.com", "aerender.exe"].map((im) => ({ file: "taskkill.exe", args: ["/IM", im, "/F"] }));
}

// ---------- the bundle (a plain tar from tools/ae/bundle.py) ----------
/** Files of a tar archive; refuses absolute paths, "..", and links. @param {Buffer} buf @returns {{name: string, data: Buffer|null}[]} */
function untar(buf) {
  const out = [];
  let off = 0, longName = "";
  while (off + 512 <= buf.length) {
    const h = buf.subarray(off, off + 512);
    if (h.every((b) => b === 0)) break;
    const str = (/** @type {number} */ a, /** @type {number} */ b) => h.subarray(a, b).toString("utf8").replace(/\0.*$/s, "");
    let name = str(0, 100);
    const prefix = str(345, 500);
    if (prefix) name = prefix + "/" + name;
    const size = parseInt(str(124, 136).trim() || "0", 8);
    const type = String.fromCharCode(h[156] || 48);
    const body = buf.subarray(off + 512, off + 512 + size);
    off += 512 + Math.ceil(size / 512) * 512;
    if (type === "x" || type === "g") {                  // pax header: take its path for the next entry
      const m = /\d+ path=([^\n]*)\n/.exec(body.toString("utf8"));
      if (type === "x" && m) longName = m[1];
      continue;
    }
    if (type === "L") { longName = body.toString("utf8").replace(/\0.*$/s, ""); continue; }
    if (longName) { name = longName; longName = ""; }
    if (path.posix.isAbsolute(name) || name.split("/").includes("..") || /^[A-Za-z]:/.test(name)) throw new Error(`unsafe entry in bundle: ${name}`);
    if (type === "5") { out.push({ name: name.replace(/\/$/, ""), data: null }); continue; }
    if (type !== "0" && type !== "\0") throw new Error(`unsafe entry in bundle: ${name}`);
    out.push({ name, data: Buffer.from(body) });
  }
  return out;
}

/** @param {Buffer} buf @param {string} dest */
function extract(buf, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const e of untar(buf)) {
    const p = path.join(dest, ...e.name.split("/"));
    if (!path.resolve(p).startsWith(path.resolve(dest))) throw new Error(`unsafe entry in bundle: ${e.name}`);
    if (e.data === null) fs.mkdirSync(p, { recursive: true });
    else { fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, e.data); }
  }
}

// ---------- log.txt of a build ----------
/** @param {string} text */
function parseLog(text) {
  const lines = (text || "").split(/\r?\n/).filter((x) => x.trim());
  return {
    started: lines.includes("START") || lines.length > 0,
    done: lines.includes("DONE"),
    shotsOk: lines.filter((x) => /^shot \S+ ok/.test(x)).map((x) => "S" + x.split(" ")[1]),
    errors: lines.filter((x) => x.startsWith("ERR")),
    checks: lines.filter((x) => x.startsWith("CHECK ")),
    tail: lines.slice(-20).join("\n"),
  };
}

class BridgeError extends Error {
  /** @param {string} code @param {string} message @param {string} [tail] */
  constructor(code, message, tail = "") { super(message); this.code = code; this.tail = tail; }
}

// ---------- the bridge ----------
/**
 * @typedef {{
 *   base: () => string|null, key: string, platform: string, config: () => AeConfig|undefined,
 *   found: () => Found|null, version?: string, fetch?: typeof fetch, freeBytes?: (dir: string) => number,
 *   aePath?: (p: string) => string,
 *   log?: (s: string) => void, sleep?: (ms: number) => Promise<void>, tick?: number
 * }} BridgeOptions
 */
class Bridge {
  /** @param {BridgeOptions} o */
  constructor(o) {
    this.o = o;
    this.fetch = o.fetch || fetch;
    this.running = false;           // the one-run lock (FR-007)
    this.stopped = true;
    this.closing = false;           // stop() was called: a build in progress gives up
    this.busy = null;               // id of the request being built
    this.lastHello = 0;
    /** @type {Set<import("node:child_process").ChildProcess>} */
    this.children = new Set();
    this.freeBytes = o.freeBytes || ((/** @type {string} */ d) => { const s = fs.statfsSync(d); return Number(s.bavail) * Number(s.bsize); });
    this.log = o.log || (() => {});
  }

  settings() { return settings(this.o.config(), this.o.found()); }

  /** A path as After Effects sees it (the same, except a development run from WSL: C:\\…). @param {string} p */
  aePath(p) { return this.o.aePath ? this.o.aePath(p) : p; }

  /** True when the configured After Effects and aerender exist. */
  hasAE() {
    const s = this.settings();
    if (isFake(s.afterfx)) return true;
    return !!s.afterfx && fs.existsSync(String(s.afterfx));     // aerender is not needed: AE renders in its render queue
  }

  /** @param {string} p @param {RequestInit} [init] */
  async call(p, init = {}) {
    const base = this.o.base();
    if (!base) throw new BridgeError("no_core", "the studio is not running");
    const headers = { "x-cu-bridge": this.o.key, ...(init.headers || {}) };
    return this.fetch(base.replace(/\/$/, "") + "/api/v1/ae/bridge/" + p, { ...init, headers });
  }

  /** @param {string} p @param {any} body */
  async post(p, body) {
    return this.call(p, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  }

  async hello() {
    const s = this.settings();
    this.lastHello = Date.now();
    const found = this.hasAE();
    await this.post("hello", { version: this.o.version || "", os: this.o.platform, found,
      afterfx: isFake(s.afterfx) ? "fake" : String(s.afterfx || ""), aerender: isFake(s.aerender) ? "fake" : String(s.aerender || "") }).catch(() => {});
    return found;
  }

  /** One poll: claim a request and build it. Returns true when it built something. */
  async once() {
    if (this.running) return false;
    if (Date.now() - this.lastHello >= HELLO_MS) await this.hello();
    let r;
    try { r = await this.call("next"); } catch { return false; }
    if (r.status !== 200) return false;
    const req = await r.json();
    this.running = true;
    this.busy = req.id;
    try { await this.build(req); } finally { this.running = false; this.busy = null; }
    return true;
  }

  start() {
    if (!this.stopped) return;
    this.stopped = false;
    this.closing = false;
    const sleep = this.o.sleep || ((/** @type {number} */ ms) => new Promise((res) => setTimeout(res, ms)));
    (async () => {
      while (!this.stopped) {
        const built = await this.once().catch((e) => { this.log(`ae bridge: ${e}`); return false; });
        await sleep(built ? 0 : (this.o.tick || IDLE_POLL_MS));     // after a build, ask for the next one at once
      }
    })();
  }

  stop() {
    this.stopped = true;
    this.closing = true;
    for (const c of this.children) { try { c.kill(); } catch { /* gone */ } }
  }

  /** @param {{file: string, args: string[]}} cmd @param {{cwd?: string, timeoutMs?: number}} [opt] */
  run(cmd, opt = {}) {
    return new Promise((resolve) => {
      let out = "";
      const c = spawn(cmd.file, cmd.args, { cwd: opt.cwd, windowsHide: true });
      this.children.add(c);
      const t = opt.timeoutMs ? setTimeout(() => { c.kill(); resolve({ code: null, out, timedOut: true }); }, opt.timeoutMs) : null;
      c.stdout && c.stdout.on("data", (d) => { out += d; });
      c.stderr && c.stderr.on("data", (d) => { out += d; });
      c.on("error", (e) => { if (t) clearTimeout(t); this.children.delete(c); resolve({ code: -1, out: out + String(e), timedOut: false }); });
      c.on("close", (code) => { if (t) clearTimeout(t); this.children.delete(c); resolve({ code, out, timedOut: false }); });
    });
  }

  async killAE() {
    for (const k of killCommands(this.o.platform, this.settings())) await this.run(k, { timeoutMs: 15_000 });
  }

  /** Build one claimed request end to end; always finishes it (ok or error). @param {any} req */
  async build(req) {
    const s = this.settings();
    let beat = null;
    const progress = (/** @type {any} */ p) => this.post(`${req.id}/progress`, p).catch(() => {});
    try {
      beat = setInterval(() => progress({}), BEAT_MS);
      if (!this.hasAE()) throw new BridgeError("ae_missing", "After Effects was not found on this computer; open the tray menu → After Effects… to choose it");
      if (!s.work) throw new BridgeError("bad_work", "no work folder for After Effects; choose one in the tray menu → After Effects…");
      if (workProblem(this.o.platform, s)) throw new BridgeError("bad_work", workProblem(this.o.platform, s));
      fs.mkdirSync(s.work, { recursive: true });
      if (this.freeBytes(s.work) < MIN_FREE) throw new BridgeError("disk_low", `the work folder ${s.work} has less than 2 GB free`);
      const dir = path.join(s.work, req.id);
      const b = await this.call(`${req.id}/bundle`);
      if (b.status !== 200) throw new BridgeError("bundle", `the studio did not send the bundle (${b.status})`);
      extract(Buffer.from(await b.arrayBuffer()), dir);
      const meta = JSON.parse(fs.readFileSync(path.join(dir, "bundle.json"), "utf8"));
      const shots = meta.shots || req.shots;
      const proj = meta.proj || "build.aep";
      await progress({ state: "running", shot: shots[0], index: 0, total: shots.length });
      // After Effects builds and renders MASTER itself (render queue) and stays open: no kill, no aerender (a forced
      // close leaves it on a start-up dialog; a cold start takes minutes)
      const script = this.run(scriptCommand(this.o.platform, s, this.aePath(path.join(dir, "entry.jsx"))), { cwd: dir });
      const text = await this.waitLog(path.join(dir, "log.txt"), shots, s, progress);
      await Promise.race([script, new Promise((res) => setTimeout(res, 10_000))]);
      const lg = parseLog(text);
      if (lg.errors.length) throw new BridgeError(lg.errors[0].startsWith("ERR render") ? "render_error" : "build_error", lg.errors[0], lg.tail);
      const out = path.join(dir, "master.mp4");
      const marksFile = path.join(dir, `shots_${proj.replace(/\.aep$/, "")}.json`);
      if (!fs.existsSync(marksFile)) throw new BridgeError("build_error", "After Effects wrote no shot marks", lg.tail);
      if (!fs.existsSync(out) || fs.statSync(out).size === 0) throw new BridgeError("render_error", "After Effects rendered no video", lg.tail);
      const up = await this.call(`${req.id}/result/MASTER`, { method: "PUT", headers: { "content-type": "video/mp4" }, body: fs.readFileSync(out) });
      if (up.status !== 201) throw new BridgeError("upload", `the studio did not take the clip (${up.status})`);
      const marks = JSON.parse(fs.readFileSync(marksFile, "utf8"));
      const keysFile = path.join(dir, `keys_${proj.replace(/\.aep$/, "")}.json`);       // specs/035 R5
      let keys = null;
      try { keys = fs.existsSync(keysFile) ? JSON.parse(fs.readFileSync(keysFile, "utf8")) : null; } catch { keys = null; }
      await this.post(`${req.id}/finish`, { ok: true, checks: lg.checks, marks: marks.shots, duration: marks.duration, keys });
      fs.rmSync(dir, { recursive: true, force: true });
    } catch (e) {
      const err = e instanceof BridgeError ? e : new BridgeError("build_error", String(e && /** @type {any} */ (e).message || e));
      this.log(`ae bridge ${req.id}: ${err.code} ${err.message}`);
      await this.post(`${req.id}/finish`, { ok: false, error: { code: err.code, message: err.message, log_tail: err.tail } }).catch(() => {});
    } finally {
      if (beat) clearInterval(beat);
    }
  }

  /** "Test" in the After Effects window: run a script that only writes log.txt, to prove AE runs scripts here. */
  async selfTest() {
    if (!this.hasAE()) return { ok: false, code: "ae_missing", message: "After Effects was not found. Choose AfterFX (Windows) or the After Effects app (macOS)." };
    const s = this.settings();
    if (this.running) return { ok: false, code: "busy", message: "After Effects is busy with a film." };
    if (workProblem(this.o.platform, s)) return { ok: false, code: "bad_work", message: workProblem(this.o.platform, s) };
    this.running = true;
    const dir = path.join(s.work, `test-${Date.now()}`);
    try {
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(path.join(dir, "bundle.json"), JSON.stringify({ shots: [], proj: "test.aep" }));
      fs.writeFileSync(path.join(dir, "entry.jsx"), '// claude-Utube: After Effects test (specs/032)\n' +
        'var f = new File((new File($.fileName)).parent.fsName + "/log.txt"); f.open("w"); f.writeln("START"); f.writeln("DONE"); f.close();\n');
      const t0 = Date.now();
      const p = this.run(scriptCommand(this.o.platform, s, this.aePath(path.join(dir, "entry.jsx"))), { cwd: dir });
      await this.waitLog(path.join(dir, "log.txt"), [], s, () => {});
      await Promise.race([p, new Promise((res) => setTimeout(res, 10_000))]);
      return { ok: true, message: `After Effects ran the test script in ${((Date.now() - t0) / 1000).toFixed(1)} s.` };
    } catch (e) {
      const err = /** @type {any} */ (e);
      return { ok: false, code: err.code || "error", message: err.message || String(e) };
    } finally {
      this.running = false;
      fs.rmSync(dir, { recursive: true, force: true });
    }
  }

  /** Wait for START within the start timeout, then a new log line at least every shot timeout, until DONE.
   * @param {string} file @param {string[]} shots @param {ReturnType<typeof settings>} s @param {(p: any) => any} progress */
  async waitLog(file, shots, s, progress) {
    const t0 = Date.now();
    let last = t0, seen = 0, text = "";
    for (;;) {
      if (this.closing) throw new BridgeError("stopped", "the desktop app is closing");
      try { text = fs.readFileSync(file, "utf8"); } catch { text = ""; }
      const lg = parseLog(text);
      if (lg.done) return text;
      const n = text.split(/\r?\n/).filter((x) => x.trim()).length;
      if (n > seen) {
        seen = n; last = Date.now();
        const lastLine = text.split(/\r?\n/).filter((x) => x.trim()).pop() || "";
        if (lastLine.startsWith("render ")) progress({ state: "running", shot: "MASTER", index: shots.length, total: shots.length });
        else if (lg.shotsOk.length) progress({ state: "running", shot: lg.shotsOk[lg.shotsOk.length - 1], index: lg.shotsOk.length, total: shots.length });
      }
      const rendering = (text.split(/\r?\n/).filter((x) => x.trim()).pop() || "").startsWith("render ");
      const allow = s.shotTimeoutSec * (rendering ? Math.max(1, shots.length) : 1);
      const now = Date.now();
      if (!n && now - t0 > s.startTimeoutSec * 1000) {
        // never force After Effects closed here: it is usually waiting on a dialog, and a forced close brings back
        // the crash / Safe Mode dialog at the next start (T031). On Windows the child may be After Effects itself.
        if (this.o.platform !== "win32" || isFake(s.afterfx)) for (const c of this.children) { try { c.kill(); } catch { /* gone */ } }
        throw new BridgeError("ae_scripting_off", `After Effects did not start the script in ${s.startTimeoutSec} s. Open After Effects once ` +
          `(a dialog may be waiting: answer it, and do not choose Safe Mode) and turn on Preferences > Scripting & Expressions > "Allow Scripts to Write Files and Access Network".`);
      }
      if (n && now - last > allow * 1000) {
        await this.killAE();
        for (const c of this.children) { try { c.kill(); } catch { /* gone */ } }
        throw new BridgeError("ae_stalled", `After Effects made no progress for ${allow} s`, parseLog(text).tail);
      }
      await new Promise((res) => setTimeout(res, 250));
    }
  }
}

module.exports = { Bridge, BridgeError, findAE, settings, workProblem, scriptCommand, renderCommand, killCommands, untar, extract, parseLog, aeYear,
  IDLE_POLL_MS, BUSY_POLL_MS, MIN_FREE };
