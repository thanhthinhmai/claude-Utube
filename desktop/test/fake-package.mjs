// A tiny fake studio package for the smoke run of the install screen (specs/016 T017):
//   node test/fake-package.mjs <dir>   writes <dir>/core-manifest.json and a small .tar.gz with the right SHA-256
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";

const dir = process.argv[2];
if (!dir) { console.error("usage: node test/fake-package.mjs <dir>"); process.exit(2); }
fs.mkdirSync(dir, { recursive: true });
const file = "claude-utube-core-fake-0.0.1.tar.gz";
const tar = Buffer.alloc(10240);                       // an empty tar archive: two zero blocks and padding
const gz = zlib.gzipSync(tar);
fs.writeFileSync(path.join(dir, file), gz);
const manifest = { version: "0.0.1", os: "fake", file, sha256: crypto.createHash("sha256").update(gz).digest("hex"),
  bytes: gz.length, unpacked_bytes: tar.length, lib_commit: "0".repeat(40), built: new Date().toISOString() };
fs.writeFileSync(path.join(dir, "core-manifest.json"), JSON.stringify(manifest));
console.log(path.join(dir, file));
