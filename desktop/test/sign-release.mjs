// Write release.json and its signature for the files in a folder, with the TEST key (specs/017 T020 smoke runs).
//   node test/sign-release.mjs <dir> <version>
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const [dir, version] = process.argv.slice(2);
if (!dir || !version) { console.error("usage: node test/sign-release.mjs <dir> <version>"); process.exit(2); }
const V = JSON.parse(fs.readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), "vectors", "vectors.json"), "utf8"));
const b64u = (b) => Buffer.from(b).toString("base64url");
const priv = crypto.createPrivateKey({ key: { kty: "OKP", crv: "Ed25519", d: b64u(Buffer.from(V.private_test_only, "base64")),
  x: b64u(Buffer.from(V.public, "base64")) }, format: "jwk" });
const files = fs.readdirSync(dir).filter((n) => /\.(exe|dmg)$/.test(n)).map((name) => {
  const data = fs.readFileSync(path.join(dir, name));
  return { name, size: data.length, sha256: crypto.createHash("sha256").update(data).digest("hex") };
});
const body = Buffer.from(JSON.stringify({ version, tag: `desktop-v${version}`, files }, null, 1));
fs.writeFileSync(path.join(dir, "release.json"), body);
fs.writeFileSync(path.join(dir, "release.json.sig"), b64u(crypto.sign(null, body, priv)) + "\n");
console.log(files.map((f) => f.name).join(", "));
