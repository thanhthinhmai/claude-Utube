// @ts-check
// Sharing the studio with the team (specs/018): the Host's HTTPS gateway in front of the core, pairing bound to the
// certificate's fingerprint, and the Client side (pairing, pinned requests). No Electron in here, so `node --test`
// covers it; main.js only wires it to windows and the config.
"use strict";

const crypto = require("node:crypto");
const http = require("node:http");
const https = require("node:https");
const { Readable } = require("node:stream");

const ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
const DEFAULT_PORT = 47860;
const CODE_MS = 10 * 60_000;
const NONCE_MS = 2 * 60_000;
const CODE_TRIES = 5;
const MISSES = 10, WINDOW_MS = 10 * 60_000;
const MAX_BODY = 16 * 1024;

// ---------- codes, proofs, tokens (R2) ----------
function newCode() {
  const s = Array.from({ length: 10 }, () => ALPHABET[crypto.randomInt(ALPHABET.length)]).join("");
  return s.slice(0, 5) + "-" + s.slice(5);
}

/** "abcde fghjk" → "ABCDEFGHJK", or null. @param {string} code */
function normalizeCode(code) {
  const s = String(code || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  return s.length === 10 && [...s].every((c) => ALPHABET.includes(c)) ? s : null;
}

/** sha256 hex of a certificate (DER bytes or PEM text). @param {Buffer|string} cert */
function fingerprintOf(cert) {
  const der = typeof cert === "string" ? new crypto.X509Certificate(cert).raw : cert;
  return crypto.createHash("sha256").update(der).digest("hex");
}

/** @param {string} code @param {"host"|"client"} role @param {string} fp @param {string} nonceC @param {string} nonceH */
function proof(code, role, fp, nonceC, nonceH) {
  return crypto.createHmac("sha256", normalizeCode(code) || "").update(`${role}|${fp}|${nonceC}|${nonceH}`).digest("hex");
}

/** @param {string} a @param {string} b */
function sameHex(a, b) {
  const x = Buffer.from(String(a || ""), "hex"), y = Buffer.from(String(b || ""), "hex");
  return x.length === 32 && y.length === 32 && crypto.timingSafeEqual(x, y);
}

const newToken = () => crypto.randomBytes(32).toString("hex");
const tokenHash = (/** @type {string} */ t) => crypto.createHash("sha256").update(String(t)).digest("hex");

/** The paired, not removed client that sent `X-CU-Client: <id>.<token>`, or null.
 *  @param {{id: string, tokenHash: string, removed?: any}[]} clients @param {string|string[]|undefined} header */
function checkClient(clients, header) {
  const m = /^([0-9a-f-]{36})\.([0-9a-f]{64})$/.exec(String(header || ""));
  if (!m) return null;
  const c = (clients || []).find((x) => x.id === m[1] && !x.removed);
  return c && sameHex(c.tokenHash, tokenHash(m[2])) ? c : null;
}

/** @param {string} ip */
function isTailscale(ip) {
  const p = ip.split(".").map(Number);
  return p[0] === 100 && p[1] >= 64 && p[1] <= 127;
}

/** Addresses to give the team (R6). @param {NodeJS.Dict<import("node:os").NetworkInterfaceInfo[]>} ifaces @param {number} port */
function addresses(ifaces, port) {
  const out = [];
  for (const [name, list] of Object.entries(ifaces || {})) {
    if (/wsl|docker|vethernet|^br-|^veth|vmnet|virtualbox/i.test(name)) continue;
    for (const i of list || []) {
      if (i.internal || (i.family !== "IPv4" && /** @type {any} */ (i.family) !== 4)) continue;
      out.push({ address: `${i.address}:${port}`, kind: isTailscale(i.address) ? "tailscale" : "lan", name });
    }
  }
  return out.sort((a, b) => (a.kind === b.kind ? 0 : a.kind === "lan" ? -1 : 1));
}

/** The code the owner opened with "Add a computer": 10 minutes, one-use nonces, a few wrong tries. */
class Pairing {
  constructor(now = Date.now) {
    this.now = now;
    /** @type {{code: string, until: number, tries: number}|null} */ this.cur = null;
    /** @type {Map<string, {nonceC: string, at: number}>} */ this.nonces = new Map();
  }
  open() { this.cur = { code: newCode(), until: this.now() + CODE_MS, tries: 0 }; this.nonces.clear(); return { code: this.cur.code, until: this.cur.until }; }
  close() { this.cur = null; this.nonces.clear(); }
  active() { if (this.cur && this.now() >= this.cur.until) this.close(); return !!this.cur; }
  /** Step 1: the Host proves it knows the code, bound to its own certificate. @param {string} nonceC @param {string} fp */
  start(nonceC, fp) {
    if (!this.active() || !this.cur) return null;
    const nonceH = crypto.randomBytes(16).toString("hex");
    this.nonces.set(nonceH, { nonceC, at: this.now() });
    return { nonceH, proofH: proof(this.cur.code, "host", fp, nonceC, nonceH) };
  }
  /** Step 3: the Client proves it too, bound to the certificate it saw. @param {string} nonceH @param {string} proofC @param {string} fp */
  confirm(nonceH, proofC, fp) {
    const n = this.nonces.get(nonceH);
    this.nonces.delete(nonceH);
    if (!this.active() || !this.cur || !n || this.now() - n.at > NONCE_MS) return false;
    if (sameHex(proofC, proof(this.cur.code, "client", fp, n.nonceC, nonceH))) { this.close(); return true; }
    if (++this.cur.tries >= CODE_TRIES) this.close();
    return false;
  }
}

class Limiter {
  constructor(now = Date.now) { this.now = now; /** @type {Map<string, number[]>} */ this.hits = new Map(); }
  /** @param {string} ip */
  blocked(ip) { const q = (this.hits.get(ip) || []).filter((t) => t > this.now() - WINDOW_MS); this.hits.set(ip, q); return q.length >= MISSES; }
  /** @param {string} ip */
  miss(ip) { this.hits.set(ip, [...(this.hits.get(ip) || []), this.now()]); }
}

// ---------- the Host's gateway (R1) ----------
/** @param {http.IncomingMessage} req @returns {Promise<any>} */
function readJson(req) {
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (c) => { raw += c; if (raw.length > MAX_BODY) { reject(new Error("too large")); req.destroy(); } });
    req.on("end", () => { try { resolve(JSON.parse(raw || "{}")); } catch { reject(new Error("bad json")); } });
    req.on("error", reject);
  });
}

/** @param {http.ServerResponse} res @param {number} status @param {any} body */
function json(res, status, body) {
  res.writeHead(status, { "content-type": "application/json", "cache-control": "no-store" });
  res.end(JSON.stringify(body));
}

/** Pass a request on to a URL, streaming both ways. @param {http.IncomingMessage} req @param {http.ServerResponse} res
 *  @param {URL} target @param {Record<string, any>} headers */
function pass(req, res, target, headers) {
  const mod = target.protocol === "https:" ? https : http;
  const up = mod.request(target, { method: req.method, headers }, (r) => {
    res.writeHead(r.statusCode || 502, r.headers);
    r.pipe(res);
  });
  up.on("error", () => { if (!res.headersSent) json(res, 502, { code: "core_unreachable" }); else res.destroy(); });
  req.pipe(up);
}

/** Start the HTTPS gateway. `state.clients` is changed in place; `onChange` saves it.
 *  @param {{cert: string, key: string, port: number, host?: string, corePort: () => number, state: {hostId: string,
 *   clients: any[]}, pairing: Pairing, onChange?: () => void, update?: (() => ({server: string, lease: string}|null)) | null,
 *   now?: () => number}} o
 *  @returns {Promise<{port: number, stop: () => Promise<void>, fingerprint: string}>} */
function startGateway(o) {
  const now = o.now || Date.now;
  const fp = fingerprintOf(o.cert);
  const limiter = new Limiter(now);
  const seen = new Map();
  const server = https.createServer({ cert: o.cert, key: o.key }, async (req, res) => {
    const ip = req.socket.remoteAddress || "";
    const url = req.url || "/";
    try {
      if (url === "/__cu/hello") return json(res, 200, { app: "claude-Utube", hostId: o.state.hostId, pairing: o.pairing.active() });
      if (url === "/__cu/pair" && req.method === "POST") {
        if (limiter.blocked(ip)) return json(res, 429, { code: "rate_limited" });
        const b = await readJson(req);
        if (!/^[0-9a-f]{32}$/.test(String(b.nonceC))) return json(res, 422, { code: "invalid" });
        const r = o.pairing.start(b.nonceC, fp);
        if (!r) return json(res, 409, { code: "no_pairing" });
        o.pairing.nonces.get(r.nonceH).name = String(b.name || "computer").slice(0, 80);
        return json(res, 200, { hostId: o.state.hostId, ...r });
      }
      if (url === "/__cu/pair/confirm" && req.method === "POST") {
        if (limiter.blocked(ip)) return json(res, 429, { code: "rate_limited" });
        const b = await readJson(req);
        const n = o.pairing.nonces.get(String(b.nonceH));
        if (!o.pairing.confirm(String(b.nonceH), String(b.proofC), fp)) { limiter.miss(ip); return json(res, 403, { code: "wrong_code" }); }
        const token = newToken();
        const c = { id: crypto.randomUUID(), name: /** @type {any} */ (n).name || "computer", tokenHash: tokenHash(token),
          firstSeen: Math.floor(now() / 1000), lastSeen: Math.floor(now() / 1000), removed: null };
        o.state.clients.push(c);
        o.onChange && o.onChange();
        return json(res, 200, { clientId: c.id, token });
      }
      const client = checkClient(o.state.clients, req.headers["x-cu-client"]);
      if (!client) return json(res, 403, { code: "not_paired" });
      if (now() - (seen.get(client.id) || 0) > 60_000) {
        seen.set(client.id, now());
        client.lastSeen = Math.floor(now() / 1000);
        o.onChange && o.onChange();
      }
      const headers = { ...req.headers };
      delete headers["x-cu-client"];
      if (url === "/__cu/update" || url.startsWith("/__cu/update/")) {         // R5: through the Host's own license
        const src = o.update ? o.update() : null;
        if (!src) return json(res, 404, { code: "no_updates" });
        const rest = url.slice("/__cu/update".length);
        return pass(req, res, new URL(`${src.server}/api/license/releases${rest}`), { "x-cu-lease": src.lease, accept: "*/*" });
      }
      headers["x-forwarded-for"] = ip;
      return pass(req, res, new URL(`http://127.0.0.1:${o.corePort()}${url}`), headers);
    } catch {
      if (!res.headersSent) json(res, 400, { code: "bad_request" });
    }
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(o.port, o.host || "0.0.0.0", () => {
      const port = /** @type {import("node:net").AddressInfo} */ (server.address()).port;
      resolve({ port, fingerprint: fp, stop: () => new Promise((r) => { server.closeAllConnections(); server.close(() => r()); }) });
    });
  });
}

// ---------- the Client side (R2, R3) ----------
/** "https://10.0.0.5:47860/" or "10.0.0.5" → {host, port, address}. @param {string} a */
function parseAddress(a) {
  const s = String(a || "").trim().replace(/^https?:\/\//i, "").replace(/\/.*$/, "");
  const m = /^(\[[0-9a-f:]+\]|[A-Za-z0-9.-]+)(?::(\d{1,5}))?$/.exec(s);
  if (!m) return null;
  const port = m[2] ? Number(m[2]) : DEFAULT_PORT;
  return port > 0 && port < 65536 ? { host: m[1].replace(/^\[|\]$/g, ""), port, address: `${m[1]}:${port}` } : null;
}

/** One HTTPS request that reports the certificate it met. Never trusts a CA: the caller checks the fingerprint.
 *  @param {string} address @param {string} method @param {string} path @param {any} [body] @param {Record<string, string>} [headers]
 *  @returns {Promise<{status: number, body: any, fp: string}>} */
function call(address, method, path, body, headers = {}) {
  const a = parseAddress(address);
  if (!a) return Promise.reject(new Error("bad_address"));
  return new Promise((resolve, reject) => {
    const req = https.request({ host: a.host, port: a.port, method, path, rejectUnauthorized: false, agent: false, timeout: 15_000,
      headers: { "content-type": "application/json", ...headers } }, (res) => {
      const sock = /** @type {import("node:tls").TLSSocket} */ (res.socket);
      const fp = fingerprintOf(sock.getPeerCertificate(true).raw);
      let raw = "";
      res.on("data", (c) => { raw += c; });
      res.on("end", () => { let b = null; try { b = JSON.parse(raw); } catch { /* not json */ } resolve({ status: res.statusCode || 0, body: b, fp }); });
    });
    req.on("timeout", () => req.destroy(new Error("offline")));
    req.on("error", (e) => reject(/** @type {any} */ (e).message === "offline" ? e : new Error("offline")));
    req.end(body === undefined ? undefined : JSON.stringify(body));
  });
}

/** Pair with a Host (R2). Never sends the code; stops at once when the Host's proof does not match the certificate.
 *  @param {string} address @param {string} code @param {string} name */
async function pairWithHost(address, code, name) {
  const a = parseAddress(address);
  if (!a) throw new Error("bad_address");
  if (!normalizeCode(code)) throw new Error("bad_code");
  const hello = await call(a.address, "GET", "/__cu/hello");
  if (hello.status !== 200 || !hello.body || hello.body.app !== "claude-Utube") throw new Error("not_a_studio");
  const nonceC = crypto.randomBytes(16).toString("hex");
  const p = await call(a.address, "POST", "/__cu/pair", { nonceC, name });
  if (p.status === 409) throw new Error("no_pairing");
  if (p.status === 429) throw new Error("rate_limited");
  if (p.status !== 200 || p.fp !== hello.fp) throw new Error("not_the_host");
  if (!sameHex(p.body.proofH, proof(code, "host", p.fp, nonceC, p.body.nonceH))) throw new Error("wrong_code_or_not_the_host");
  const c = await call(a.address, "POST", "/__cu/pair/confirm", { nonceH: p.body.nonceH, proofC: proof(code, "client", p.fp, nonceC, p.body.nonceH) });
  if (c.fp !== p.fp) throw new Error("not_the_host");
  if (c.status === 429) throw new Error("rate_limited");
  if (c.status !== 200 || !c.body || !c.body.clientId) throw new Error("wrong_code");
  return { address: a.address, fingerprint: p.fp, hostId: p.body.hostId, clientId: c.body.clientId, token: c.body.token,
    pairedAt: Math.floor(Date.now() / 1000) };
}

/** "ok", "mismatch" (another certificate) or "offline". @param {{address: string, fingerprint: string}} h */
async function probeHost(h) {
  try {
    const r = await call(h.address, "GET", "/__cu/hello");
    return r.fp === h.fingerprint ? "ok" : "mismatch";
  } catch {
    return "offline";
  }
}

/** A fetch() that only talks to the paired Host (pinned fingerprint), for updates through it (R5).
 *  @param {string} fingerprint @returns {typeof fetch} */
function pinnedFetch(fingerprint) {
  return /** @type {any} */ ((/** @type {string} */ url, /** @type {any} */ init = {}) => new Promise((resolve, reject) => {
    const u = new URL(url);
    const req = https.request(u, { method: init.method || "GET", headers: init.headers || {}, rejectUnauthorized: false, agent: false }, (res) => {
      const sock = /** @type {import("node:tls").TLSSocket} */ (res.socket);
      if (fingerprintOf(sock.getPeerCertificate(true).raw) !== fingerprint) { res.destroy(); reject(new Error("not_the_host")); return; }
      resolve(new Response(/** @type {any} */ (Readable.toWeb(res)), { status: res.statusCode, headers: /** @type {any} */ (res.headers) }));
    });
    req.on("error", reject);
    req.end(init.body);
  }));
}

/** The header a Client sends on every request to its Host. @param {{clientId: string, token: string}} h */
const clientHeader = (h) => `${h.clientId}.${h.token}`;

/** Plain words for pairing errors. @param {string} code */
function describe(code) {
  return ({
    bad_address: "Type the address the studio owner gave you, like 192.168.1.20:47860.",
    bad_code: "The pairing code has 10 letters and digits, like ABCDE-FGHJK.",
    offline: "This computer cannot reach that address. Check that both computers are on the same network (or Tailscale) and that the studio is sharing.",
    not_a_studio: "That address is not a claude-Utube studio.",
    no_pairing: "The studio is not adding computers right now. Ask the owner to press Add a computer.",
    rate_limited: "Too many tries. Wait a few minutes.",
    wrong_code: "The pairing code is wrong or has expired.",
    wrong_code_or_not_the_host: "The pairing code is wrong, or this is not the studio you meant.",
    not_the_host: "This is not the studio you paired with.",
  })[code] || "Could not connect to the studio.";
}

module.exports = { ALPHABET, DEFAULT_PORT, CODE_MS, newCode, normalizeCode, fingerprintOf, proof, newToken, tokenHash,
  checkClient, isTailscale, addresses, Pairing, startGateway, parseAddress, pairWithHost, probeHost, pinnedFetch, clientHeader, describe };
