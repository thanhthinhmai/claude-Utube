// @ts-check
// The desktop shell's logic, with no Electron in it (specs/015 research R1–R5), so `node --test` covers it on any
// machine. main.js does the windows and the tray; this file decides which command to run and what answers mean.
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const MIN_FREE_GB = 5;
const STATUS_EVERY_MS = 10_000;
const READY_TIMEOUT_MS = 60_000;

/** @typedef {{platform: string, distro: string|null, studio: string, data: string, home: string|null,
 *   setupAt?: string, trayNoticeShown?: boolean}} Config */

// ---------- config ----------
/** @param {string} dir @returns {Config|null} */
function loadConfig(dir) {
  try {
    const c = JSON.parse(fs.readFileSync(path.join(dir, "config.json"), "utf8"));
    return c && typeof c === "object" ? c : null;
  } catch {
    return null;
  }
}

/** @param {string} dir @param {Config} cfg */
function saveConfig(dir, cfg) {
  fs.mkdirSync(dir, { recursive: true });
  const tmp = path.join(dir, ".config.json.tmp");
  fs.writeFileSync(tmp, JSON.stringify(cfg, null, 1));
  fs.renameSync(tmp, path.join(dir, "config.json"));
}

/** A config the app can start with; `has` says whether the studio's bin/studio is there (checked by the caller,
 *  which knows how to look inside WSL). @param {Config|null} cfg @param {string} platform @param {boolean} has */
function configUsable(cfg, platform, has) {
  if (!cfg || cfg.platform !== platform || !cfg.studio || !cfg.data) return false;
  if (platform === "win32" && !cfg.distro) return false;
  return has;
}

/** "~/x" with the home of the machine the core runs on. @param {string} p @param {string|null} home */
function expandHome(p, home) {
  if (!p || !home) return p;
  if (p === "~") return home;
  return p.startsWith("~/") ? home.replace(/\/$/, "") + p.slice(1) : p;
}

// ---------- the core's commands (R1) ----------
/** {file, args, env} to run `sh bin/studio app <args…> --data <data>`.
 *  @param {Config} cfg @param {string[]} args @param {Record<string, string|undefined>} env */
function coreCommand(cfg, args, env = process.env) {
  const tail = ["app", ...args, "--data", expandHome(cfg.data, cfg.home)];
  if (env.CU_CORE_CMD) {                       // tests and GitHub Actions: a fake core
    const head = JSON.parse(env.CU_CORE_CMD);
    return { file: head[0], args: [...head.slice(1), ...tail], env: {} };
  }
  if (cfg.platform === "win32") {
    const studio = expandHome(cfg.studio, cfg.home);
    return { file: "wsl.exe", args: ["-d", String(cfg.distro), "--cd", studio, "--", "sh", "bin/studio", ...tail], env: {} };
  }
  const studio = expandHome(cfg.studio, cfg.home);
  const pathVar = ["/opt/homebrew/bin", "/usr/local/bin", env.PATH || "/usr/bin:/bin"].join(":");
  return { file: "/bin/sh", args: [path.join(studio, "bin", "studio"), ...tail], env: { PATH: pathVar } };
}

/** A command inside the core's machine (WSL or this Mac), for setup checks. @param {Config} cfg @param {string} sh */
function shellCommand(cfg, sh) {
  if (cfg.platform === "win32") return { file: "wsl.exe", args: ["-d", String(cfg.distro), "--", "sh", "-c", sh] };
  return { file: "/bin/sh", args: ["-c", sh] };
}

/** @param {string} stdout */
function parseUrl(stdout) {
  const m = /^URL:\s*(http:\/\/127\.0\.0\.1:\d+)\S*\s*$/m.exec(stdout || "");
  return m ? m[1] : null;
}

/** The core's `app status --json`, or a "not running" answer. @param {string} stdout */
function parseStatus(stdout) {
  try {
    const s = JSON.parse(String(stdout || "").trim().split("\n").filter((l) => l.startsWith("{")).pop() || "");
    return { running: !!s.running, url: s.url || null, jobs: Array.isArray(s.jobs) ? s.jobs : [],
      jobs_running: s.jobs_running || 0, logs: s.logs || null, data: s.data || null };
  } catch {
    return { running: false, url: null, jobs: [], jobs_running: 0, logs: null, data: null };
  }
}

// ---------- WSL (R3) ----------
/** `wsl -l -v` prints UTF-16LE (with or without a BOM); NUL bytes show when it is read as UTF-8.
 *  @param {Buffer|string} out @returns {{name: string, version: number, isDefault: boolean, state: string}[]} */
function parseWslList(out) {
  let text = typeof out === "string" ? out : "";
  if (Buffer.isBuffer(out)) {
    const utf16 = out.length > 1 && (out[0] === 0xff && out[1] === 0xfe || out.includes(0));
    text = utf16 ? out.toString("utf16le") : out.toString("utf8");
  }
  text = text.replace(/^﻿/, "").replace(/\0/g, "");
  const rows = [];
  for (const line of text.split(/\r?\n/)) {
    const m = /^\s*(\*)?\s*(\S+)\s+(\S+)\s+(\d+)\s*$/.exec(line);
    if (!m || m[2] === "NAME") continue;
    rows.push({ name: m[2], state: m[3], version: Number(m[4]), isDefault: !!m[1] });
  }
  return rows;
}

/** WSL distros the core can use (WSL2), the default first. @param {Buffer|string} out */
function wsl2Distros(out) {
  return parseWslList(out).filter((d) => d.version === 2 && !/^docker-desktop/.test(d.name))
    .sort((a, b) => Number(b.isDefault) - Number(a.isDefault)).map((d) => d.name);
}

/** Checks from `wsl --status`. @param {Buffer|string} out @param {number|null} code */
function wslStatusChecks(out, code) {
  const text = (Buffer.isBuffer(out) ? out.toString(out.includes(0) ? "utf16le" : "utf8") : String(out || "")).replace(/\0/g, "");
  const low = text.toLowerCase();
  const missing = code !== 0 && code !== null
    || /not installed|is not enabled|wsl --install|has no installed distributions?/.test(low) && !/default version:\s*2/.test(low);
  const virt = /virtualization|virtual machine platform/.test(low) && /(not enabled|disabled|enable)/.test(low);
  const wsl1 = /default version:\s*1/.test(low);
  return [
    { id: "wsl", ok: !missing, detail: missing ? "WSL is not turned on" : "WSL is on",
      fix: missing ? "Press “Turn on WSL”; Windows asks for administrator rights, then restart the computer." : null },
    { id: "virtualization", ok: !virt, detail: virt ? "Virtualization is off" : "Virtualization is on",
      fix: virt ? "Turn on virtualization (Intel VT-x or AMD-V) in the BIOS or UEFI settings, then restart." : null },
    { id: "wsl2", ok: !wsl1, detail: wsl1 ? "WSL uses version 1 by default" : "WSL 2",
      fix: wsl1 ? "Run in PowerShell: wsl --update; wsl --set-default-version 2" : null },
  ];
}

/** Turning WSL on: Windows shows its administrator prompt (constitution 2.2.0; R3). */
function enableWslCommand() {
  return { file: "powershell.exe", args: ["-NoProfile", "-NonInteractive", "-Command",
    "Start-Process wsl -ArgumentList '--install','--no-distribution' -Verb RunAs -Wait"] };
}

/** The setup list from the core's `app check --json` and the free space. @param {any} check @param {number|null} freeGB */
function machineChecks(check, freeGB) {
  const out = [];
  out.push({ id: "tools", ok: !!(check && check.ok), detail: check && check.ok ? "The studio has everything it needs"
    : "Missing: " + ((check && check.missing) || ["the studio did not answer"]).join("; "),
  fix: check && check.ok ? null : "Install what is missing (each line says how), then press Check again." });
  out.push({ id: "space", ok: freeGB !== null && freeGB >= MIN_FREE_GB,
    detail: freeGB === null ? "Free space unknown" : `${freeGB.toFixed(1)} GB free`,
    fix: freeGB !== null && freeGB >= MIN_FREE_GB ? null : `Pick a folder with at least ${MIN_FREE_GB} GB free.` });
  return out;
}

/** GB free from `df -Pk <dir>`. @param {string} stdout */
function parseDf(stdout) {
  const line = String(stdout || "").trim().split("\n").pop() || "";
  const cols = line.split(/\s+/);
  const kb = Number(cols[3]);
  return Number.isFinite(kb) && cols.length >= 4 ? kb / 1024 / 1024 : null;
}

// ---------- window and quit (R5) ----------
/** Only the studio's own pages open in the window. @param {string} url @param {number} port */
function isAppUrl(url, port) {
  try {
    const u = new URL(url);
    return u.protocol === "http:" && u.hostname === "127.0.0.1" && Number(u.port) === Number(port);
  } catch {
    return false;
  }
}

/** What quitting does: ask first when jobs are running, then stop the core (--force only after a yes).
 *  @param {{running: boolean, jobs: {name: string}[], jobs_running: number}} status */
function quitPlan(status) {
  const names = (status.jobs || []).map((j) => j.name);
  const busy = status.running && (status.jobs_running > 0 || names.length > 0);
  return { ask: busy, names, stopArgs: busy ? ["stop", "--force"] : ["stop"], stop: status.running };
}

/** The port in an app URL. @param {string} url */
function portOf(url) {
  try { return Number(new URL(url).port); } catch { return 0; }
}

module.exports = { MIN_FREE_GB, STATUS_EVERY_MS, READY_TIMEOUT_MS, loadConfig, saveConfig, configUsable, expandHome,
  coreCommand, shellCommand, parseUrl, parseStatus, parseWslList, wsl2Distros, wslStatusChecks, enableWslCommand,
  machineChecks, parseDf, isAppUrl, quitPlan, portOf };
