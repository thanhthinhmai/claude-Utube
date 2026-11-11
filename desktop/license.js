// @ts-check
// The desktop app's license logic, with no Electron in it (specs/017 research R2–R4, R8), so `node --test` covers it.
// main.js calls the server, stores the key and shows the screens; this file decides what answers and leases mean.
"use strict";

const crypto = require("node:crypto");

const ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
const RENEW_MS = 15 * 60_000;
const RENEW_JITTER_MS = 2 * 60_000;
const CLOCK_SKEW_S = 600;

/** "cu-abcd efgh…" → "CU-ABCD-EFGH-…", or null. @param {string} key */
function normalizeKey(key) {
  let s = String(key || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  if (s.startsWith("CU") && s.length === 18) s = s.slice(2);
  if (s.length !== 16 || [...s].some((c) => !ALPHABET.includes(c))) return null;
  return "CU-" + s.match(/.{4}/g).join("-");
}

/** The id sent to the server: a hash, never the machine's own id (R3). @param {string} raw */
function deviceIdFrom(raw) {
  return crypto.createHash("sha256").update("claude-utube-device:" + raw).digest("hex");
}

/** How to read the machine id; Linux reads /etc/machine-id. @param {string} platform */
function machineIdCommand(platform) {
  if (platform === "win32") return { file: "reg.exe", args: ["query", "HKLM\\SOFTWARE\\Microsoft\\Cryptography", "/v", "MachineGuid"] };
  if (platform === "darwin") return { file: "/usr/sbin/ioreg", args: ["-rd1", "-c", "IOPlatformExpertDevice"] };
  return null;
}

/** @param {string} platform @param {string} out */
function parseMachineId(platform, out) {
  const text = String(out || "");
  const m = platform === "win32" ? /MachineGuid\s+REG_SZ\s+([0-9a-fA-F-]{8,})/.exec(text)
    : platform === "darwin" ? /"IOPlatformUUID"\s*=\s*"([0-9A-Fa-f-]{8,})"/.exec(text)
      : /^([0-9a-f]{16,})\s*$/m.exec(text);
  return m ? m[1].toLowerCase() : null;
}

/** @param {string} s */
const unb64u = (s) => Buffer.from(s.replace(/-/g, "+").replace(/_/g, "/"), "base64");

/** Ed25519 public key from base64 of its 32 raw bytes. @param {string} pubB64 */
function publicKey(pubB64) {
  const raw = Buffer.from(String(pubB64 || "").trim(), "base64");
  if (raw.length !== 32) return null;
  return crypto.createPublicKey({ key: { kty: "OKP", crv: "Ed25519", x: raw.toString("base64url") }, format: "jwk" });
}

/** @param {string} pubB64 @param {Buffer} data @param {string} sigB64u */
function verifyBytes(pubB64, data, sigB64u) {
  try {
    const k = publicKey(pubB64);
    return !!k && crypto.verify(null, data, k, unb64u(String(sigB64u || "").trim()));
  } catch {
    return false;
  }
}

/** The payload of a lease with a good signature, or null. @param {string} pubB64 @param {string|null|undefined} lease */
function verifyLease(pubB64, lease) {
  if (typeof lease !== "string" || lease.split(".").length !== 2) return null;
  const [body, sig] = lease.split(".");
  if (!verifyBytes(pubB64, Buffer.from(body), sig)) return null;
  try {
    const p = JSON.parse(unb64u(body).toString("utf8"));
    return p && p.v === 1 ? p : null;
  } catch {
    return null;
  }
}

/** Why a lease cannot be used now, or null (same rules as tools/license/signing.py).
 *  @param {any} p @param {string} deviceId @param {number} nowS @param {number} clockS */
function leaseProblem(p, deviceId, nowS, clockS = 0) {
  if (!p) return "signature";
  if (p.did !== deviceId) return "device";
  if (nowS < Math.max(p.iat || 0, clockS || 0) - CLOCK_SKEW_S) return "clock";
  if (p.keyExp && nowS >= p.keyExp) return "key_expired";
  if (nowS >= (p.exp || 0)) return "expired";
  return null;
}

/** The highest time seen, to catch a clock set back. @param {number} clockS @param {number} nowS @param {number} [serverS] */
function nextClock(clockS, nowS, serverS) {
  return Math.max(clockS || 0, nowS || 0, serverS || 0);
}

/** What a lease call's answer means: ok, refused (stay locked even offline), or offline (keep the old lease).
 *  @param {number} status @param {any} body */
function classifyResponse(status, body) {
  if (status === 200 && body && typeof body.lease === "string") return "ok";
  if (status === 403 && body && typeof body.code === "string") return "refused";
  return "offline";
}

/** 15 minutes ± 2, so all computers do not call at once. @param {number} rand 0..1 @param {number} [base] */
function renewDelayMs(rand, base = RENEW_MS) {
  return Math.round(base + (rand * 2 - 1) * Math.min(RENEW_JITTER_MS, base / 4));
}

/** Plain words for a refusal or a lease problem. @param {string|null|undefined} code */
function describe(code) {
  return ({
    unknown: "This key is not right. Check it and try again.",
    revoked: "This key was turned off by the studio owner.",
    expired: "This key has expired. Ask the studio owner for a new one.",
    key_expired: "This key has expired. Ask the studio owner for a new one.",
    device_limit: "This key is already used on all the computers it allows. Ask the studio owner to remove one.",
    device_removed: "This computer was removed from the key by the studio owner.",
    rate_limited: "Too many tries. Wait a few minutes and try again.",
    offline: "The license server cannot be reached. Check the internet connection and try again.",
    signature: "The license could not be checked. Enter the key again.",
    device: "The license belongs to another computer. Enter the key again.",
    clock: "This computer's clock is wrong. Set the right date and time, then try again.",
  })[String(code)] || "The license is not valid. Enter the key again.";
}

/** The licensing of this build, or null when it has none (FR-011). Test overrides only work unpackaged.
 *  @param {{licenseServer?: string}|null} build @param {Record<string, string|undefined>} env @param {boolean} packaged
 *  @param {string} keyFile the text of license-public-key.txt */
function licenseConfig(build, env, packaged, keyFile) {
  const server = (!packaged && env.CU_LICENSE_SERVER) || (build && build.licenseServer) || "";
  const publicKeyB64 = ((!packaged && env.CU_LICENSE_PUBLIC_KEY) || keyFile || "").trim();
  if (!server || !publicKeyB64 || !publicKey(publicKeyB64)) return null;
  return { server: server.replace(/\/+$/, ""), publicKey: publicKeyB64 };
}

/** The file the core checks (R4). @param {{deviceId: string, lease: string|null, clock: number, refused: string|null}} s */
function gateDoc(s) {
  return { deviceId: s.deviceId, lease: s.lease || null, clock: Math.floor(s.clock || 0), refused: s.refused || null };
}

module.exports = { ALPHABET, RENEW_MS, normalizeKey, deviceIdFrom, machineIdCommand, parseMachineId, verifyBytes, verifyLease,
  leaseProblem, nextClock, classifyResponse, renewDelayMs, describe, licenseConfig, gateDoc };
