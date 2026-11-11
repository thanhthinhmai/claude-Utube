// Sharing with the team (specs/018 T006; SC-002, SC-003, SC-004): pairing, the gateway, a fake Host, the bytes on the wire.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const path = require("node:path");
const sh = require("../share.js");

const C = JSON.parse(fs.readFileSync(path.join(__dirname, "vectors", "share-cert.json"), "utf8"));

/** A fake core: echoes the request, streams an SSE line, serves a big file. */
function fakeCore() {
  return new Promise((resolve) => {
    const s = http.createServer((req, res) => {
      if (req.url === "/big") { res.writeHead(200); res.end(Buffer.alloc(3 * 1024 * 1024, 7)); return; }
      if (req.url === "/events") { res.writeHead(200, { "content-type": "text/event-stream" }); res.write("data: hi\n\n"); setTimeout(() => res.end(), 50); return; }
      let raw = "";
      req.on("data", (c) => { raw += c; });
      req.on("end", () => { res.writeHead(200, { "content-type": "application/json", "set-cookie": "sid=SECRETCOOKIE" });
        res.end(JSON.stringify({ url: req.url, method: req.method, host: req.headers.host, hasClientHeader: "x-cu-client" in req.headers, body: raw })); });
    });
    s.listen(0, "127.0.0.1", () => resolve(s));
  });
}

async function host(cert = C.host, now) {
  const core = await fakeCore();
  const state = { hostId: "11111111-1111-1111-1111-111111111111", clients: [] };
  const pairing = new sh.Pairing(now);
  const g = await sh.startGateway({ cert: cert.cert, key: cert.key, port: 0, host: "127.0.0.1", corePort: () => core.address().port,
    state, pairing, now });
  return { core, state, pairing, g, address: `127.0.0.1:${g.port}`, close: async () => { await g.stop(); core.close(); } };
}

/** GET through the pinned fetch with the client header. */
async function get(h, paired, p) {
  const r = await sh.pinnedFetch(paired.fingerprint)(`https://${h.address}${p}`, { headers: { "x-cu-client": sh.clientHeader(paired) } });
  return { status: r.status, text: Buffer.from(await r.arrayBuffer()).toString() };
}

test("codes, proofs, addresses", () => {
  const code = sh.newCode();
  assert.match(code, /^[A-HJ-NP-Z2-9]{5}-[A-HJ-NP-Z2-9]{5}$/);
  assert.equal(sh.normalizeCode(code.toLowerCase().replace("-", " ")), code.replace("-", ""));
  assert.equal(sh.normalizeCode("short"), null);
  assert.equal(sh.fingerprintOf(C.host.cert), C.host.fingerprint);                     // same as Python's
  assert.notEqual(sh.proof(code, "host", "f", "a", "b"), sh.proof(code, "client", "f", "a", "b"));
  assert.notEqual(sh.proof(code, "host", "f1", "a", "b"), sh.proof(code, "host", "f2", "a", "b"));
  const a = sh.addresses({ eth0: [{ address: "192.168.1.5", family: "IPv4", internal: false }, { address: "fe80::1", family: "IPv6", internal: false }],
    lo: [{ address: "127.0.0.1", family: "IPv4", internal: true }], tailscale0: [{ address: "100.101.2.3", family: "IPv4", internal: false }],
    "vEthernet (WSL)": [{ address: "172.20.0.1", family: "IPv4", internal: false }] }, 47860);
  assert.deepEqual(a.map((x) => [x.address, x.kind]), [["192.168.1.5:47860", "lan"], ["100.101.2.3:47860", "tailscale"]]);
  assert.deepEqual(sh.parseAddress("https://10.0.0.5/x"), { host: "10.0.0.5", port: 47860, address: "10.0.0.5:47860" });
  assert.equal(sh.parseAddress("bad address!"), null);
});

test("pair, then requests reach the core (SSE, big files)", async () => {
  const h = await host();
  try {
    await assert.rejects(sh.pairWithHost(h.address, "ABCDE-FGHJK", "PC"), /no_pairing/);
    const { code } = h.pairing.open();
    const p = await sh.pairWithHost(h.address, code, "An's laptop");
    assert.equal(p.fingerprint, C.host.fingerprint);
    assert.equal(h.state.clients.length, 1);
    assert.equal(h.state.clients[0].name, "An's laptop");
    assert.ok(!JSON.stringify(h.state).includes(p.token), "only the token's hash is kept");
    assert.equal(h.pairing.active(), false, "a code pairs one computer");
    const r = await get(h, p, "/api/v1/jobs?x=1");
    const j = JSON.parse(r.text);
    assert.deepEqual([r.status, j.url, j.hasClientHeader, j.host], [200, "/api/v1/jobs?x=1", false, h.address]);
    assert.equal((await get(h, p, "/events")).text, "data: hi\n\n");
    assert.equal((await get(h, p, "/big")).text.length, 3 * 1024 * 1024);
    assert.equal(await sh.probeHost(p), "ok");
    // no header, a wrong token, a removed computer: refused
    assert.equal((await get(h, { ...p, token: "0".repeat(64) }, "/x")).status, 403);
    h.state.clients[0].removed = 1;
    assert.equal((await get(h, p, "/x")).status, 403);
  } finally { await h.close(); }
});

test("wrong codes, expiry, limits", async () => {
  let t = 1_000_000;
  const h = await host(C.host, () => t);
  try {
    h.pairing.open();
    await assert.rejects(sh.pairWithHost(h.address, "ABCDE-FGHJK", "PC"), /wrong_code_or_not_the_host/);
    assert.equal(h.state.clients.length, 0);
    const { code } = h.pairing.open();
    t += sh.CODE_MS + 1;                                                                // 10 minutes later
    await assert.rejects(sh.pairWithHost(h.address, code, "PC"), /no_pairing/);
    // a client that sends wrong proofs directly: the code dies after 5, the address is blocked after 10
    for (let i = 0; i < 10; i++) {
      h.pairing.open();
      const n = await post(h.address, "/__cu/pair", { nonceC: "a".repeat(32), name: "x" });
      const r = await post(h.address, "/__cu/pair/confirm", { nonceH: n.body.nonceH, proofC: "b".repeat(64) });
      assert.equal(r.status, 403);
    }
    h.pairing.open();
    assert.equal((await post(h.address, "/__cu/pair", { nonceC: "a".repeat(32) })).status, 429);
  } finally { await h.close(); }
});

/** @param {string} address @param {string} p @param {any} body */
function post(address, p, body) {
  const [hostName, port] = address.split(":");
  return new Promise((resolve, reject) => {
    const req = require("node:https").request({ host: hostName, port, path: p, method: "POST", rejectUnauthorized: false, agent: false,
      headers: { "content-type": "application/json" } }, (res) => {
      let raw = ""; res.on("data", (c) => { raw += c; }); res.on("end", () => resolve({ status: res.statusCode, body: raw ? JSON.parse(raw) : null }));
    });
    req.on("error", reject);
    req.end(JSON.stringify(body));
  });
}

test("a fake Host with another certificate is caught before the client proves anything (SC-003)", async () => {
  const real = await host(C.host);
  // the impostor relays to the real Host but shows its own certificate
  const imp = await host(C.impostor);
  try {
    const { code } = real.pairing.open();
    imp.pairing.cur = { ...real.pairing.cur };                                          // even knowing the code's slot,
    imp.pairing.cur.code = "ZZZZZ-ZZZZZ";                                               // it does not know the code
    await assert.rejects(sh.pairWithHost(imp.address, code, "PC"), /wrong_code_or_not_the_host/);
    assert.equal(imp.state.clients.length, 0);
    // a paired client refuses a Host whose certificate changed
    const p = await sh.pairWithHost(real.address, code, "PC");
    assert.equal(await sh.probeHost({ ...p, address: imp.address }), "mismatch");
    await assert.rejects(sh.pinnedFetch(p.fingerprint)(`https://${imp.address}/x`), /not_the_host/);
  } finally { await real.close(); await imp.close(); }
});

test("the bytes on the wire hold no password or cookie (SC-002)", async () => {
  const h = await host();
  const seen = [];
  const relay = net.createServer((c) => {                                               // a TCP relay that keeps every byte
    const u = net.connect(h.g.port, "127.0.0.1");
    c.on("data", (d) => { seen.push(d); u.write(d); });
    u.on("data", (d) => { seen.push(d); c.write(d); });
    c.on("close", () => u.destroy()); u.on("close", () => c.destroy());
  });
  await new Promise((r) => relay.listen(0, "127.0.0.1", r));
  try {
    const address = `127.0.0.1:${relay.address().port}`;
    const { code } = h.pairing.open();
    const p = await sh.pairWithHost(address, code, "PC");
    const r = await sh.pinnedFetch(p.fingerprint)(`https://${address}/api/v1/auth/login`, { method: "POST",
      headers: { "x-cu-client": sh.clientHeader(p), "content-type": "application/json" },
      body: JSON.stringify({ email: "an@example.com", password: "MY-PASSWORD-123" }) });
    assert.equal(r.status, 200);
    assert.match(Buffer.from(await r.arrayBuffer()).toString(), /MY-PASSWORD-123/);         // it reached the core
    const all = Buffer.concat(seen).toString("latin1");
    for (const secret of ["MY-PASSWORD-123", "SECRETCOOKIE", code.replace("-", ""), p.token, "/api/v1/auth/login"]) assert.ok(!all.includes(secret), secret);
  } finally { relay.close(); await h.close(); }
});

test("stopping sharing closes the port within 2 seconds (SC-004)", async () => {
  const h = await host();
  const t0 = Date.now();
  await h.g.stop();
  assert.ok(Date.now() - t0 < 2000);
  await assert.rejects(new Promise((resolve, reject) => {
    const s = net.connect(h.g.port, "127.0.0.1"); s.on("connect", () => { s.destroy(); resolve(); }); s.on("error", reject);
  }));
  h.core.close();
});
