// The license logic (specs/017 T014), checked against leases signed by the Python side (test/vectors).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const lic = require("../license.js");

const V = JSON.parse(fs.readFileSync(path.join(__dirname, "vectors", "vectors.json"), "utf8"));
const T0 = 1_800_000_000;

test("keys", () => {
  assert.equal(lic.normalizeKey("cu-abcd efgh-jkmn pqrs"), "CU-ABCD-EFGH-JKMN-PQRS");
  assert.equal(lic.normalizeKey("ABCDEFGHJKMNPQRS"), "CU-ABCD-EFGH-JKMN-PQRS");
  assert.equal(lic.normalizeKey("CU-0000-0000-0000-0000"), null);      // 0 is not in the alphabet
  assert.equal(lic.normalizeKey("short"), null);
});

test("machine id", () => {
  assert.equal(lic.parseMachineId("win32", "\r\nHKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Cryptography\r\n    MachineGuid    REG_SZ    3F2504E0-4F89-11D3-9A0C-0305E82C3301\r\n"),
    "3f2504e0-4f89-11d3-9a0c-0305e82c3301");
  assert.equal(lic.parseMachineId("darwin", '  "IOPlatformUUID" = "564D1E2A-AAAA-BBBB-CCCC-0123456789AB"\n'), "564d1e2a-aaaa-bbbb-cccc-0123456789ab");
  assert.equal(lic.parseMachineId("linux", "0123456789abcdef0123456789abcdef\n"), "0123456789abcdef0123456789abcdef");
  assert.equal(lic.parseMachineId("win32", "ERROR"), null);
  assert.match(lic.deviceIdFrom("x"), /^[0-9a-f]{64}$/);
  assert.notEqual(lic.deviceIdFrom("x"), lic.deviceIdFrom("y"));
  assert.equal(lic.machineIdCommand("win32").file, "reg.exe");
  assert.equal(lic.machineIdCommand("linux"), null);
});

test("leases signed by Python", () => {
  const p = lic.verifyLease(V.public, V.lease);
  assert.deepEqual(p, V.payload);
  assert.equal(lic.leaseProblem(p, V.device, T0), null);
  assert.equal(lic.leaseProblem(p, "f".repeat(64), T0), "device");
  assert.equal(lic.leaseProblem(p, V.device, T0 + 7 * 86400), "expired");
  assert.equal(lic.leaseProblem(p, V.device, T0 - 3600), "clock");                 // set back an hour
  assert.equal(lic.leaseProblem(p, V.device, T0 + 100, T0 + 3600), "clock");       // seen a later time before
  assert.equal(lic.leaseProblem(p, V.device, T0, T0 + 500), null);                 // inside the 10 minutes
  assert.equal(lic.leaseProblem({ ...p, keyExp: T0 + 10 }, V.device, T0 + 10), "key_expired");
  assert.equal(lic.leaseProblem(null, V.device, T0), "signature");
  // one changed character anywhere breaks it
  const [body, sig] = V.lease.split(".");
  const flip = (s, i) => s.slice(0, i) + (s[i] === "A" ? "B" : "A") + s.slice(i + 1);
  assert.equal(lic.verifyLease(V.public, flip(body, 5) + "." + sig), null);
  assert.equal(lic.verifyLease(V.public, body + "." + flip(sig, 3)), null);
  assert.equal(lic.verifyLease("A".repeat(43) + "=", V.lease), null);              // another key
  assert.equal(lic.verifyLease(V.public, "nonsense"), null);
});

test("release.json signed by Python", () => {
  const data = fs.readFileSync(path.join(__dirname, "vectors", "release.json"));
  const sig = fs.readFileSync(path.join(__dirname, "vectors", "release.json.sig"), "utf8");
  assert.equal(lic.verifyBytes(V.public, data, sig), true);
  const bad = Buffer.from(data); bad[10] ^= 1;
  assert.equal(lic.verifyBytes(V.public, bad, sig), false);
});

test("answers, clock, renew, gate", () => {
  assert.equal(lic.classifyResponse(200, { lease: "x.y" }), "ok");
  assert.equal(lic.classifyResponse(403, { code: "revoked" }), "refused");
  for (const [s, b] of [[429, { code: "rate_limited" }], [500, {}], [0, null], [403, {}]]) assert.equal(lic.classifyResponse(s, b), "offline");
  assert.equal(lic.nextClock(T0, T0 - 50, T0 + 5), T0 + 5);
  for (const r of [0, 0.5, 1]) { const d = lic.renewDelayMs(r); assert.ok(d >= 13 * 60_000 && d <= 17 * 60_000, String(d)); }
  assert.deepEqual(lic.gateDoc({ deviceId: "d", lease: "l", clock: 12.7, refused: null }), { deviceId: "d", lease: "l", clock: 12, refused: null });
  assert.match(lic.describe("device_limit"), /all the computers/);
  assert.match(lic.describe("whatever"), /not valid/);
});

test("licensing only when the build has a server and a key (FR-011)", () => {
  assert.equal(lic.licenseConfig(null, {}, true, ""), null);
  assert.equal(lic.licenseConfig({ licenseServer: "https://lic.example.com/" }, {}, true, ""), null);   // no public key
  assert.equal(lic.licenseConfig({ licenseServer: "https://lic.example.com" }, {}, true, "not a key"), null);
  assert.deepEqual(lic.licenseConfig({ licenseServer: "https://lic.example.com/" }, {}, true, V.public + "\n"),
    { server: "https://lic.example.com", publicKey: V.public });
  // test overrides work only when the app is not packaged
  const env = { CU_LICENSE_SERVER: "http://127.0.0.1:9", CU_LICENSE_PUBLIC_KEY: V.public };
  assert.equal(lic.licenseConfig(null, env, true, ""), null);
  assert.deepEqual(lic.licenseConfig(null, env, false, ""), { server: "http://127.0.0.1:9", publicKey: V.public });
});
