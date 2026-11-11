// A fake license server for the desktop smoke runs (specs/017 T016, T020), signing with the TEST key in vectors/.
//   node test/fake-license.mjs <port> [release-dir]
// Key CU-TEST-TEST-TEST-TEST is good until POST /__revoke. With a release dir (release.json, its .sig and the
// installers), /api/license/releases[/<name>] serve it to a good lease.
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const V = JSON.parse(fs.readFileSync(path.join(here, "vectors", "vectors.json"), "utf8"));
const b64u = (b) => Buffer.from(b).toString("base64url");
const priv = crypto.createPrivateKey({ key: { kty: "OKP", crv: "Ed25519", d: b64u(Buffer.from(V.private_test_only, "base64")),
  x: b64u(Buffer.from(V.public, "base64")) }, format: "jwk" });
const port = Number(process.argv[2] || 0);
const releaseDir = process.argv[3] || null;
let revoked = false;
const leases = new Set();

function sign(payload) {
  const body = b64u(JSON.stringify(payload));
  return body + "." + b64u(crypto.sign(null, Buffer.from(body), priv));
}
const json = (res, status, body) => { res.writeHead(status, { "content-type": "application/json" }); res.end(JSON.stringify(body)); };

http.createServer((req, res) => {
  let raw = "";
  req.on("data", (c) => { raw += c; });
  req.on("end", () => {
    if (req.method === "POST" && req.url === "/__revoke") { revoked = true; return json(res, 200, { ok: true }); }
    if (req.method === "POST" && req.url === "/api/license/lease") {
      let b = {};
      try { b = JSON.parse(raw); } catch { /* empty */ }
      const key = String(b.key || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
      if (key !== "CUTESTTESTTESTTEST") return json(res, 403, { code: "unknown", error: "wrong key" });
      if (revoked) return json(res, 403, { code: "revoked", error: "turned off" });
      const now = Math.floor(Date.now() / 1000);
      const lease = sign({ v: 1, lid: "smoke", did: b.deviceId, label: "Smoke test", iat: now, exp: now + 7 * 86400, keyExp: null });
      leases.add(lease);
      return json(res, 200, { lease, label: "Smoke test", expiresAt: null, serverTime: now });
    }
    if (req.url.startsWith("/api/license/releases")) {
      if (revoked || !leases.has(req.headers["x-cu-lease"])) return json(res, 403, { code: "not_licensed" });
      if (!releaseDir) return json(res, 404, { code: "no_release" });
      const rel = JSON.parse(fs.readFileSync(path.join(releaseDir, "release.json"), "utf8"));
      const names = ["release.json", "release.json.sig", ...rel.files.map((f) => f.name)];
      if (req.url === "/api/license/releases") {
        return json(res, 200, { tag: rel.tag, version: rel.version,
          assets: names.map((n) => ({ name: n, size: fs.statSync(path.join(releaseDir, n)).size })) });
      }
      const name = decodeURIComponent(req.url.split("/").pop());
      if (!names.includes(name)) return json(res, 404, { code: "not_found" });
      res.writeHead(200, { "content-type": "application/octet-stream", "content-length": fs.statSync(path.join(releaseDir, name)).size });
      return fs.createReadStream(path.join(releaseDir, name)).pipe(res);
    }
    json(res, 404, { code: "not_found" });
  });
}).listen(port, "127.0.0.1", function () { console.log(`fake license on ${this.address().port}`); });
