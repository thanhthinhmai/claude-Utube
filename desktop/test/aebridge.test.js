// @ts-check
// The desktop app's After Effects bridge (specs/032 T019) with the fake AE (fake-ae.mjs) and a fake core queue.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const http = require("node:http");
const ae = require("../aebridge.js");

const FAKE = path.join(__dirname, "fake-ae.mjs");
const KEY = "k".repeat(43);

/** A tar with these files (ustar, short names). @param {Record<string, string>} files */
function tar(files) {
  const parts = [];
  for (const [name, text] of Object.entries(files)) {
    const data = Buffer.from(text);
    const h = Buffer.alloc(512);
    h.write(name, 0);
    h.write("0000644\0", 100); h.write("0000000\0", 108); h.write("0000000\0", 116);
    h.write(data.length.toString(8).padStart(11, "0") + "\0", 124);
    h.write("00000000000\0", 136);
    h.write("0", 156); h.write("ustar\0", 257); h.write("00", 263);
    h.fill(" ", 148, 156);
    let sum = 0; for (const b of h) sum += b;
    h.write(sum.toString(8).padStart(6, "0") + "\0 ", 148);
    parts.push(h, data, Buffer.alloc((512 - (data.length % 512)) % 512));
  }
  parts.push(Buffer.alloc(1024));
  return Buffer.concat(parts);
}

/** A fake core queue behind /api/v1/ae/bridge/*. */
function fakeCore() {
  /** @type {any[]} */
  const reqs = [];
  const st = { hellos: /** @type {any[]} */ ([]), forbidden: 0 };
  const server = http.createServer(async (q, r) => {
    const chunks = [];
    for await (const c of q) chunks.push(c);
    const body = Buffer.concat(chunks);
    if (q.headers["x-cu-bridge"] !== KEY) { st.forbidden++; r.writeHead(403); r.end(); return; }
    const p = (q.url || "").replace("/api/v1/ae/bridge/", "");
    const json = (/** @type {number} */ code, /** @type {any} */ o) => { r.writeHead(code, { "content-type": "application/json" }); r.end(JSON.stringify(o)); };
    if (p === "hello") { st.hellos.push(JSON.parse(body.toString())); return json(200, { ok: true }); }
    if (p === "next") {
      if (reqs.some((x) => x.state === "claimed" || x.state === "running")) { r.writeHead(204); r.end(); return; }
      const x = reqs.find((y) => y.state === "queued");
      if (!x) { r.writeHead(204); r.end(); return; }
      x.state = "claimed"; x.claimedAt = Date.now();
      return json(200, { id: x.id, shots: x.shots, film: "f1" });
    }
    const [id, what, name] = p.split("/");
    const x = reqs.find((y) => y.id === id);
    if (!x) return json(404, {});
    if (what === "bundle") { r.writeHead(200); r.end(x.bundle); return; }
    if (what === "progress") { const b = JSON.parse(body.toString() || "{}"); if (b.state) { x.state = "running"; x.progress.push(b); } return json(200, {}); }
    if (what === "result") { x.results[name] = body.length; return json(201, {}); }
    if (what === "finish") { const b = JSON.parse(body.toString()); x.state = b.ok ? "done" : "failed"; x.finish = b; x.finishedAt = Date.now(); return json(200, {}); }
    json(404, {});
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => {
    const a = /** @type {any} */ (server.address());
    resolve({
      url: `http://127.0.0.1:${a.port}`, reqs, st, close: () => new Promise((res) => server.close(res)),
      /** @param {string[]} shots */
      add(shots) {
        const id = `ae-20261124-000000-${String(reqs.length).padStart(4, "0")}`;
        reqs.push({ id, shots, state: "queued", progress: [], results: {}, bundle: tar({
          "bundle.json": JSON.stringify({ film: "f1", shots, proj: "build.aep", fps: 30 }), "entry.jsx": "// entry" }) });
        return id;
      },
    });
  }));
}

/** @param {any} core @param {any} [cfg] @param {any} [extra] */
function bridge(core, cfg, extra = {}) {
  const work = fs.mkdtempSync(path.join(os.tmpdir(), "ae bridge "));
  const c = { afterfx: [process.execPath, FAKE, "afterfx"], aerender: [process.execPath, FAKE, "aerender"],
    work: path.join(work, "thư mục thử"), ...cfg };
  return new ae.Bridge({ base: () => core.url, key: KEY, platform: process.platform, config: () => c, found: () => null,
    version: "test", tick: 50, ...extra });
}

/** @param {() => boolean} cond @param {number} ms */
async function until(cond, ms) {
  const end = Date.now() + ms;
  while (Date.now() < end) { if (cond()) return true; await new Promise((r) => setTimeout(r, 20)); }
  return cond();
}

test("finds the newest After Effects in the default places", () => {
  const win = { readdir: () => ["Adobe After Effects 2025", "Adobe After Effects 2027", "Adobe Photoshop 2026"], exists: () => true };
  const w = ae.findAE("win32", win, { ProgramFiles: "C:\\Program Files" });
  assert.equal(w && w.afterfx, "C:\\Program Files\\Adobe\\Adobe After Effects 2027\\Support Files\\AfterFX.exe");
  assert.equal(w && w.aerender, "C:\\Program Files\\Adobe\\Adobe After Effects 2027\\Support Files\\aerender.exe");
  const m = ae.findAE("darwin", { readdir: () => ["Adobe After Effects 2026", "Safari.app"], exists: () => true }, {});
  assert.equal(m && m.afterfx, "/Applications/Adobe After Effects 2026/Adobe After Effects 2026.app");
  assert.equal(ae.findAE("win32", { readdir: () => { throw new Error("no"); }, exists: () => false }, {}), null);
});

test("commands per system", () => {
  const s = ae.settings({ afterfx: "/Applications/AE 2026/AE.app", aerender: "/Applications/AE 2026/aerender" }, null);
  const mac = ae.scriptCommand("darwin", s, "/w/x/entry.jsx");
  assert.equal(mac.file, "/usr/bin/osascript");
  assert.match(mac.args[1], /DoScriptFile "\/w\/x\/entry.jsx"/);
  const w = ae.scriptCommand("win32", ae.settings({ afterfx: "C:\\AE\\AfterFX.exe" }, null), "E:\\w\\entry.jsx");
  assert.deepEqual([w.file, ...w.args], ["C:\\AE\\AfterFX.exe", "-r", "E:\\w\\entry.jsx"]);
  assert.deepEqual(ae.renderCommand(s, "a.aep", "o.mp4").args.slice(0, 4), ["-project", "a.aep", "-comp", "MASTER"]);
});

test("untar refuses unsafe names", () => {
  assert.throws(() => ae.untar(tar({ "../evil.jsx": "x" })), /unsafe/);
  assert.throws(() => ae.untar(tar({ "/abs.jsx": "x" })), /unsafe/);
  assert.deepEqual(ae.untar(tar({ "kit/lib.jsx": "a" })).map((e) => e.name), ["kit/lib.jsx"]);
});

test("one AE run at a time; the next request starts within 2 s (SC-003)", async () => {
  const core = await fakeCore();
  const lock = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "ae lock ")), "running");
  process.env.FAKE_AE_LOCK = lock;
  const b = bridge(core);
  try {
    for (let i = 0; i < 10; i++) { core.add(["S1", "S2"]); core.add(["S3"]); }     // 10 rounds of two at once
    b.start();
    assert.ok(await until(() => core.reqs.every((/** @type {any} */ x) => x.state === "done" || x.state === "failed"), 90_000), "all built");
    for (const x of core.reqs) assert.equal(x.state, "done", JSON.stringify(x.finish));
    assert.equal(fs.existsSync(lock + ".overlap"), false, "two AE runs overlapped");
    for (let i = 1; i < core.reqs.length; i++) {
      assert.ok(core.reqs[i].claimedAt >= core.reqs[i - 1].finishedAt, "claimed before the previous one finished");
      assert.ok(core.reqs[i].claimedAt - core.reqs[i - 1].finishedAt <= 2000, `request ${i} waited too long: ${core.reqs.slice(1).map((/** @type {any} */ x, /** @type {number} */ k) => x.claimedAt - core.reqs[k].finishedAt).join(",")}`);
    }
    const x = core.reqs[0];
    assert.ok(x.results.MASTER > 0);
    assert.deepEqual(x.finish.marks.map((/** @type {any} */ m) => m[3]), ["S1", "S2"]);
    assert.ok(x.progress.some((/** @type {any} */ p) => p.shot === "MASTER"));
    assert.equal(core.st.hellos[0].found, true);
  } finally {
    b.stop(); delete process.env.FAKE_AE_LOCK; await core.close();
  }
});

test("no After Effects: hello says so and a request fails with ae_missing within 10 s (SC-004)", async () => {
  const core = await fakeCore();
  const b = bridge(core, { afterfx: "/nope/AfterFX.exe", aerender: "/nope/aerender.exe" });
  try {
    core.add(["S1"]);
    const t = Date.now();
    await b.once();
    assert.ok(Date.now() - t < 10_000);
    assert.equal(core.st.hellos[0].found, false);
    assert.equal(core.reqs[0].finish.error.code, "ae_missing");
  } finally { b.stop(); await core.close(); }
});

test("a hung After Effects is stopped at the time limit", async () => {
  const core = await fakeCore();
  process.env.FAKE_AE_MODE = "hang";
  const b = bridge(core, { startTimeoutSec: 1 });
  try {
    core.add(["S1"]);
    const t = Date.now();
    await b.once();
    assert.ok(Date.now() - t < 10_000);
    assert.equal(core.reqs[0].finish.error.code, "ae_scripting_off");
    assert.match(core.reqs[0].finish.error.message, /Allow Scripts to Write Files and Access Network/);
    assert.ok(await until(() => b.children.size === 0, 3000), "the hung AE process was killed");
  } finally { delete process.env.FAKE_AE_MODE; b.stop(); await core.close(); }
});

test("build errors and a full disk are reported", async () => {
  const core = await fakeCore();
  process.env.FAKE_AE_MODE = "err";
  const b = bridge(core);
  try {
    core.add(["S1"]);
    await b.once();
    assert.equal(core.reqs[0].finish.error.code, "build_error");
    assert.match(core.reqs[0].finish.error.log_tail, /START/);
  } finally { delete process.env.FAKE_AE_MODE; }
  const b2 = bridge(core, {}, { freeBytes: () => 1024 });
  core.add(["S1"]);
  await b2.once();
  assert.equal(core.reqs[1].finish.error.code, "disk_low");
  b.stop(); b2.stop(); await core.close();
});

test("the key goes with every call", async () => {
  const core = await fakeCore();
  const b = new ae.Bridge({ base: () => core.url, key: "wrong", platform: process.platform, config: () => ({}), found: () => null });
  await b.once();
  assert.ok(core.st.forbidden >= 1);
  assert.equal(core.st.hellos.length, 0);
  await core.close();
});

test("the Test button runs a script in After Effects", async () => {
  const core = await fakeCore();
  const b = bridge(core);
  const r = await b.selfTest();
  assert.equal(r.ok, true, r.message);
  const b2 = bridge(core, { afterfx: "/nope/AfterFX.exe" });
  assert.equal((await b2.selfTest()).code, "ae_missing");
  await core.close();
});

test("a work folder with a space is refused on Windows before After Effects is called (T031)", async () => {
  const s = (work, afterfx = "C:\\AE\\AfterFX.exe") => ae.settings({ work, afterfx, aerender: "C:\\AE\\aerender.exe" }, null);
  assert.match(ae.workProblem("win32", s("C:\\Users\\a\\Documents\\claude-Utube AE")), /space/);
  assert.equal(ae.workProblem("win32", s("E:\\claude-utube-ae")), "");
  assert.equal(ae.workProblem("darwin", s("/Users/a/claude Utube AE")), "");
  assert.equal(ae.workProblem("win32", s("C:\\a b", ["node", "fake"])), "");
});
