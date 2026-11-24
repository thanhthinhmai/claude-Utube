// Development only (specs/032 T027): run the desktop app's AE bridge from WSL against a core started with
// `sh bin/studio app start --bridge <file>`, driving the real After Effects on Windows through WSL interop.
//   node desktop/test/wsl-bridge.mjs --core http://127.0.0.1:8790 --bridge <file> --work /mnt/e/claude-utube-ae/work
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
const require = createRequire(import.meta.url);
const { Bridge } = require("../aebridge.js");
const arg = (k) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : null; };
const AE = process.env.AE_DIR || "/mnt/c/Program Files/Adobe/Adobe After Effects 2027/Support Files";
const key = JSON.parse(fs.readFileSync(arg("--bridge"), "utf8")).key;
const b = new Bridge({
  base: () => arg("--core"), key, platform: "win32", version: "wsl-dev",
  config: () => ({ afterfx: `${AE}/AfterFX.exe`, aerender: `${AE}/aerender.exe`, work: arg("--work") }),
  found: () => null,
  aePath: (p) => execFileSync("wslpath", ["-w", p]).toString().trim(),
  log: (m) => console.log(new Date().toISOString(), m),
});
console.log("bridge: polling", arg("--core"));
b.start();
