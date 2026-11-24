// A fake studio core for the desktop shell's smoke run (specs/015 T006, T014): the same `app` commands as
// `sh bin/studio app …` (specs/014), with a tiny web server instead of the studio. GitHub Actions has no WSL2.
//   node fake-core.mjs app start|status|stop|check [--json] [--force] --data <dir>
// FAKE_CORE_JOB=1: `app status` reports one running job, so quitting has to ask.
// FAKE_CORE_AE=1 (specs/032): `app start --bridge <file>` makes the server queue one After Effects build request behind
// /api/v1/ae/bridge/* (key from the file); GET /__fake/ae shows how it went.
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { spawn } from "node:child_process";

const argv = process.argv.slice(2);
const dataIx = argv.indexOf("--data");
const data = dataIx > 0 ? argv[dataIx + 1] : path.join(process.cwd(), ".fake-core");
const cmd = argv[1];
const stateFile = path.join(data, "fake-core.json");
const read = () => { try { return JSON.parse(fs.readFileSync(stateFile, "utf8")); } catch { return null; } };
const alive = (pid) => { try { process.kill(pid, 0); return true; } catch { return false; } };

/** A tar of small text files (ustar). @param {Record<string, string>} files */
function tar(files) {
  const parts = [];
  for (const [name, text] of Object.entries(files)) {
    const data = Buffer.from(text), h = Buffer.alloc(512);
    h.write(name, 0); h.write("0000644\0", 100); h.write("0000000\0", 108); h.write("0000000\0", 116);
    h.write(data.length.toString(8).padStart(11, "0") + "\0", 124); h.write("00000000000\0", 136);
    h.write("0", 156); h.write("ustar\0", 257); h.write("00", 263); h.fill(" ", 148, 156);
    let sum = 0; for (const b of h) sum += b;
    h.write(sum.toString(8).padStart(6, "0") + "\0 ", 148);
    parts.push(h, data, Buffer.alloc((512 - (data.length % 512)) % 512));
  }
  parts.push(Buffer.alloc(1024));
  return Buffer.concat(parts);
}

if (cmd === "serve") {                              // the background web server
  const bridgeIx = argv.indexOf("--bridge");
  const bridgeFile = bridgeIx > 0 ? argv[bridgeIx + 1] : null;
  const ae = { state: process.env.FAKE_CORE_AE === "1" && bridgeFile ? "queued" : "none", hello: null, progress: [], result: 0, finish: null };
  const bundle = tar({ "bundle.json": JSON.stringify({ film: "smoke", shots: ["S1", "S2"], proj: "build.aep", fps: 30 }), "entry.jsx": "// smoke" });
  const server = http.createServer(async (req, res) => {
    if (req.url.startsWith("/__fake/ae")) { res.writeHead(200, { "content-type": "application/json" }); res.end(JSON.stringify(ae)); return; }
    if (req.url.startsWith("/api/v1/ae/bridge/")) {
      const chunks = []; for await (const c of req) chunks.push(c);
      const body = Buffer.concat(chunks);
      let key = ""; try { key = JSON.parse(fs.readFileSync(bridgeFile, "utf8")).key; } catch { /* none */ }
      if (!key || req.headers["x-cu-bridge"] !== key) { res.writeHead(403); res.end(); return; }
      const p = req.url.slice("/api/v1/ae/bridge/".length);
      const ok = (code, o) => { res.writeHead(code, { "content-type": "application/json" }); res.end(JSON.stringify(o || {})); };
      if (p === "hello") { ae.hello = JSON.parse(body.toString() || "{}"); return ok(200); }
      if (p === "next") { if (ae.state !== "queued") { res.writeHead(204); res.end(); return; } ae.state = "claimed"; return ok(200, { id: "ae-20261124-000000-0001", shots: ["S1", "S2"] }); }
      const [, what] = p.split("/");
      if (what === "bundle") { res.writeHead(200); res.end(bundle); return; }
      if (what === "progress") { const b = JSON.parse(body.toString() || "{}"); if (b.state) { ae.state = "running"; ae.progress.push(b.shot); } return ok(200); }
      if (what === "result") { ae.result = body.length; return ok(201); }
      if (what === "finish") { ae.finish = JSON.parse(body.toString()); ae.state = ae.finish.ok ? "done" : "failed"; return ok(200); }
      return ok(404);
    }
    if (req.url.startsWith("/api/v1/health")) { res.writeHead(200, { "content-type": "application/json" }); res.end('{"ok":true}'); return; }
    res.writeHead(200, { "content-type": "text/html" });
    res.end('<!doctype html><title>fake core</title><h1>fake core</h1><a id="out" href="https://example.com/">outside</a>');
  });
  server.listen(0, "127.0.0.1", () => {
    fs.writeFileSync(stateFile, JSON.stringify({ pid: process.pid, port: server.address().port }));
  });
} else if (cmd === "start") {
  fs.mkdirSync(data, { recursive: true });
  const s = read();
  if (s && alive(s.pid)) {
    console.log(`✓ already running\nURL: http://127.0.0.1:${s.port}`);
  } else {
    fs.rmSync(stateFile, { force: true });
    const bIx = argv.indexOf("--bridge");
    const child = spawn(process.execPath, [new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"), "app", "serve", "--data", data,
      ...(bIx > 0 ? ["--bridge", argv[bIx + 1]] : [])],
      { detached: true, stdio: "ignore", windowsHide: true });
    child.unref();
    const end = Date.now() + 10000;
    while (Date.now() < end && !read()) await new Promise((r) => setTimeout(r, 100));
    const st = read();
    if (!st) { console.log("✗ the fake core did not start"); process.exit(1); }
    console.log(`✓ running\nURL: http://127.0.0.1:${st.port}`);
  }
} else if (cmd === "status") {
  const s = read();
  const up = !!(s && alive(s.pid));
  const job = process.env.FAKE_CORE_JOB === "1";
  console.log(JSON.stringify(up ? { running: true, url: `http://127.0.0.1:${s.port}`, data, logs: path.join(data, "logs"),
    jobs_running: job ? 1 : 0, jobs_queued: 0, jobs: job ? [{ id: "j-1", name: "A fox and a lantern", status: "running" }] : [] }
    : { running: false, data, logs: path.join(data, "logs") }));
  process.exit(up ? 0 : 1);
} else if (cmd === "stop") {
  const s = read();
  if (s && alive(s.pid)) {
    if (process.env.FAKE_CORE_JOB === "1" && !argv.includes("--force")) { console.log("✗ jobs are running: A fox and a lantern"); process.exit(1); }
    process.kill(s.pid);
  }
  fs.rmSync(stateFile, { force: true });
  console.log("✓ the studio stopped");
} else if (cmd === "cert") {                       // specs/018: the TEST certificate
  const v = JSON.parse(fs.readFileSync(new URL("./vectors/share-cert.json", import.meta.url), "utf8"));
  console.log(JSON.stringify(v.host));
} else if (cmd === "check") {
  console.log(JSON.stringify({ ok: true, missing: [], data_default: data }));
} else {
  console.error(`fake core: unknown command ${argv.join(" ")}`);
  process.exit(2);
}
