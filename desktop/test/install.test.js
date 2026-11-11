// Installing the packaged core (specs/016 T013, T020): node --test desktop/test
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const core = require("../core.js");

const M = { version: "0.1.0", os: "linux-x64", file: "claude-utube-core-linux-x64-0.1.0.tar.gz", sha256: "a".repeat(64),
  bytes: 1.5e9, unpacked_bytes: 4e9 };

test("manifest: read and refuse bad ones", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "cu-man-"));
  assert.equal(core.readManifest(dir), null);
  assert.equal(core.readManifest(null), null);
  fs.writeFileSync(path.join(dir, "core-manifest.json"), JSON.stringify(M));
  assert.deepEqual(core.readManifest(dir), M);
  for (const bad of [{ file: "../x.tar.gz" }, { sha256: "xyz" }, { version: "1 && rm" }, { bytes: "big" }]) {
    fs.writeFileSync(path.join(dir, "core-manifest.json"), JSON.stringify({ ...M, ...bad }));
    assert.equal(core.readManifest(dir), null, JSON.stringify(bad));
  }
});

test("sha256 of a file", async () => {
  const f = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "cu-sha-")), "x");
  fs.writeFileSync(f, "hello");
  assert.equal(await core.sha256File(f), crypto.createHash("sha256").update("hello").digest("hex"));
  await assert.rejects(core.sha256File(f + "-missing"));
});

test("space needed", () => {
  assert.equal(core.spaceNeeded(M, "win32"), 8e9 + 1024 ** 3);
  assert.equal(core.spaceNeeded(M, "darwin"), 4e9 + 1024 ** 3);
});

test("packaged config", () => {
  const w = core.packagedConfig("win32", M, "C:\\Users\\an");
  assert.equal(w.distro, "ClaudeUtube");
  assert.equal(w.studio, "/home/studio/claude-Utube");
  assert.equal(w.coreKind, "packaged");
  assert.equal(w.coreVersion, "0.1.0");
  assert.equal(core.configUsable(w, "win32", true), true);
  const m = core.packagedConfig("darwin", M, "/Users/an");
  assert.equal(m.studio, "/Users/an/Library/Application Support/ClaudeUtube-core/0.1.0");
  assert.equal(m.data, "/Users/an/Library/Application Support/ClaudeUtube");
  assert.ok(!m.studio.startsWith(m.data + "/"), "the core is not inside the data folder");
});

test("own distro, paths, versions", () => {
  const list = Buffer.from("  NAME           STATE    VERSION\r\n* Ubuntu         Running  2\r\n  ClaudeUtube    Stopped  2\r\n", "utf16le");
  assert.equal(core.hasOwnDistro(list), true);
  assert.equal(core.hasOwnDistro(Buffer.from("* Ubuntu Running 2\r\n", "utf16le")), false);
  assert.equal(core.wslPath("C:\\Users\\an\\AppData\\Local\\ClaudeUtube\\tmp"), "/mnt/c/Users/an/AppData/Local/ClaudeUtube/tmp");
  assert.equal(core.needsReinstall(null, M), false);
  assert.equal(core.needsReinstall("0.1.0\n", M), false);
  assert.equal(core.needsReinstall("0.0.9", M), true);
});

test("install steps: Windows, first time and reinstall", () => {
  const ctx = { manifest: M, coreFile: "C:\\app\\resources\\core\\x.tar.gz", tmpDir: "C:\\Users\\an\\AppData\\Local\\ClaudeUtube\\tmp",
    wslDir: "C:\\Users\\an\\AppData\\Local\\ClaudeUtube\\wsl", home: "C:\\Users\\an" };
  const first = core.installSteps("win32", ctx);
  assert.deepEqual(first.map((s) => s.id), ["verify", "space", "unpack", "install", "voice", "models", "check"]);
  const inst = first.find((s) => s.id === "install");
  assert.deepEqual(inst && inst.run, [{ file: "wsl.exe", args: ["--import", "ClaudeUtube", ctx.wslDir,
    "C:\\Users\\an\\AppData\\Local\\ClaudeUtube\\tmp\\core.tar", "--version", "2"] }]);
  const voice = first.find((s) => s.id === "voice");
  assert.deepEqual(voice && voice.run[0].args.slice(0, 4), ["-d", "ClaudeUtube", "--", "sh"]);
  assert.match(String(voice && voice.run[0].args[5]), /cd "\/home\/studio\/claude-Utube" && sh lib\/lemo-opuscar\/tools\/fetch.sh voice/);

  const again = core.installSteps("win32", { ...ctx, reinstall: true, distroThere: true });
  const cmds = (again.find((s) => s.id === "install") || { run: [] }).run.map((c) => c.args.join(" "));
  assert.equal(cmds.length, 5);
  assert.match(cmds[0], /app stop --force/);
  assert.match(cmds[1], /tar -czf "\/mnt\/c\/Users\/an\/AppData\/Local\/ClaudeUtube\/tmp\/data-backup.tgz" -C "\/home\/studio\/.local\/share\/claude-utube" \./);
  assert.equal(cmds[2], "--unregister ClaudeUtube");
  assert.match(cmds[3], /^--import ClaudeUtube/);
  assert.match(cmds[4], /tar -xzf .*data-backup.tgz.* && rm -f/);
});

test("install steps: macOS", () => {
  const steps = core.installSteps("darwin", { manifest: { ...M, os: "darwin-arm64" }, coreFile: "/Applications/claude-Utube.app/Contents/Resources/core/x.tar.gz",
    tmpDir: "/tmp", home: "/Users/an" });
  assert.deepEqual(steps.map((s) => s.id), ["verify", "space", "install", "voice", "models", "check"]);
  const run = (steps.find((s) => s.id === "install") || { run: [] }).run;
  const dir = "/Users/an/Library/Application Support/ClaudeUtube-core/0.1.0";
  assert.deepEqual(run[1], { file: "/usr/bin/tar", args: ["-xzf", "/Applications/claude-Utube.app/Contents/Resources/core/x.tar.gz", "-C", dir] });
  assert.deepEqual(run[2].args, ["-dr", "com.apple.quarantine", dir]);
  assert.deepEqual(run[3], { file: `${dir}/python/bin/python3`, args: ["-m", "venv", "--system-site-packages", `${dir}/tools/.venv`] });
  assert.equal(run[4].args[3], `${dir}/lib/lemo-opuscar/.venv`);
  assert.equal(core.espeakPathOk(dir), true);
  assert.equal(core.espeakPathOk("/Users/" + "x".repeat(60) + "/Library/Application Support/ClaudeUtube-core/0.1.0"), false);
});
