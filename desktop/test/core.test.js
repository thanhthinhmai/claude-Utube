// The desktop shell's logic (specs/015 T005, T010): node --test desktop/test
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const core = require("../core.js");

const MAC = { platform: "darwin", distro: null, studio: "~/claude-Utube", data: "~/Library/Application Support/ClaudeUtube", home: "/Users/an" };
const WIN = { platform: "win32", distro: "Ubuntu", studio: "~/claude-Utube", data: "~/.local/share/claude-utube", home: "/home/an" };

test("config: save, load, usable", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "cu-cfg-"));
  assert.equal(core.loadConfig(dir), null);
  core.saveConfig(dir, WIN);
  assert.deepEqual(core.loadConfig(dir), WIN);
  assert.equal(core.configUsable(WIN, "win32", true), true);
  assert.equal(core.configUsable(WIN, "win32", false), false);              // bin/studio is gone
  assert.equal(core.configUsable({ ...WIN, distro: null }, "win32", true), false);
  assert.equal(core.configUsable(WIN, "darwin", true), false);              // copied from another OS
  assert.equal(core.configUsable(null, "darwin", true), false);
});

test("home", () => {
  assert.equal(core.expandHome("~/x/y", "/home/an/"), "/home/an/x/y");
  assert.equal(core.expandHome("/abs", "/home/an"), "/abs");
  assert.equal(core.expandHome("~", "/home/an"), "/home/an");
});

test("core commands per OS", () => {
  const mac = core.coreCommand(MAC, ["start"], { PATH: "/usr/bin" });
  assert.equal(mac.file, "/bin/sh");
  assert.deepEqual(mac.args, ["/Users/an/claude-Utube/bin/studio", "app", "start", "--data", "/Users/an/Library/Application Support/ClaudeUtube"]);
  assert.match(mac.env.PATH, /^\/opt\/homebrew\/bin:/);
  const win = core.coreCommand(WIN, ["status", "--json"], {});
  assert.equal(win.file, "wsl.exe");
  assert.deepEqual(win.args, ["-d", "Ubuntu", "--cd", "/home/an/claude-Utube", "--", "sh", "bin/studio", "app", "status", "--json",
    "--data", "/home/an/.local/share/claude-utube"]);
  const fake = core.coreCommand(WIN, ["stop"], { CU_CORE_CMD: '["node","fake-core.mjs"]' });
  assert.deepEqual([fake.file, ...fake.args], ["node", "fake-core.mjs", "app", "stop", "--data", "/home/an/.local/share/claude-utube"]);
  assert.deepEqual(core.shellCommand(WIN, "echo $HOME"), { file: "wsl.exe", args: ["-d", "Ubuntu", "--", "sh", "-c", "echo $HOME"] });
});

test("url and status", () => {
  assert.equal(core.parseUrl("! warning\n✓ running\nURL: http://127.0.0.1:8791\n"), "http://127.0.0.1:8791");
  assert.equal(core.parseUrl("URL: http://evil.example:80"), null);
  const s = core.parseStatus('{"running": true, "url": "http://127.0.0.1:8790", "jobs_running": 1, "jobs": [{"id": "j1", "name": "A fox"}]}');
  assert.equal(s.running, true);
  assert.equal(s.jobs[0].name, "A fox");
  assert.deepEqual(core.parseStatus("✗ not running").running, false);
  assert.deepEqual(core.parseStatus('{"running": false, "data": "/d"}').jobs, []);
  assert.equal(core.portOf("http://127.0.0.1:8792/#/jobs"), 8792);
});

test("wsl -l -v in UTF-16LE", () => {
  const text = "  NAME                   STATE           VERSION\r\n* Ubuntu-24.04           Running         2\r\n  Debian                 Stopped         1\r\n  docker-desktop         Stopped         2\r\n  Alpine                 Stopped         2\r\n";
  const withBom = Buffer.concat([Buffer.from([0xff, 0xfe]), Buffer.from(text, "utf16le")]);
  const rows = core.parseWslList(withBom);
  assert.deepEqual(rows.map((r) => [r.name, r.version, r.isDefault]), [["Ubuntu-24.04", 2, true], ["Debian", 1, false],
    ["docker-desktop", 2, false], ["Alpine", 2, false]]);
  assert.deepEqual(core.wsl2Distros(Buffer.from(text, "utf16le")), ["Ubuntu-24.04", "Alpine"]);   // no BOM, WSL1 and Docker left out
  assert.deepEqual(core.wsl2Distros(""), []);
});

test("wsl --status", () => {
  const ok = core.wslStatusChecks("Default Distribution: Ubuntu\nDefault Version: 2\n", 0);
  assert.ok(ok.every((c) => c.ok));
  const none = core.wslStatusChecks("The Windows Subsystem for Linux is not installed. You can install by running 'wsl --install'.", 1);
  assert.equal(none.find((c) => c.id === "wsl").ok, false);
  const virt = core.wslStatusChecks("Please enable the Virtual Machine Platform Windows feature and ensure virtualization is enabled in the BIOS.", 0);
  assert.equal(virt.find((c) => c.id === "virtualization").ok, false);
  const v1 = core.wslStatusChecks("Default Distribution: Ubuntu\nDefault Version: 1\n", 0);
  assert.equal(v1.find((c) => c.id === "wsl2").ok, false);
  const utf16 = core.wslStatusChecks(Buffer.from("Default Version: 2\r\n", "utf16le"), 0);
  assert.ok(utf16.every((c) => c.ok));
});

test("turning WSL on asks Windows for administrator rights", () => {
  const c = core.enableWslCommand();
  assert.equal(c.file, "powershell.exe");
  assert.match(c.args.join(" "), /Start-Process wsl -ArgumentList '--install','--no-distribution' -Verb RunAs/);
});

test("setup checks and free space", () => {
  const good = core.machineChecks({ ok: true, missing: [] }, 42.5);
  assert.ok(good.every((c) => c.ok));
  const bad = core.machineChecks({ ok: false, missing: ["ffmpeg: install ffmpeg"] }, 2);
  assert.deepEqual(bad.map((c) => c.ok), [false, false]);
  assert.match(bad[0].detail, /ffmpeg/);
  assert.equal(core.machineChecks(null, null)[0].ok, false);
  assert.equal(core.parseDf("Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/sdc 1000 10 10485760 1% /\n"), 10);
  assert.equal(core.parseDf("nonsense"), null);
});

test("only the studio's pages open in the window", () => {
  assert.equal(core.isAppUrl("http://127.0.0.1:8790/#/jobs/x", 8790), true);
  assert.equal(core.isAppUrl("http://127.0.0.1:8791/", 8790), false);
  assert.equal(core.isAppUrl("http://localhost:8790/", 8790), false);
  assert.equal(core.isAppUrl("http://127.0.0.1.evil.example:8790/", 8790), false);
  assert.equal(core.isAppUrl("https://www.youtube.com/watch?v=x", 8790), false);
  assert.equal(core.isAppUrl("not a url", 8790), false);
});

test("quitting asks first when jobs run (SC-004)", () => {
  const busy = core.quitPlan({ running: true, jobs_running: 2, jobs: [{ name: "A fox" }, { name: "Honey" }] });
  assert.deepEqual(busy, { ask: true, names: ["A fox", "Honey"], stopArgs: ["stop", "--force"], stop: true });
  const idle = core.quitPlan({ running: true, jobs_running: 0, jobs: [] });
  assert.deepEqual(idle, { ask: false, names: [], stopArgs: ["stop"], stop: true });
  const down = core.quitPlan({ running: false, jobs_running: 0, jobs: [] });
  assert.equal(down.stop, false);
  assert.equal(down.ask, false);
});
