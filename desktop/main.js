// @ts-check
// The desktop app (specs/015): one instance, a splash while the studio core starts, the setup screen the first time,
// the main window on the core's own page, a tray icon, and a safe quit. The core is `sh bin/studio app …` (specs/014):
// on macOS on this machine, on Windows inside WSL2. All decisions live in core.js; this file does the windows.
"use strict";

const { app, BrowserWindow, Tray, Menu, dialog, shell, ipcMain, Notification, nativeImage, safeStorage, session } = require("electron");
const { execFile, spawn } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const core = require("./core.js");
const lic = require("./license.js");
const upd = require("./updates.js");
const share = require("./share.js");

const SMOKE = process.argv.includes("--smoke");
const LICENSE_SMOKE = process.argv.includes("--smoke-license");
const UPDATE_SMOKE = process.argv.includes("--smoke-update");
const CLIENT_SMOKE = process.argv.includes("--smoke-client");
const isClient = () => !!(cfg && /** @type {any} */ (cfg).mode === "client");
const SECOND = process.argv.includes("--smoke-second");
if (process.env.CU_CONFIG_DIR) app.setPath("userData", process.env.CU_CONFIG_DIR);   // tests: own config and own lock
const CONFIG_DIR = app.getPath("userData");
const PLATFORM = process.env.CU_PLATFORM || process.platform;
const ASSETS = path.join(__dirname, "assets");

/** @type {core.Config|null} */ let cfg = null;
/** @type {BrowserWindow|null} */ let win = null;
/** @type {BrowserWindow|null} */ let splash = null;
/** @type {BrowserWindow|null} */ let setupWin = null;
/** @type {Tray|null} */ let tray = null;
let appUrl = "";
let quitting = false;
let monitor = /** @type {NodeJS.Timeout|null} */ (null);

const smoke = (/** @type {string} */ line) => { if (SMOKE) console.log(`smoke: ${line}`); };
const smokeFail = (/** @type {string} */ why) => { console.log(`smoke: fail ${why}`); app.exit(1); };

// ---------- running commands ----------
/** @param {{file: string, args: string[], env?: Record<string, string>}} cmd @param {number} timeout
 *  @returns {Promise<{code: number|null, stdout: Buffer, stderr: Buffer}>} */
function run(cmd, timeout = 30_000) {
  return new Promise((resolve) => {
    execFile(cmd.file, cmd.args, { env: { ...process.env, ...(cmd.env || {}) }, timeout, windowsHide: true,
      encoding: "buffer", maxBuffer: 8 * 1024 * 1024 }, (err, stdout, stderr) => {
      const code = err ? (typeof err.code === "number" ? err.code : 1) : 0;
      resolve({ code, stdout: /** @type {Buffer} */ (stdout), stderr: /** @type {Buffer} */ (stderr) });
    });
  });
}

/** @param {string[]} args @param {number} [timeout] */
async function coreRun(args, timeout) {
  if (!cfg) throw new Error("no config");
  const r = await run(core.coreCommand(cfg, args), timeout);
  return { code: r.code, out: r.stdout.toString("utf8"), err: r.stderr.toString("utf8") };
}

async function coreStatus() {
  const r = await coreRun(["status", "--json"], 20_000).catch(() => ({ code: 1, out: "", err: "" }));
  return core.parseStatus(r.out);
}

/** Is the studio there (bin/studio)? On Windows it lives inside WSL. @param {core.Config|null} c */
async function studioThere(c) {
  if (!c) return false;
  if (process.env.CU_CORE_CMD) return true;
  if (c.platform === "win32") {
    const r = await run(core.shellCommand(c, `test -f "${core.expandHome(c.studio, c.home)}/bin/studio"`), 20_000);
    return r.code === 0;
  }
  return fs.existsSync(path.join(core.expandHome(c.studio, c.home), "bin", "studio"));
}

// ---------- folders ----------
/** A folder of the core's machine as Windows or macOS sees it. @param {string|null} p */
function hostPath(p) {
  if (!p || !cfg) return null;
  if (cfg.platform === "win32" && !process.env.CU_CORE_CMD) return `\\\\wsl.localhost\\${cfg.distro}${p.replace(/\//g, "\\")}`;
  return p;
}

async function openFolder(/** @type {"data"|"logs"} */ which) {
  const s = await coreStatus();
  const p = hostPath(which === "logs" ? (s.logs || null) : (s.data || (cfg && core.expandHome(cfg.data, cfg.home))));
  if (p) shell.openPath(p);
}

// ---------- splash, start ----------
function showSplash() {
  splash = new BrowserWindow({ width: 460, height: 300, frame: false, resizable: false, show: false, icon: path.join(ASSETS, "icon.png"),
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true } });
  splash.loadFile(path.join(__dirname, "splash.html"));
  splash.once("ready-to-show", () => splash && !SMOKE && splash.show());
}

/** @param {string} text */
function step(text) {
  if (splash && !splash.isDestroyed()) splash.webContents.executeJavaScript(`setStep(${JSON.stringify(text)})`).catch(() => {});
}

async function startCore() {
  if (!splash || splash.isDestroyed()) showSplash();
  await new Promise((r) => splash && splash.webContents.once("did-finish-load", r));
  step("Starting the studio…");
  const r = await coreRun(["start", ...gateArgs()], core.READY_TIMEOUT_MS + 5_000).catch((e) => ({ code: 1, out: "", err: String(e) }));
  const url = core.parseUrl(r.out);
  if (r.code !== 0 || !url) {
    const why = (r.out + "\n" + r.err).trim().split("\n").slice(-20).join("\n");
    if (SMOKE) return smokeFail(`core did not start: ${why}`);
    splash && splash.webContents.executeJavaScript(`showError(${JSON.stringify(why || "The studio did not answer in time.")})`);
    return;
  }
  step("Opening…");
  appUrl = url;
  openMain(url);
  if (cfg && /** @type {any} */ (cfg).share && /** @type {any} */ (cfg).share.enabled) startSharing();   // specs/018
}

// ---------- the main window ----------
/** The studio's own pages: the local core (Host) or the paired Host (Client). @param {string} u */
function isOwnUrl(u) {
  if (isClient()) {
    try { return new URL(u).protocol === "https:" && new URL(u).host === new URL(appUrl).host; } catch { return false; }
  }
  return core.isAppUrl(u, core.portOf(appUrl));
}

/** @param {string} url */
function openMain(url) {
  const port = core.portOf(url);
  if (!win || win.isDestroyed()) {
    win = new BrowserWindow({ width: 1400, height: 900, minWidth: 960, minHeight: 600, show: false, title: "claude-Utube",
      icon: path.join(ASSETS, "icon.png"), autoHideMenuBar: true,
      webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true, preload: path.join(__dirname, "preload.js") } });
    win.webContents.setWindowOpenHandler(({ url: u }) => {
      if (!isOwnUrl(u)) openOutside(u);
      return { action: "deny" };
    });
    win.webContents.on("will-navigate", (e, u) => {
      if (!isOwnUrl(u) && !u.startsWith("file:")) {
        e.preventDefault();
        openOutside(u);
      }
    });
    win.on("close", (e) => {                        // closing hides it: films keep running (FR-012)
      if (quitting) return;
      e.preventDefault();
      win && win.hide();
      trayNotice();
    });
  }
  win.loadURL(url);
  win.once("ready-to-show", () => {
    if (!SMOKE) win && win.show();
    if (splash && !splash.isDestroyed()) splash.destroy();
    splash = null;
  });
  buildTray();
  watchCore();
  if (SMOKE) win.webContents.once("did-finish-load", () => (CLIENT_SMOKE ? smokeClient() : UPDATE_SMOKE ? smokeUpdate() : LICENSE_SMOKE ? smokeLicense() : smokeMain(port)));
}

/** @param {string} u */
function openOutside(u) {
  if (SMOKE) { smoke(`external ok ${u}`); return; }
  if (/^https?:\/\//.test(u)) shell.openExternal(u);
}

function trayNotice() {
  if (!cfg || cfg.trayNoticeShown) return;
  cfg.trayNoticeShown = true;
  core.saveConfig(CONFIG_DIR, cfg);
  const body = "The studio keeps running in the tray, so films are not interrupted. Use Quit in the tray menu to stop it.";
  if (Notification.isSupported() && !SMOKE) new Notification({ title: "claude-Utube is still running", body }).show();
}

function showMain() {
  if (win && !win.isDestroyed()) { win.show(); win.focus(); }
}

function watchCore() {
  if (monitor) clearInterval(monitor);
  monitor = setInterval(checkCore, core.STATUS_EVERY_MS);
}

async function checkCore() {
  if (quitting || !win || win.isDestroyed()) return;
  if (isClient()) return checkHost();
  const s = await coreStatus();
  if (!s.running && !win.webContents.getURL().startsWith("file:")) {
    win.loadFile(path.join(__dirname, "stopped.html"));      // FR-014
    if (SMOKE) win.webContents.once("did-finish-load", () => { smoke("stopped ok"); smokeAfterStopped(); });
  }
}

// ---------- tray ----------
function buildTray() {
  if (tray) return;
  const file = PLATFORM === "darwin" ? "trayTemplate.png" : "tray.png";
  const img = nativeImage.createFromPath(path.join(ASSETS, file));
  if (PLATFORM === "darwin") img.setTemplateImage(true);
  tray = new Tray(img);
  tray.setToolTip("claude-Utube");
  setTrayMenu();
  tray.on("click", showMain);
}

function setTrayMenu() {
  if (!tray) return;
  const pending = pendingUpdate();
  tray.setContextMenu(Menu.buildFromTemplate([
    ...(pending && PLATFORM === "win32" ? [{ label: `Restart to update (${pending.version})`, click: () => app.quit() },
      { type: /** @type {const} */ ("separator") }] : []),
    { label: "Open the studio", click: showMain },
    ...(isClient() ? [] : [
      { label: "Open in the browser", click: () => appUrl && shell.openExternal(appUrl) },
      { label: "Share with my team…", click: showShare },
      { type: /** @type {const} */ ("separator") },
      { label: "Data folder", click: () => openFolder("data") },
      { label: "Log folder", click: () => openFolder("logs") }]),
    { label: "Change setup…", click: changeSetup },
    ...(LIC && !isClient() ? [{ label: "License…", click: () => showLicense("info") }] : []),
    ...(LIC ? [{ label: "Check for updates", click: () => checkUpdates(true) }] : []),
    { type: "separator" },
    { label: "Quit", click: () => app.quit() },
  ]));
}

// ---------- quitting (FR-013) ----------
/** Ask when jobs run; returns false when the person keeps the studio. */
async function stopCore(/** @type {string} */ verb) {
  const s = await coreStatus();
  const plan = core.quitPlan(s);
  if (plan.ask) {
    const answer = SMOKE ? (process.env.CU_SMOKE_ANSWER === "cancel" ? 0 : 1) : (await dialog.showMessageBox({
      type: "warning", buttons: ["Cancel", verb], defaultId: 0, cancelId: 0, title: "Films are being made",
      message: "These jobs are still running:", detail: plan.names.map((n) => `• ${n}`).join("\n")
        + `\n\n${verb} stops them; the credits they used are not given back.` })).response;
    if (answer !== 1) return false;
  }
  if (plan.stop) await coreRun(plan.stopArgs, 30_000);
  return true;
}

app.on("before-quit", async (e) => {
  if (quitting) return;
  e.preventDefault();
  if (!cfg) { quitting = true; app.exit(0); return; }
  const ok = isClient() ? true : await stopCore("Quit");
  if (!ok) { if (SMOKE) smoke("quit cancel ok"); return; }
  quitting = true;
  if (monitor) clearInterval(monitor);
  if (gateway) await gateway.stop().catch(() => {});
  const pending = PLATFORM === "win32" ? pendingUpdate() : null;
  if (pending) {                           // the per-user installer replaces the app, then starts it again (R6)
    const cmd = upd.installCommand(pending.file);
    spawn(cmd.file, cmd.args, { detached: true, stdio: "ignore", windowsHide: true }).on("error", () => {}).unref();
    saveLicState({ pendingUpdate: null });
    smoke("installer started");
  }
  smoke("quit ok");
  app.exit(0);
});

// ---------- license (specs/017) ----------
const LIC = lic.licenseConfig(readJson(path.join(__dirname, "build-config.json")), process.env, app.isPackaged,
  readText(path.join(__dirname, "license-public-key.txt")));
const GATE = path.join(CONFIG_DIR, "gate.json");
const KEY_FILE = path.join(CONFIG_DIR, "license.key");
const KEYCHAIN = "claude-Utube license";
let deviceId = "";
let locked = false;
let licenseWin = /** @type {BrowserWindow|null} */ (null);
let renewTimer = /** @type {NodeJS.Timeout|null} */ (null);

/** @param {string} f */
function readJson(f) { try { return JSON.parse(fs.readFileSync(f, "utf8")); } catch { return null; } }
/** @param {string} f */
function readText(f) { try { return fs.readFileSync(f, "utf8"); } catch { return ""; } }
const nowS = () => Math.floor(Date.now() / 1000);

async function machineDeviceId() {
  const cmd = lic.machineIdCommand(process.platform);
  let raw = null;
  if (cmd) raw = lic.parseMachineId(process.platform, (await run(cmd, 10_000)).stdout.toString("utf8"));
  else raw = lic.parseMachineId("linux", readText("/etc/machine-id"));
  if (!raw) {                                              // no id from the OS: one random id kept in the config
    const c = core.loadConfig(CONFIG_DIR) || /** @type {any} */ ({});
    if (!c.installId) { c.installId = require("node:crypto").randomUUID(); core.saveConfig(CONFIG_DIR, c); }
    raw = c.installId;
  }
  return lic.deviceIdFrom(String(raw));
}

// The key: Windows encrypts it for this user (DPAPI); macOS keeps it in the Keychain; a dev build uses a plain file.
async function readKey() {
  if (app.isPackaged && process.platform === "darwin") {
    const r = await run({ file: "/usr/bin/security", args: ["find-generic-password", "-s", KEYCHAIN, "-a", "key", "-w"] }, 10_000);
    return r.code === 0 ? r.stdout.toString("utf8").trim() : "";
  }
  const raw = readText(KEY_FILE).trim();
  if (!raw) return "";
  if (app.isPackaged && safeStorage.isEncryptionAvailable()) {
    try { return safeStorage.decryptString(Buffer.from(raw, "base64")); } catch { return ""; }
  }
  return raw;
}

/** @param {string} key */
async function saveKey(key) {
  if (app.isPackaged && process.platform === "darwin") {
    await run({ file: "/usr/bin/security", args: ["add-generic-password", "-U", "-s", KEYCHAIN, "-a", "key", "-w", key] }, 10_000);
    return;
  }
  fs.mkdirSync(CONFIG_DIR, { recursive: true });
  const body = app.isPackaged && safeStorage.isEncryptionAvailable() ? safeStorage.encryptString(key).toString("base64") : key;
  fs.writeFileSync(KEY_FILE, body, { mode: 0o600 });
}

function licState() {
  const c = /** @type {any} */ (core.loadConfig(CONFIG_DIR) || {});
  return { lease: c.lease || null, clock: c.licenseClock || 0, refused: c.licenseRefused || null, label: c.licenseLabel || null,
    expires: c.licenseExpires || null };
}

/** @param {any} patch */
function saveLicState(patch) {
  const c = /** @type {any} */ (core.loadConfig(CONFIG_DIR) || cfg || { platform: PLATFORM });
  Object.assign(c, patch);
  core.saveConfig(CONFIG_DIR, c);
  if (cfg) Object.assign(cfg, patch);
  const st = licState();
  const tmp = GATE + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(lic.gateDoc({ deviceId, lease: st.lease, clock: st.clock, refused: st.refused && st.refused.code })));
  fs.renameSync(tmp, GATE);
}

function gateArgs() {
  if (!LIC) return [];
  const p = cfg && cfg.platform === "win32" && !process.env.CU_CORE_CMD ? core.wslPath(GATE) : GATE;
  return ["--gate", p];
}

/** Why the license cannot be used now, or null. Moves the seen clock forward. */
function licenseProblem() {
  const st = licState();
  if (st.refused) return st.refused.code;
  const t = nowS();
  const p = lic.verifyLease(LIC ? LIC.publicKey : "", st.lease);
  const why = lic.leaseProblem(p, deviceId, t, st.clock);
  if (!why && t > st.clock) saveLicState({ licenseClock: t });
  return why;
}

/** Ask the server for a lease. Returns "ok", "refused" (code saved) or "offline". @param {string} key */
async function renew(key) {
  if (!LIC || !key) return "offline";
  let status = 0, body = null;
  try {
    const r = await fetch(`${LIC.server}/api/license/lease`, { method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ key, deviceId, deviceName: os.hostname(), os: `${process.platform} ${os.release()}`, version: app.getVersion() }),
      signal: AbortSignal.timeout(20_000) });
    status = r.status;
    body = await r.json().catch(() => null);
  } catch { /* offline */ }
  const kind = lic.classifyResponse(status, body);
  if (kind === "ok") {
    const p = lic.verifyLease(LIC.publicKey, body.lease);
    if (!p || p.did !== deviceId) return "offline";
    saveLicState({ lease: body.lease, licenseClock: lic.nextClock(licState().clock, nowS(), body.serverTime),
      licenseRefused: null, licenseLabel: body.label || null, licenseExpires: body.expiresAt || null });
  } else if (kind === "refused") {
    saveLicState({ lease: null, licenseRefused: { code: body.code, at: nowS() } });
  } else if (status === 429) {
    return "rate_limited";
  }
  return kind;
}

function scheduleRenew() {
  if (!LIC) return;
  if (renewTimer) clearTimeout(renewTimer);
  const ms = Number(!app.isPackaged && process.env.CU_LICENSE_RENEW_MS) || lic.renewDelayMs(Math.random());
  renewTimer = setTimeout(async () => {
    await renew(await readKey());
    if (licenseProblem()) lock();
    scheduleRenew();
  }, ms);
}

/** Hide the studio, keep running jobs going (the core's gate stops new ones), ask for a key (FR-008). */
function lock() {
  if (locked) return;
  locked = true;
  saveLicState({});
  if (win && !win.isDestroyed()) win.hide();
  if (tray) tray.setToolTip("claude-Utube (locked)");
  showLicense("locked");
  smoke("locked ok");
}

/** @param {"needed"|"locked"|"info"} mode */
function showLicense(mode) {
  if (licenseWin && !licenseWin.isDestroyed()) {
    licenseWin.webContents.send("license:mode", mode);
    licenseWin.show();
    return;
  }
  licenseWin = new BrowserWindow({ width: 520, height: 520, title: "claude-Utube license", icon: path.join(ASSETS, "icon.png"),
    show: !SMOKE, autoHideMenuBar: true, resizable: false,
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true } });
  licenseWin.loadFile(path.join(__dirname, "license.html"), { query: { mode } });
  licenseWin.on("closed", () => {
    licenseWin = null;
    if ((mode === "needed" || locked) && !quitting && licenseProblem()) app.quit();   // no license: nothing to show
  });
  if (SMOKE && mode === "needed") licenseWin.webContents.once("did-finish-load", () => submitKey(process.env.CU_SMOKE_KEY || ""));
}

ipcMain.handle("license:state", async () => {
  const st = licState();
  const why = licenseProblem();
  return { label: st.label, expires: st.expires, problem: why, message: why ? lic.describe(why) : null, locked };
});
ipcMain.handle("license:submit", async (_e, key) => submitKey(key));

/** @param {string} typed */
async function submitKey(typed) {
  const key = lic.normalizeKey(typed);
  if (!key) return { ok: false, error: lic.describe("unknown") };
  const kind = await renew(key);
  if (kind !== "ok") return { ok: false, error: lic.describe(kind === "refused" ? licState().refused.code : kind) };
  await saveKey(key);
  smoke("license ok");
  const wasLocked = locked;
  locked = false;
  if (tray) tray.setToolTip("claude-Utube");
  if (licenseWin && !licenseWin.isDestroyed()) { const w = licenseWin; licenseWin = null; w.destroy(); }
  scheduleRenew();
  if (wasLocked && win && !win.isDestroyed()) { win.loadURL(appUrl); showMain(); }
  else if (!win) afterLicense();
  return { ok: true };
}

/** A Host needs a good license before its core starts (017). False: the license window is shown. */
async function ensureLicense() {
  if (!LIC || isClient()) return true;
  if (!deviceId) deviceId = await machineDeviceId();
  const key = await readKey();
  if (key) await renew(key);
  if (licenseProblem()) { showLicense("needed"); return false; }
  scheduleRenew();
  return true;
}

/** Licensed: go on with setup or start the core. */
async function afterLicense() {
  const m = cfg && cfg.coreKind === "packaged" ? core.readManifest(PACKAGED_DIR) : null;
  if (m && cfg && cfg.coreVersion !== m.version) return showSetup();      // a new app brought a new core (016 R7)
  if (core.configUsable(cfg, PLATFORM, await studioThere(cfg))) startCore();
  else showSetup();
}

// ---------- updates (specs/017 US3) ----------
const UPDATES = path.join(CONFIG_DIR, "updates");
let checking = false;

/** A downloaded, checked installer newer than this app, or null. */
function pendingUpdate() {
  const p = /** @type {any} */ (core.loadConfig(CONFIG_DIR) || {}).pendingUpdate;
  return p && p.file && fs.existsSync(p.file) && upd.newer(p.version, app.getVersion()) ? p : null;
}

/** @param {boolean} manual */
/** Where updates come from: the license server (Host) or the paired Host (Client, specs/018 R5). */
function updateSource() {
  if (!LIC) return null;
  if (isClient()) {
    const h = /** @type {any} */ (cfg).host;
    return h ? { base: `https://${h.address}/__cu/update`, headers: { "x-cu-client": share.clientHeader(h) }, fetch: share.pinnedFetch(h.fingerprint) } : null;
  }
  const lease = licState().lease;
  return lease && !locked ? { base: `${LIC.server}/api/license/releases`, headers: { "x-cu-lease": lease }, fetch } : null;
}

async function checkUpdates(manual) {
  const src = updateSource();
  if (!LIC || !src || checking) return;
  checking = true;
  const say = (/** @type {string} */ m) => { if (manual && !SMOKE) dialog.showMessageBox({ type: "info", message: m }); };
  try {
    const h = src.headers;
    const get = (/** @type {string} */ name) => src.fetch(`${src.base}/${encodeURIComponent(name)}`,
      { headers: h, signal: AbortSignal.timeout(60_000) }).then(async (r) => { if (r.status !== 200) throw new Error(`answer ${r.status}`); return Buffer.from(await r.arrayBuffer()); });
    const list = await src.fetch(src.base, { headers: h, signal: AbortSignal.timeout(30_000) });
    if (list.status !== 200) { say("No update could be found right now."); return; }
    const info = await list.json();
    if (!upd.newer(info.version, app.getVersion())) { say(`claude-Utube ${app.getVersion()} is the newest version.`); return; }
    const rel = upd.verifyRelease(LIC.publicKey, await get("release.json"), (await get("release.json.sig")).toString("utf8"));
    if (!rel || !upd.newer(rel.version, app.getVersion())) throw new Error("the release list is not signed by the studio owner");
    const asset = upd.pickAsset(rel, PLATFORM);
    if (!asset) return;
    const file = await upd.downloadTo(`${src.base}/${encodeURIComponent(asset.name)}`, h,
      path.join(UPDATES, asset.name), asset, src.fetch);
    upd.cleanDir(UPDATES, file);
    saveLicState({ pendingUpdate: { version: rel.version, file } });
    setTrayMenu();
    smoke("update ready ok");
    if (SMOKE) return;
    if (PLATFORM === "win32") {
      if (Notification.isSupported()) new Notification({ title: `claude-Utube ${rel.version} is ready`,
        body: "It is installed when you quit the app, or choose Restart to update in the tray menu." }).show();
    } else if (PLATFORM === "darwin") {
      const r = await dialog.showMessageBox({ type: "info", buttons: ["Later", "Open"], defaultId: 1, cancelId: 0,
        message: `claude-Utube ${rel.version} is ready`, detail: "Open it, then drag claude-Utube into Applications to replace this version." });
      if (r.response === 1) shell.openPath(file);
    }
  } catch (e) {
    if (SMOKE) smoke(`fail update: ${e}`);
    say(`The update could not be downloaded: ${e && /** @type {any} */ (e).message || e}`);
  } finally {
    checking = false;
  }
}

function scheduleUpdates() {
  if (!LIC) return;
  const every = Number(!app.isPackaged && process.env.CU_UPDATE_EVERY_MS) || upd.EVERY_MS;
  setTimeout(() => { checkUpdates(false); setInterval(() => checkUpdates(false), every); }, SMOKE ? 600_000 : upd.FIRST_CHECK_MS);
}

// ---------- sharing with the team (specs/018, Host) ----------
let gateway = /** @type {{port: number, stop: () => Promise<void>, fingerprint: string}|null} */ (null);
const pairing = new share.Pairing();
let shareError = /** @type {string|null} */ (null);
let shareWin = /** @type {BrowserWindow|null} */ (null);

function shareState() {
  const c = /** @type {any} */ (cfg);
  if (!c.share) c.share = { enabled: false, port: share.DEFAULT_PORT, hostId: require("node:crypto").randomUUID(), clients: [] };
  return c.share;
}
function saveShare() { if (cfg) core.saveConfig(CONFIG_DIR, cfg); pushShare(); }
function pushShare() { if (shareWin && !shareWin.isDestroyed()) shareWin.webContents.send("share:changed"); }

/** The gateway's certificate, made once by the core (`app cert`) and kept here. */
async function shareCert() {
  const f = path.join(CONFIG_DIR, "share-cert.json");
  const have = readJson(f);
  if (have && have.cert && have.key) return have;
  const r = await coreRun(["cert"], 60_000);
  const c = JSON.parse(r.out.trim().split("\n").filter((l) => l.startsWith("{")).pop() || "null");
  if (!c || !c.cert) throw new Error("the studio did not make a certificate: " + (r.err || r.out).slice(-300));
  fs.writeFileSync(f, JSON.stringify(c), { mode: 0o600 });
  return c;
}

async function startSharing() {
  if (gateway || isClient()) return;
  const st = shareState();
  try {
    const c = await shareCert();
    gateway = await share.startGateway({ cert: c.cert, key: c.key, port: st.port, corePort: () => core.portOf(appUrl), state: st,
      pairing, onChange: saveShare,
      update: () => (LIC && licState().lease && !locked ? { server: LIC.server, lease: licState().lease } : null) });
    shareError = null;
    smoke(`share ok ${gateway.port}`);
  } catch (e) {
    shareError = /** @type {any} */ (e).code === "EADDRINUSE" ? `Port ${st.port} is busy on this computer.` : String(/** @type {any} */ (e).message || e);
    st.enabled = false;
  }
  saveShare();
}

async function stopSharing() {
  pairing.close();
  if (gateway) { await gateway.stop().catch(() => {}); gateway = null; }
  saveShare();
}

function showShare() {
  if (shareWin && !shareWin.isDestroyed()) { shareWin.show(); return; }
  shareWin = new BrowserWindow({ width: 620, height: 640, title: "Share with my team", icon: path.join(ASSETS, "icon.png"),
    autoHideMenuBar: true, show: !SMOKE, webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true } });
  shareWin.loadFile(path.join(__dirname, "share.html"));
  shareWin.on("closed", () => { shareWin = null; });
}

ipcMain.handle("share:state", () => {
  const st = shareState();
  return { enabled: !!gateway, port: st.port, error: shareError, fingerprint: gateway ? gateway.fingerprint : null,
    addresses: gateway ? share.addresses(os.networkInterfaces(), gateway.port) : [],
    pairing: pairing.active() && pairing.cur ? { code: pairing.cur.code, until: pairing.cur.until } : null,
    clients: st.clients.filter((/** @type {any} */ c) => !c.forgotten).map((/** @type {any} */ c) => ({ id: c.id, name: c.name,
      firstSeen: c.firstSeen, lastSeen: c.lastSeen, removed: !!c.removed })) };
});
ipcMain.handle("share:toggle", async (_e, on) => {
  shareState().enabled = !!on;
  if (on) await startSharing(); else await stopSharing();
  return { ok: !!gateway === !!on, error: shareError };
});
ipcMain.handle("share:add", () => { if (!gateway) return null; const p = pairing.open(); pushShare(); return p; });
ipcMain.handle("share:remove", (_e, id) => {
  const st = shareState();
  const c = st.clients.find((/** @type {any} */ x) => x.id === id);
  if (c && c.removed) st.clients = st.clients.filter((/** @type {any} */ x) => x.id !== id);
  else if (c) c.removed = nowS();
  saveShare();
  return true;
});

// ---------- Client mode (specs/018) ----------
function pinHost() {
  const h = /** @type {any} */ (cfg).host;
  const target = share.parseAddress(h.address);
  if (!target) return;
  session.defaultSession.setCertificateVerifyProc((req, cb) => {
    if (req.hostname !== target.host) return cb(-3);                       // other sites: Chromium's own checks
    let fp = "";
    try { fp = share.fingerprintOf(req.certificate.data); } catch { /* refused below */ }
    cb(fp === h.fingerprint ? 0 : -2);
  });
  session.defaultSession.webRequest.onBeforeSendHeaders({ urls: [`https://${h.address}/*`] }, (d, cb) => {
    d.requestHeaders["X-CU-Client"] = share.clientHeader(h);
    cb({ requestHeaders: d.requestHeaders });
  });
}

function startClient() {
  const h = /** @type {any} */ (cfg).host;
  pinHost();
  appUrl = `https://${h.address}/`;
  if (splash && !splash.isDestroyed()) splash.destroy();
  splash = null;
  openMain(appUrl);
  if (win) win.webContents.on("did-fail-load", (_e, code, _d, url, isMain) => { if (isMain && code !== -3) showOffline(); });
}

let offlineShown = false;
async function showOffline() {
  if (!win || win.isDestroyed()) return;
  const why = await share.probeHost(/** @type {any} */ (cfg).host);
  if (why === "ok" && !win.webContents.getURL().startsWith("file:")) return;
  offlineShown = true;
  win.loadFile(path.join(__dirname, "offline.html"), { query: { why, address: /** @type {any} */ (cfg).host.address } });
  if (SMOKE) win.webContents.once("did-finish-load", () => smoke("offline ok"));
}

async function checkHost() {
  if (!win || win.isDestroyed()) return;
  const onPage = !win.webContents.getURL().startsWith("file:");
  const why = await share.probeHost(/** @type {any} */ (cfg).host);
  if (why !== "ok" && onPage) showOffline();
  if (why === "ok" && !onPage && offlineShown) { offlineShown = false; win.loadURL(appUrl); }
}

ipcMain.handle("client:setup", () => { changeSetup(); return true; });
ipcMain.handle("client:retry", async () => { if (win && !win.isDestroyed()) win.loadURL(appUrl); return true; });

/** Pair from the setup screen and save the Client config. @param {{address: string, code: string, name: string}} d */
async function pairClient(d) {
  try {
    const h = await share.pairWithHost(d.address, d.code, d.name || os.hostname());
    const old = /** @type {any} */ (core.loadConfig(CONFIG_DIR) || {});
    const c = /** @type {any} */ ({ platform: PLATFORM, mode: "client", host: h, distro: null, studio: "", data: "", home: null,
      setupAt: new Date().toISOString(), trayNoticeShown: !!old.trayNoticeShown });
    for (const k of ["installId", "pendingUpdate", "share"]) if (old[k] !== undefined) c[k] = old[k];   // a former Host keeps its sharing list
    cfg = c;
    core.saveConfig(CONFIG_DIR, c);
    smoke("pair ok");
    if (setupWin && !setupWin.isDestroyed()) setupWin.destroy();
    setupWin = null;
    startClient();
    scheduleUpdates();
    return { ok: true };
  } catch (e) {
    return { ok: false, error: share.describe(String(/** @type {any} */ (e).message || e)) };
  }
}
ipcMain.handle("setup:pair", (_e, d) => pairClient(d));
ipcMain.handle("setup:hostname", () => os.hostname());

// ---------- setup (US2) ----------
function showSetup() {
  setupWin = new BrowserWindow({ width: 760, height: 720, title: "Set up claude-Utube", icon: path.join(ASSETS, "icon.png"),
    show: !SMOKE, autoHideMenuBar: true,
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true } });
  setupWin.loadFile(path.join(__dirname, "setup.html"));
  if (SMOKE) setupWin.webContents.once("did-finish-load", smokeSetup);
}

async function changeSetup() {
  if (!isClient() && !(await stopCore("Stop the studio"))) return;
  if (gateway) { await gateway.stop().catch(() => {}); gateway = null; }
  if (win && !win.isDestroyed()) { quitting = true; win.destroy(); quitting = false; win = null; }
  if (monitor) clearInterval(monitor);
  showSetup();
}

async function wslChecks() {
  const st = await run({ file: "wsl.exe", args: ["--status"] }, 20_000).catch(() => ({ code: 1, stdout: Buffer.from(""), stderr: Buffer.from("") }));
  const list = await run({ file: "wsl.exe", args: ["-l", "-v"] }, 20_000).catch(() => ({ code: 1, stdout: Buffer.from(""), stderr: Buffer.from("") }));
  return { checks: core.wslStatusChecks(Buffer.concat([st.stdout, st.stderr]), st.code), distros: core.wsl2Distros(list.stdout) };
}

ipcMain.handle("setup:check", async (_e, draft) => {
  const out = { platform: PLATFORM, checks: /** @type {any[]} */ ([]), distros: /** @type {string[]} */ ([]),
    defaults: { studio: "~/claude-Utube", data: PLATFORM === "darwin" ? "~/Library/Application Support/ClaudeUtube" : "~/.local/share/claude-utube" } };
  if (PLATFORM === "win32" && !process.env.CU_CORE_CMD) {
    const w = await wslChecks();
    out.checks.push(...w.checks);
    out.distros = w.distros;
    if (!w.distros.length) out.checks.push({ id: "distro", ok: false, detail: "No WSL 2 Linux found",
      fix: "Install a Linux with the studio first (see the studio's README), then press Check again." });
  }
  const c = { platform: PLATFORM, distro: draft && draft.distro || out.distros[0] || null, studio: draft && draft.studio || out.defaults.studio,
    data: draft && draft.data || out.defaults.data, home: draft && draft.home || (PLATFORM === "darwin" ? os.homedir() : null) };
  if (PLATFORM !== "win32" || c.distro || process.env.CU_CORE_CMD) {
    if (PLATFORM === "win32" && !c.home && !process.env.CU_CORE_CMD) c.home = await wslHome(c.distro);
    const there = await studioThere(c);
    out.checks.push({ id: "studio", ok: there, detail: there ? `Studio found at ${c.studio}` : `No studio at ${c.studio}`,
      fix: there ? null : "Type the folder of the studio (it holds bin/studio)." });
    if (there) {
      const r = await run(core.coreCommand(c, ["check", "--json"]), 60_000);
      let check = null;
      try { check = JSON.parse(r.stdout.toString("utf8").trim().split("\n").pop() || ""); } catch { /* shown as missing */ }
      const df = await run(core.shellCommand(c, `mkdir -p "${core.expandHome(c.data, c.home)}" && df -Pk "${core.expandHome(c.data, c.home)}"`), 20_000);
      out.checks.push(...core.machineChecks(check, core.parseDf(df.stdout.toString("utf8"))));
    }
  }
  return { ...out, draft: c };
});

/** @param {string|null} distro */
async function wslHome(distro) {
  if (!distro) return null;
  const r = await run({ file: "wsl.exe", args: ["-d", distro, "--", "sh", "-c", "echo $HOME"] }, 20_000);
  return r.stdout.toString("utf8").replace(/\0/g, "").trim() || null;
}

ipcMain.handle("setup:enableWsl", async () => {
  const yes = await dialog.showMessageBox({ type: "question", buttons: ["Cancel", "Turn on WSL"], defaultId: 1, cancelId: 0,
    title: "Turn on WSL", message: "Windows will turn on WSL 2 and the Virtual Machine Platform.",
    detail: "Windows asks for administrator rights. When it is done, restart the computer and open claude-Utube again." });
  if (yes.response !== 1) return { ok: false, cancelled: true, rebootNeeded: false };
  const r = await run(core.enableWslCommand(), 30 * 60_000);
  return r.code === 0 ? { ok: true, cancelled: false, rebootNeeded: true } : { ok: false, cancelled: true, rebootNeeded: false };
});

ipcMain.handle("setup:finish", async (_e, draft) => finishSetup(draft));

/** @param {any} draft */
async function finishSetup(draft) {
  const c = { platform: PLATFORM, distro: draft.distro || null, studio: draft.studio, data: draft.data, home: draft.home || null,
    setupAt: new Date().toISOString(), trayNoticeShown: !!(cfg && cfg.trayNoticeShown),
    coreKind: draft.coreKind || "existing", coreVersion: draft.coreVersion || null, modelsReady: !!draft.modelsReady };
  const old = /** @type {any} */ (core.loadConfig(CONFIG_DIR) || {});       // keep the license and update state (017)
  for (const k of ["installId", "lease", "licenseClock", "licenseRefused", "licenseLabel", "licenseExpires", "pendingUpdate"]) {
    if (old[k] !== undefined) /** @type {any} */ (c)[k] = old[k];
  }
  if (!(await studioThere(c))) return { ok: false, error: `No studio at ${c.studio}` };
  cfg = c;
  core.saveConfig(CONFIG_DIR, c);
  if (setupWin && !setupWin.isDestroyed()) setupWin.destroy();
  setupWin = null;
  if (await ensureLicense()) startCore();
  return { ok: true };
}

// ---------- the packaged core (specs/016 T014, T020) ----------
const FAKE_INSTALL = process.env.CU_FAKE_INSTALL === "1";      // smoke runs: real checks and unpacking, no commands
const PACKAGED_DIR = process.env.CU_PACKAGED_DIR || (app.isPackaged ? path.join(process.resourcesPath, "core") : null);
const LOCAL = PLATFORM === "win32" ? path.join(process.env.LOCALAPPDATA || os.homedir(), "ClaudeUtube") : null;

async function packagedInfo() {
  const manifest = core.readManifest(PACKAGED_DIR);
  if (!manifest) return { available: false };
  let installed = null, distroThere = false;
  if (PLATFORM === "win32" && !FAKE_INSTALL) {
    const list = await run({ file: "wsl.exe", args: ["-l", "-v"] }, 20_000);
    distroThere = core.hasOwnDistro(list.stdout);
    if (distroThere) {
      const v = await run({ file: "wsl.exe", args: ["-d", core.DISTRO, "--", "cat", "/home/studio/claude-Utube/.core-version"] }, 20_000);
      installed = v.code === 0 ? v.stdout.toString("utf8").replace(/\0/g, "").trim() : null;
    }
  } else if (PLATFORM === "darwin") {
    const f = path.join(core.macCoreDir(os.homedir(), manifest.version), ".core-version");
    installed = fs.existsSync(f) ? fs.readFileSync(f, "utf8").trim() : null;
  }
  const steps = core.installSteps(PLATFORM, { manifest, coreFile: "", tmpDir: os.tmpdir(), home: os.homedir() }).map((s) => s.id);
  return { available: true, platform: PLATFORM, manifest, installed, distroThere, steps,
    reinstall: core.needsReinstall(installed, manifest), smoke: SMOKE };
}

ipcMain.handle("setup:packaged", async () => packagedInfo());

/** Gunzip the core file into a .tar for `wsl --import` (Windows). @param {string} from @param {string} to */
function gunzipTo(from, to) {
  const zlib = require("node:zlib");
  const { pipeline } = require("node:stream/promises");
  fs.mkdirSync(path.dirname(to), { recursive: true });
  return pipeline(fs.createReadStream(from), zlib.createGunzip(), fs.createWriteStream(to));
}

ipcMain.handle("setup:installCore", async (e, opts) => {
  const info = await packagedInfo();
  if (!info.available || !info.manifest) return { ok: false, step: "verify", error: "This copy of the app has no studio package." };
  const m = info.manifest;
  const coreFile = path.join(String(PACKAGED_DIR), m.file);
  const tmpDir = FAKE_INSTALL ? path.join(CONFIG_DIR, "tmp") : (LOCAL ? path.join(LOCAL, "tmp") : os.tmpdir());
  const steps = core.installSteps(PLATFORM, { manifest: m, coreFile, tmpDir, wslDir: LOCAL ? path.join(LOCAL, "wsl") : undefined,
    reinstall: info.reinstall, distroThere: info.distroThere, home: os.homedir() });
  const skipInstall = PLATFORM === "darwin" && info.installed === m.version;       // unpacked before: go on with the models
  let i = opts && opts.from ? Math.max(0, steps.findIndex((s) => s.id === opts.from)) : 0;
  const send = (/** @type {any} */ msg) => { if (!e.sender.isDestroyed()) e.sender.send("setup:progress", msg); };
  for (; i < steps.length; i++) {
    const st = steps[i];
    send({ step: st.id, text: st.text, index: i, total: steps.length });
    try {
      if (st.id === "verify") {
        if (!fs.existsSync(coreFile)) throw new Error(`The studio package is missing: ${coreFile}`);
        if ((await core.sha256File(coreFile)) !== m.sha256) throw new Error("The studio package is damaged (SHA-256 does not match). Download the installer again.");
      } else if (st.id === "space") {
        const where = PLATFORM === "win32" ? tmpDir : os.homedir();
        fs.mkdirSync(where, { recursive: true });
        const sf = fs.statfsSync(where);
        const free = sf.bavail * sf.bsize, need = core.spaceNeeded(m, PLATFORM);
        if (!FAKE_INSTALL && free < need) throw new Error(`Not enough free space: ${(need / 1024 ** 3).toFixed(1)} GB needed, ${(free / 1024 ** 3).toFixed(1)} GB free.`);
      } else if (st.id === "unpack") {
        await gunzipTo(coreFile, path.join(tmpDir, "core.tar"));
      } else if (st.id === "install" && skipInstall) {
        continue;
      } else if (st.id === "install" && PLATFORM === "darwin" && !core.espeakPathOk(core.macCoreDir(os.homedir(), m.version))) {
        throw new Error("Your user folder path is too long for the voice engine (over 160 bytes).");
      }
      for (const cmd of st.run) {
        if (FAKE_INSTALL) { smoke(`install would run ${cmd.file} ${cmd.args[0] || ""}`); continue; }
        const r = await run(cmd, 60 * 60_000);
        if (r.code !== 0) {
          const out = (r.stdout.toString("utf8") + "\n" + r.stderr.toString("utf8")).replace(/\0/g, "").trim().split("\n").slice(-8).join("\n");
          throw new Error(out || `${cmd.file} failed (code ${r.code})`);
        }
      }
      if (st.id === "install" && PLATFORM === "win32") fs.rmSync(path.join(tmpDir, "core.tar"), { force: true });
      if (st.id === "check" && !FAKE_INSTALL) {
        const c = core.packagedConfig(PLATFORM, m, os.homedir());
        const r = await run(core.coreCommand(c, ["check", "--json"]), 60_000);
        const check = (() => { try { return JSON.parse(r.stdout.toString("utf8").trim().split("\n").pop() || ""); } catch { return null; } })();
        if (!check || !check.ok) throw new Error("Missing: " + ((check && check.missing) || ["the studio did not answer"]).join("; "));
      }
    } catch (err) {
      send({ step: st.id, error: String(err && /** @type {any} */ (err).message || err) });
      return { ok: false, step: st.id, error: String(err && /** @type {any} */ (err).message || err) };
    }
  }
  const c = { ...core.packagedConfig(PLATFORM, m, os.homedir()), modelsReady: true };
  if (FAKE_INSTALL) c.data = path.join(CONFIG_DIR, "data");
  smoke("install ok");
  return finishSetup(c);
});

ipcMain.handle("core:restart", async () => {
  if (win && !win.isDestroyed()) {
    const r = await coreRun(["start", ...gateArgs()], core.READY_TIMEOUT_MS + 5_000);
    const url = core.parseUrl(r.out);
    if (!url) return { ok: false, error: (r.out + r.err).trim().split("\n").slice(-5).join("\n") };
    appUrl = url;
    win.loadURL(url);
    return { ok: true };
  }
  startCore();
  return { ok: true };
});
ipcMain.handle("core:retry", () => { startCore(); return { ok: true }; });
ipcMain.handle("core:openLogs", () => openFolder("logs"));
ipcMain.handle("core:quit", () => app.quit());

// ---------- smoke run (GitHub Actions; specs/015 R4) ----------
/** specs/018 T009: the Client shows the fake Host's page over the pinned HTTPS; the Host stops; the Client says so. */
async function smokeClient() {
  if (win && win.getTitle() !== "fake core") return smokeFail(`window title is ${win && win.getTitle()}`);
  smoke("window ok");
  if (process.env.CU_SMOKE_UPDATE === "1") {
    await checkUpdates(true);
    if (!pendingUpdate()) return smokeFail("no update ready through the Host");
  }
  if (process.env.CU_SMOKE_CONTROL) await fetch(`${process.env.CU_SMOKE_CONTROL}/stop`, { method: "POST" }).catch(() => {});
  await new Promise((r) => setTimeout(r, 500));
  await checkHost();
  await new Promise((r) => setTimeout(r, 1500));
  if (!offlineShown) return smokeFail("the offline page did not show");
  app.quit();
}

/** specs/017 T020: the fake license server offers a newer release; it downloads, checks, and (Windows) installs on quit. */
async function smokeUpdate() {
  smoke("window ok");
  await checkUpdates(true);
  if (!pendingUpdate()) return smokeFail("no update ready");
  app.quit();
}

/** specs/017 T016: the fake license server turns the key off; the next renewal locks the app. */
async function smokeLicense() {
  smoke("window ok");
  const gateDoc = readJson(GATE);
  if (!gateDoc || !gateDoc.lease || gateDoc.deviceId !== deviceId) return smokeFail("no gate file for the core");
  await fetch(`${LIC && LIC.server}/__revoke`, { method: "POST" });
  await renew(await readKey());
  if (licenseProblem()) lock();
  if (!locked) return smokeFail("not locked after the key was turned off");
  const after = readJson(GATE);
  if (!after || after.refused !== "revoked") return smokeFail("the gate file does not say revoked");
  if (win && win.isVisible()) return smokeFail("the studio window is still shown");
  quitting = false;
  app.quit();
}

function smokeSetup() {
  smoke("setup ok");
  if (process.env.CU_SMOKE_PAIR) {                       // specs/018: pair with the fake Host
    const [address, code] = process.env.CU_SMOKE_PAIR.split("|");
    pairClient({ address, code, name: "smoke" }).then((r) => { if (!r.ok) smokeFail(`pair: ${r.error}`); });
    return;
  }
  if (PACKAGED_DIR) return;                              // setup.html starts the install itself (smoke-install)
  finishSetup({ distro: null, studio: process.cwd(), data: path.join(CONFIG_DIR, "data") });
}

/** @param {number} port */
async function smokeMain(port) {
  if (!win) return;
  if (win.getTitle() !== "fake core") return smokeFail(`window title is ${win.getTitle()}`);
  smoke(`window ok ${port}`);
  if (process.env.CU_SMOKE_SHARE === "1") {             // specs/018: share, pair a computer, open the page through the gateway
    shareState().port = 0;
    shareState().enabled = true;
    await startSharing();
    if (!gateway) return smokeFail(`sharing did not start: ${shareError}`);
    const { code } = pairing.open();
    const p = await share.pairWithHost(`127.0.0.1:${gateway.port}`, code, "smoke client").catch((e) => smokeFail(`pair: ${e}`));
    if (!p) return;
    const r = await share.pinnedFetch(p.fingerprint)(`https://127.0.0.1:${gateway.port}/`, { headers: { "x-cu-client": share.clientHeader(p) } });
    if (!/fake core/.test(await r.text())) return smokeFail("the gateway did not pass the core's page on");
    if (shareState().clients.length !== 1) return smokeFail("the paired computer was not saved");
    await stopSharing();
    smoke("share pair ok");
  }
  await win.webContents.executeJavaScript("document.getElementById('out').click()");
  await new Promise((r) => setTimeout(r, 500));
  const second = spawn(process.execPath, [__dirname, "--smoke-second"], { env: process.env, stdio: "ignore" });
  const code = await new Promise((r) => { const t = setTimeout(() => r("timeout"), 10_000); second.on("exit", (c) => { clearTimeout(t); r(c); }); });
  if (code === "timeout") return smokeFail("a second instance stayed open");
  smoke("second instance ok");
  win.close();
  if (win.isDestroyed() || win.isVisible()) return smokeFail("closing the window did not hide it");
  smoke("hide ok");
  await coreRun(["stop", "--force"]);              // the core stops behind the app's back
  await checkCore();
}

async function smokeAfterStopped() {
  const r = await coreRun(["start"], 20_000);
  appUrl = core.parseUrl(r.out) || appUrl;
  process.env.FAKE_CORE_JOB = "1";                  // one job runs: quitting has to ask
  process.env.CU_SMOKE_ANSWER = "cancel";
  app.quit();
  await new Promise((res) => setTimeout(res, 3000));
  if ((await coreStatus()).running !== true) return smokeFail("cancel stopped the core");
  process.env.CU_SMOKE_ANSWER = "quit";
  app.quit();
}

// ---------- start ----------
if (!app.requestSingleInstanceLock()) {
  app.exit(0);                                       // FR-001: the first instance shows its window
} else {
  app.on("second-instance", showMain);
  app.on("window-all-closed", () => { /* keep running in the tray */ });
  app.whenReady().then(async () => {
    if (SECOND) return app.exit(0);
    if (PLATFORM === "darwin" && app.dock) app.dock.setIcon(path.join(ASSETS, "icon.png"));
    cfg = core.loadConfig(CONFIG_DIR);
    if (SMOKE && !cfg && process.env.CU_SMOKE_NO_SETUP === "1") {
      cfg = { platform: PLATFORM, distro: null, studio: process.cwd(), data: path.join(CONFIG_DIR, "data"), home: null };
      core.saveConfig(CONFIG_DIR, cfg);
    }
    if (isClient() && /** @type {any} */ (cfg).host) {           // specs/018: no core, no license here
      startClient();
      scheduleUpdates();
      return;
    }
    if (!cfg) return showSetup();                    // first run: choose Host or Client first (a Client needs no license)
    scheduleUpdates();
    if (await ensureLicense()) afterLicense();
  });
}
