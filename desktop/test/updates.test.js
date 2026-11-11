// Updates (specs/017 T018; SC-004): versions, signed release.json, checked downloads.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const up = require("../updates.js");

const V = JSON.parse(fs.readFileSync(path.join(__dirname, "vectors", "vectors.json"), "utf8"));
const REL = fs.readFileSync(path.join(__dirname, "vectors", "release.json"));
const SIG = fs.readFileSync(path.join(__dirname, "vectors", "release.json.sig"), "utf8");

test("versions", () => {
  assert.equal(up.newer("0.2.0", "0.1.0"), true);
  assert.equal(up.newer("0.10.0", "0.9.9"), true);
  assert.equal(up.newer("0.1.0", "0.1.0"), false);
  assert.equal(up.newer("0.1.0", "0.2.0"), false);
  assert.equal(up.newer("0.2.0", "0.2.0-test"), true);
  assert.equal(up.newer("0.2.0-test", "0.2.0"), false);
  assert.equal(up.newer("junk", "0.1.0"), false);
});

test("signed release.json", () => {
  const r = up.verifyRelease(V.public, REL, SIG);
  assert.equal(r && r.version, "0.2.0");
  assert.equal(up.pickAsset(r, "win32").name, "claude-Utube-Setup-0.2.0.exe");
  assert.equal(up.pickAsset(r, "darwin"), null);
  const bad = Buffer.from(REL); bad[bad.indexOf("0.2.0")] = "9".charCodeAt(0);
  assert.equal(up.verifyRelease(V.public, bad, SIG), null);                        // one byte changed
});

/** A fetch that answers with fixed bytes. @param {Buffer} bytes */
const fakeFetch = (bytes, status = 200) => async () => new Response(bytes, { status });

test("downloads are checked; one changed byte is refused (SC-004)", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "cu-up-"));
  const data = crypto.randomBytes(5000);
  const want = { size: data.length, sha256: crypto.createHash("sha256").update(data).digest("hex") };
  const file = path.join(dir, "a.exe");
  await up.downloadTo("http://x/a.exe", {}, file, want, fakeFetch(data));
  assert.deepEqual(fs.readFileSync(file), data);
  await up.downloadTo("http://x/a.exe", {}, file, want, async () => { throw new Error("must not download again"); });
  const bad = Buffer.from(data); bad[100] ^= 1;
  const file2 = path.join(dir, "b.exe");
  await assert.rejects(up.downloadTo("http://x/b.exe", {}, file2, want, fakeFetch(bad)), /does not match/);
  assert.equal(fs.existsSync(file2) || fs.existsSync(file2 + ".part"), false);
  await assert.rejects(up.downloadTo("http://x/c.exe", {}, path.join(dir, "c.exe"), want, fakeFetch(data, 403)), /403/);
  up.cleanDir(dir, file);
  assert.deepEqual(fs.readdirSync(dir), ["a.exe"]);
  const cmd = up.installCommand("C:\\Users\\O'Neil\\x.exe");
  assert.equal(cmd.file, "powershell.exe");
  assert.match(cmd.args.at(-1), /^Start-Sleep -Seconds 3; Start-Process -FilePath 'C:\\Users\\O''Neil\\x\.exe' -ArgumentList '\/S','--updated','--force-run'$/);
});
