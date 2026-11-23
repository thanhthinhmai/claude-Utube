// specs/029: opens a film page in a real browser and uses the Shots section: timeline, list, play one shot, add a note
// with a pasted picture, tick it, filters, the previous version, "Fix with Claude". Called by test_shot_notes.py, and
// by hand: node browser_shots.cjs <base> <film> [screenshot dir]. Prints JSON. Exit 77 = no browser.
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, film, shots, filmDir] = process.argv.slice(2);
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==", "base64");
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 1000 } });
  await ctx.grantPermissions(["clipboard-read", "clipboard-write"], { origin: base });
  const page = await ctx.newPage();
  page.on("dialog", (d) => d.accept());
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  const snap = async (name) => { if (shots) await page.screenshot({ path: `${shots}/${name}.png`, fullPage: true }); };
  const out = { errors };
  try {
    await page.goto(`${base}/#/films/${film}`);
    await page.waitForSelector("#sh-timeline .sh-cell", { timeout: 10000 });
    out.cells = await page.locator("#sh-timeline .sh-cell").count();
    out.rows = await page.locator("#sh-list .sh-row").count();
    await page.waitForFunction(() => document.querySelectorAll("#sh-list img.sh-thumb.ok").length >= 3, null, { timeout: 20000 });
    out.thumbsLoaded = await page.locator("#sh-list img.sh-thumb.ok").count();
    await page.click("#sh-list .sh-row[data-i='1']");
    out.paneTitle = (await page.locator("#sh-pane .sh-pane-head strong").innerText()).trim();
    out.prevDisabled = await page.locator("#sh-prev").isDisabled();
    // play one shot (H.264 may be missing in a test Chromium: then only the controls are checked)
    out.playable = await page.evaluate(() => new Promise((res) => {
      const v = /** @type {HTMLVideoElement} */ (document.getElementById("sh-pane-video"));
      if (v.readyState >= 1) return res(true);
      v.addEventListener("loadedmetadata", () => res(true), { once: true });
      v.addEventListener("error", () => res(false), { once: true });
      setTimeout(() => res(v.readyState >= 1), 4000);
    }));
    if (out.playable) {
      await page.evaluate(() => { /** @type {HTMLVideoElement} */ (document.getElementById("sh-pane-video")).muted = true; });
      await page.click("#sh-play");
      await page.waitForTimeout(300);
      out.pauseShown = await page.getAttribute("#sh-play", "aria-label");
      await page.waitForFunction(() => { const v = /** @type {HTMLVideoElement} */ (document.getElementById("sh-pane-video")); return v.paused && v.currentTime > 1.5; }, null, { timeout: 8000 }).catch(() => {});
      out.stoppedAt = await page.evaluate(() => /** @type {HTMLVideoElement} */ (document.getElementById("sh-pane-video")).currentTime);
      out.afterStopLabel = await page.getAttribute("#sh-play", "aria-label");
      await page.click("#sh-play"); await page.waitForTimeout(300); await page.click("#sh-play");   // play, then pause by hand
      out.pausedByHand = await page.evaluate(() => /** @type {HTMLVideoElement} */ (document.getElementById("sh-pane-video")).paused);
      out.afterPauseLabel = await page.getAttribute("#sh-play", "aria-label");
    }
    await page.click("#sh-next");
    out.nextTitle = (await page.locator("#sh-pane .sh-pane-head strong").innerText()).trim();
    out.nextDisabled = await page.locator("#sh-next").isDisabled();
    await page.click("#sh-prev");
    // an unsaved note stays on its own shot: switching shots shows an empty box, coming back brings it back
    await page.fill("#sh-note", "nháp shot 2");
    await page.click("#sh-next");
    out.otherShotBox = await page.inputValue("#sh-note");
    await page.click("#sh-prev");
    out.backBox = await page.inputValue("#sh-note");
    await page.waitForFunction(() => document.getElementById("sh-msg").textContent.trim() === "Saved", null, { timeout: 5000 }).catch(() => {});
    out.unsavedMsg = (await page.locator("#sh-msg").innerText()).trim();
    // typing alone saves: wait past the 1 s pause, reload, the note is there without pressing anything
    await page.fill("#sh-note", "gõ là lưu");
    await page.waitForTimeout(1800);
    await page.reload();
    await page.waitForSelector("#sh-list .sh-row");
    await page.click("#sh-list .sh-row[data-i='1']");
    out.typedSaved = (await page.locator("#sh-notes .sh-note .sh-note-text").allInnerTexts()).map((t) => t.trim());
    await page.click("#sh-notes .sh-del").catch(() => {});
    // a note with a pasted picture
    await page.fill("#sh-note", "tay người ngồi bị bàn che");
    await page.evaluate((b64) => {
      const bin = atob(b64), arr = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
      const dt = new DataTransfer();
      dt.items.add(new File([arr], "shot.png", { type: "image/png" }));
      document.getElementById("sh-note").dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
    }, PNG.toString("base64"));
    await page.waitForSelector("#sh-pending img", { timeout: 5000 });
    out.noteTextKept = await page.inputValue("#sh-note");
    await page.click("#sh-add");
    await page.waitForSelector("#sh-notes .sh-note .sh-note-imgs img", { timeout: 5000 });
    out.cell2 = await page.getAttribute("#sh-timeline .sh-cell[data-i='1']", "class");
    await page.click("#sh-filters button[data-f='fix']");
    out.fixRows = await page.locator("#sh-list .sh-row").count();
    out.fixLabel = (await page.locator("#sh-filters button[data-f='fix']").innerText()).replace(/\s+/g, " ");
    await snap("1-note");
    await page.reload();
    await page.waitForSelector("#sh-timeline .sh-cell.st-fix", { timeout: 10000 });
    await page.click("#sh-list .sh-row[data-i='1']");
    out.afterReload = await page.locator("#sh-notes .sh-note").count();
    out.afterReloadImg = await page.locator("#sh-notes .sh-note-imgs img").count();
    await page.check("#sh-notes .sh-done");
    await page.waitForSelector("#sh-timeline .sh-cell[data-i='1'].st-fixed", { timeout: 5000 });
    out.fixedBadge = (await page.locator("#sh-pane .sh-pane-head .badge").innerText()).trim();
    await page.click("#sh-notes .sh-status button[data-st='ok']");
    await page.waitForSelector("#sh-timeline .sh-cell[data-i='1'].st-ok", { timeout: 5000 });
    out.handStatus = "ok";
    // Fix with Claude
    await page.click("#sh-claude-copy");
    await page.waitForFunction(() => document.getElementById("sh-claude-copy").textContent.trim() === "Copied", null, { timeout: 3000 }).catch(() => {});
    out.copyLabel = (await page.locator("#sh-claude-copy").innerText()).trim();
    out.clipboard = await page.evaluate(() => navigator.clipboard.readText()).catch(() => null);
    out.prevButton = await page.locator("#sh-prev-version").count();
    if (out.prevButton) {
      await page.click("#sh-prev-version");
      await page.waitForSelector("#sh-prev-video", { timeout: 5000 });
      out.prevNote = (await page.locator("#sh-prev-slot p").innerText()).trim();
    }
    // live: changes made outside the page show up without a reload (specs/029)
    await page.goto(`${base}/#/films/${film}`); await page.waitForSelector("#sh-list .sh-row");
    await page.waitForTimeout(1500);                     // the event stream is connected
    const api = `${base}/api/v1/films/${film}`;
    const nb = await (await fetch(`${api}/notes`)).json();
    const sid = (await (await fetch(`${api}/shots`)).json()).shots[0].id;
    nb.doc.shots[sid] = { status: "none", status_by: "auto", notes: [{ at: null, text: "từ bên ngoài", images: [], done: false }] };
    await fetch(`${api}/notes`, { method: "PUT", headers: { "Content-Type": "application/json", "X-Studio": "1" }, body: JSON.stringify({ base: nb.base, doc: nb.doc }) });
    out.liveNote = await page.waitForSelector("#sh-timeline .sh-cell[data-i='0'].st-fix", { timeout: 8000 }).then(() => true).catch(() => false);
    if (filmDir) {
      const fs = require("fs"), path = require("path");
      const before = await page.getAttribute("#sh-pane-video", "src");
      const vid = path.join(filmDir, `${film}.mp4`), tmp = vid + ".new";
      fs.copyFileSync(path.join(filmDir, `${film}.prev.mp4`), tmp); fs.renameSync(tmp, vid);
      out.liveVideo = await page.waitForFunction((b) => document.getElementById("sh-pane-video").getAttribute("src") !== b, before, { timeout: 8000 }).then(() => true).catch(() => false);
    }
    await snap("2-done");
  } catch (e) {
    out.failed = String(e).split("\n")[0];
    await snap("x-failed");
  }
  console.log(JSON.stringify(out));
  await browser.close();
})();
