// The bridge of the app's own pages (splash.html, setup.html, stopped.html) to main.js (specs/015 contracts/core.md).
// The studio's pages in the main window get nothing from here: they only talk to the studio over HTTP.
"use strict";
const { contextBridge, ipcRenderer } = require("electron");

if (location.protocol === "file:") {
  contextBridge.exposeInMainWorld("setup", {
    check: (draft) => ipcRenderer.invoke("setup:check", draft),
    enableWsl: () => ipcRenderer.invoke("setup:enableWsl"),
    finish: (draft) => ipcRenderer.invoke("setup:finish", draft),
    packaged: () => ipcRenderer.invoke("setup:packaged"),
    installCore: (opts) => ipcRenderer.invoke("setup:installCore", opts),
    onProgress: (fn) => ipcRenderer.on("setup:progress", (_e, msg) => fn(msg)),
  });
  contextBridge.exposeInMainWorld("license", {
    state: () => ipcRenderer.invoke("license:state"),
    submit: (key) => ipcRenderer.invoke("license:submit", key),
    onMode: (fn) => ipcRenderer.on("license:mode", (_e, mode) => fn(mode)),
  });
  contextBridge.exposeInMainWorld("core", {
    restart: () => ipcRenderer.invoke("core:restart"),
    retry: () => ipcRenderer.invoke("core:retry"),
    openLogs: () => ipcRenderer.invoke("core:openLogs"),
    quit: () => ipcRenderer.invoke("core:quit"),
  });
}
