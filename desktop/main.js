// @ts-check
// The desktop app (specs/015): one instance, a splash while the studio core starts, the setup screen the first time,
// the main window on the core's own page, a tray icon, and a safe quit. The core is `sh bin/studio app …` (specs/014):
// on macOS on this machine, on Windows inside WSL2. All decisions live in core.js; this file does the windows.
"use strict";

const { app, BrowserWindow, Tray, Menu, dialog, shell, ipcMain, Notification, nativeImage } = require("electron");
const { execFile, spawn } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const core = require("./core.js");

const SMOKE = process.argv.includes("--smoke");
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
  const r = await coreRun(["start"], core.READY_TIMEOUT_MS + 5_000).catch((e) => ({ code: 1, out: "", err: String(e) }));
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
}

// ---------- the main window ----------
/** @param {string} url */
function openMain(url) {
  const port = core.portOf(url);
  if (!win || win.isDestroyed()) {
    win = new BrowserWindow({ width: 1400, height: 900, minWidth: 960, minHeight: 600, show: false, title: "claude-Utube",
      icon: path.join(ASSETS, "icon.png"), autoHideMenuBar: true,
      webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true, preload: path.join(__dirname, "preload.js") } });
    win.webContents.setWindowOpenHandler(({ url: u }) => {
      if (!core.isAppUrl(u, core.portOf(appUrl))) openOutside(u);
      return { action: "deny" };
    });
    win.webContents.on("will-navigate", (e, u) => {
      if (!core.isAppUrl(u, core.portOf(appUrl)) && !u.startsWith("file:")) {
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
  if (SMOKE) win.webContents.once("did-finish-load", () => smokeMain(port));
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
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: "Open the studio", click: showMain },
    { label: "Open in the browser", click: () => appUrl && shell.openExternal(appUrl) },
    { type: "separator" },
    { label: "Data folder", click: () => openFolder("data") },
    { label: "Log folder", click: () => openFolder("logs") },
    { label: "Change setup…", click: changeSetup },
    { type: "separator" },
    { label: "Quit", click: () => app.quit() },
  ]));
  tray.on("click", showMain);
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
  const ok = await stopCore("Quit");
  if (!ok) { if (SMOKE) smoke("quit cancel ok"); return; }
  quitting = true;
  if (monitor) clearInterval(monitor);
  smoke("quit ok");
  app.exit(0);
});

// ---------- setup (US2) ----------
function showSetup() {
  setupWin = new BrowserWindow({ width: 760, height: 720, title: "Set up claude-Utube", icon: path.join(ASSETS, "icon.png"),
    show: !SMOKE, autoHideMenuBar: true,
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true } });
  setupWin.loadFile(path.join(__dirname, "setup.html"));
  if (SMOKE) setupWin.webContents.once("did-finish-load", smokeSetup);
}

async function changeSetup() {
  if (!(await stopCore("Stop the studio"))) return;
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
  if (!(await studioThere(c))) return { ok: false, error: `No studio at ${c.studio}` };
  cfg = c;
  core.saveConfig(CONFIG_DIR, c);
  if (setupWin && !setupWin.isDestroyed()) setupWin.destroy();
  setupWin = null;
  startCore();
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
    const r = await coreRun(["start"], core.READY_TIMEOUT_MS + 5_000);
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
function smokeSetup() {
  smoke("setup ok");
  if (PACKAGED_DIR) return;                              // setup.html starts the install itself (smoke-install)
  finishSetup({ distro: null, studio: process.cwd(), data: path.join(CONFIG_DIR, "data") });
}

/** @param {number} port */
async function smokeMain(port) {
  if (!win) return;
  if (win.getTitle() !== "fake core") return smokeFail(`window title is ${win.getTitle()}`);
  smoke(`window ok ${port}`);
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
    if (core.configUsable(cfg, PLATFORM, await studioThere(cfg))) startCore();
    else showSetup();
  });
}
