// Every module main.js loads is packed into the app (specs/018: a missing share.js broke the packed app).
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

test("electron-builder packs every local module and page", () => {
  const yml = fs.readFileSync(path.join(__dirname, "..", "electron-builder.yml"), "utf8");
  const main = fs.readFileSync(path.join(__dirname, "..", "main.js"), "utf8");
  const local = [...main.matchAll(/require\("\.\/([\w-]+\.js)"\)/g)].map((m) => m[1]);
  assert.ok(local.length >= 4, local.join(","));
  for (const f of [...local, "preload.js"]) assert.match(yml, new RegExp(`^\\s+- ${f.replace(".", "\\.")}$`, "m"), `${f} is not packed`);
  assert.match(yml, /- "\*\.html"/);
});
