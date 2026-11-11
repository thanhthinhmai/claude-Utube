// @ts-check
// Updates of the desktop app (specs/017 research R5, R6), with no Electron in it. main.js asks the license server,
// downloads through these functions, and installs (Windows) or opens the .dmg (macOS).
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const { Readable } = require("node:stream");
const { pipeline } = require("node:stream/promises");
const lic = require("./license.js");

const FIRST_CHECK_MS = 30_000;
const EVERY_MS = 4 * 3600_000;

/** "1.2.3" or "1.2.3-test" → parts. @param {string} v */
function parse(v) {
  const m = /^(\d+)\.(\d+)\.(\d+)(?:-([\w.]+))?$/.exec(String(v || "").trim());
  return m ? { n: [Number(m[1]), Number(m[2]), Number(m[3])], pre: m[4] || null } : null;
}

/** Is `a` newer than `b`? A pre-release comes before its release. @param {string} a @param {string} b */
function newer(a, b) {
  const x = parse(a), y = parse(b);
  if (!x || !y) return false;
  for (let i = 0; i < 3; i++) if (x.n[i] !== y.n[i]) return x.n[i] > y.n[i];
  if (x.pre === y.pre) return false;
  if (!x.pre) return true;
  if (!y.pre) return false;
  return x.pre > y.pre;
}

/** release.json with a good signature and the right shape, or null. @param {string} pub @param {Buffer} bytes @param {string} sig */
function verifyRelease(pub, bytes, sig) {
  if (!lic.verifyBytes(pub, bytes, sig)) return null;
  try {
    const r = JSON.parse(bytes.toString("utf8"));
    const ok = parse(r.version) && Array.isArray(r.files) && r.files.every((f) => typeof f.name === "string" && !/[\\/]/.test(f.name)
      && Number.isFinite(f.size) && /^[0-9a-f]{64}$/.test(f.sha256));
    return ok ? r : null;
  } catch {
    return null;
  }
}

/** The installer of this OS in a release. @param {{files: {name: string}[]}} rel @param {string} platform */
function pickAsset(rel, platform) {
  const re = platform === "win32" ? /^claude-Utube-Setup-[\w.-]+\.exe$/ : platform === "darwin" ? /^claude-Utube-[\w.-]+-arm64\.dmg$/ : null;
  return re ? rel.files.find((f) => re.test(f.name)) || null : null;
}

/** SHA-256 of a file. @param {string} file @returns {Promise<string>} */
function sha256File(file) {
  return new Promise((resolve, reject) => {
    const h = crypto.createHash("sha256");
    fs.createReadStream(file).on("error", reject).on("data", (c) => h.update(c)).on("end", () => resolve(h.digest("hex")));
  });
}

/** Download to <file>.part, check size and SHA-256, then rename. A bad file never keeps its final name.
 *  @param {string} url @param {Record<string, string>} headers @param {string} file @param {{size: number, sha256: string}} want
 *  @param {typeof fetch} [fetchImpl] */
async function downloadTo(url, headers, file, want, fetchImpl = fetch) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  if (fs.existsSync(file) && (await sha256File(file)) === want.sha256) return file;    // downloaded before
  const part = file + ".part";
  const r = await fetchImpl(url, { headers, signal: AbortSignal.timeout(2 * 3600_000) });
  if (r.status !== 200 || !r.body) throw new Error(`download failed (${r.status})`);
  const h = crypto.createHash("sha256");
  let size = 0;
  const counter = new (require("node:stream").Transform)({ transform(chunk, _e, done) { h.update(chunk); size += chunk.length; done(null, chunk); } });
  await pipeline(Readable.fromWeb(/** @type {any} */ (r.body)), counter, fs.createWriteStream(part));
  if (size !== want.size || h.digest("hex") !== want.sha256) {
    fs.rmSync(part, { force: true });
    throw new Error("the downloaded file does not match its signed checksum");
  }
  fs.renameSync(part, file);
  return file;
}

/** Remove older installers and leftovers, keeping `keep`. @param {string} dir @param {string} keep */
function cleanDir(dir, keep) {
  for (const f of fs.existsSync(dir) ? fs.readdirSync(dir) : []) {
    if (f !== path.basename(keep)) fs.rmSync(path.join(dir, f), { force: true });
  }
}

/** Windows: the per-user NSIS installer, silent, then starts the app again. @param {string} file */
function installCommand(file) {
  return { file, args: ["/S", "--updated", "--force-run"] };
}

module.exports = { FIRST_CHECK_MS, EVERY_MS, newer, verifyRelease, pickAsset, sha256File, downloadTo, cleanDir, installCommand };
