// A fake Host for the Client smoke run (specs/018 T009, T011): the real share gateway with the TEST certificate,
// in front of a tiny fake core.
//   node test/fake-host.mjs <gateway port> <control port> <out file> [fake license URL]
// Writes "<address>|<pairing code>" to <out file>. POST <control>/stop closes the gateway.
// With a fake license URL, it takes a lease with the test key and passes updates on to paired Clients.
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const share = require("../share.js");
const V = JSON.parse(fs.readFileSync(new URL("./vectors/share-cert.json", import.meta.url), "utf8")).host;
const [port, controlPort, outFile, licenseUrl] = process.argv.slice(2);

const core = http.createServer((req, res) => {
  res.writeHead(200, { "content-type": "text/html" });
  res.end("<!doctype html><title>fake core</title><h1>fake core</h1>");
});
await new Promise((r) => core.listen(0, "127.0.0.1", r));

let lease = null;
if (licenseUrl) {
  const r = await fetch(`${licenseUrl}/api/license/lease`, { method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ key: "CU-TEST-TEST-TEST-TEST", deviceId: crypto.randomBytes(32).toString("hex") }) });
  lease = (await r.json()).lease;
}

const state = { hostId: crypto.randomUUID(), clients: [] };
const pairing = new share.Pairing();
const g = await share.startGateway({ cert: V.cert, key: V.key, port: Number(port), host: "127.0.0.1", corePort: () => core.address().port,
  state, pairing, update: () => (lease ? { server: licenseUrl, lease } : null) });
const { code } = pairing.open();
fs.writeFileSync(outFile, `127.0.0.1:${g.port}|${code}`);
console.log(`fake host on 127.0.0.1:${g.port}, code ${code}`);

http.createServer(async (req, res) => {
  if (req.url === "/stop") { await g.stop(); res.end("stopped"); console.log("gateway stopped"); return; }
  res.writeHead(404); res.end();
}).listen(Number(controlPort), "127.0.0.1");
