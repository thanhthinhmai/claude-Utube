// A fake studio core for the desktop shell's smoke run (specs/015 T006, T014): the same `app` commands as
// `sh bin/studio app …` (specs/014), with a tiny web server instead of the studio. GitHub Actions has no WSL2.
//   node fake-core.mjs app start|status|stop|check [--json] [--force] --data <dir>
// FAKE_CORE_JOB=1: `app status` reports one running job, so quitting has to ask.
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

if (cmd === "serve") {                              // the background web server
  const server = http.createServer((req, res) => {
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
    const child = spawn(process.execPath, [new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"), "app", "serve", "--data", data],
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
