// specs/035: the Animatic step of an After Effects film job page, in a real browser.
//   node browser_animatic.cjs <base> <job id> [screenshot prefix]   (exit 77 = no browser)
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, jid, shot] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const out = { errors: [] };
  const open = async (width) => {
    const p = await browser.newPage({ viewport: { width, height: 1100 } });
    p.on("pageerror", (e) => out.errors.push(String(e)));
    await p.goto(`${base}/#/jobs/${jid}`);
    try { await p.waitForSelector(".anim .tl .sh", { timeout: 30000 }); }
    catch (e) { if (shot) await p.screenshot({ path: `${shot}-fail.png`, fullPage: true }); console.error((await p.locator("body").innerText()).slice(0, 800), out.errors); throw e; }
    return p;
  };
  const p = await open(1280);
  out.rail = await p.locator("#rail-slot .rail .t").allTextContents();
  out.gate = await p.locator("#rail-slot .rail button[data-step='Animatic'] .gate").count();
  out.silence = await p.locator("#anim-silence").textContent();
  out.silenceWarn = await p.locator("#anim-silence.warn").count();
  out.shots = await p.locator(".anim .tl .sh").count();
  out.lines = await p.locator(".anim .tl .vo").count();
  out.gaps = await p.locator(".anim .tl .gap").count();
  out.cards = await p.locator(".anim .shot-grid .shot").count();
  out.pictures = await p.locator(".anim .shot-grid .shot img").count();
  out.player = await p.locator("video.anim-draft").count();
  out.suggestions = await p.locator(".anim-sugg li").count();
  out.impact = await p.locator("#impact .chip").allTextContents();
  out.approveDisabled = await p.$eval("#approve", (x) => x.disabled).catch(() => null);
  out.anyway = await p.locator("#approve-anyway").count();
  if (shot) await p.screenshot({ path: `${shot}-1280.png`, fullPage: true });
  await p.click(".anim [data-acc='S2']");                                   // accept one suggestion
  await p.waitForFunction(() => !document.querySelector(".anim-sugg li[data-shot='S2']"), null, { timeout: 60000 });
  await p.waitForSelector("#anim-undo", { timeout: 120000 });                // the rebuild of S2 ends, edits open again
  out.afterAccept = { suggestions: await p.locator(".anim-sugg li").count(), undo: await p.locator("#anim-undo").count(),
    total: await p.locator("#anim-total").textContent() };
  // pin a note on S2's clip: pause, click at 25% / 40% of the picture (SC-007: within 2% of the frame width)
  const pinAt = async (page, shotId, fx, fy, text) => {
    await page.click(`.anim .shot-grid .shot[data-pick='${shotId}']`);
    await page.waitForSelector("#anim-note video.anim-clip", { timeout: 10000 });
    const src = await page.$eval("#anim-note video.anim-clip", (v) => v.getAttribute("src"));
    await page.$eval("#anim-note video.anim-clip", (v) => new Promise((ok) => {
      const go = () => { v.pause(); v.currentTime = 1; v.addEventListener("seeked", () => ok(), { once: true }); };
      if (v.readyState >= 1) go(); else v.addEventListener("loadedmetadata", go, { once: true });
    }));
    const box = await page.locator("#anim-note video.anim-clip").boundingBox();
    await page.mouse.click(box.x + box.width * fx, box.y + box.height * fy);
    await page.waitForSelector("#anim-pin-note", { timeout: 5000 });
    await page.fill("#anim-pin-note", text);
    await page.click("#anim-pin-save");
    await page.waitForFunction((t) => [...document.querySelectorAll(".anim-notes li")].some((x) => x.textContent.includes(t)), text, { timeout: 30000 });
    await page.waitForFunction(() => { const el = document.querySelector("#anim-clipwrap .pin"); return el && !el.hidden; }, null, { timeout: 10000 });
    const pin = await page.$eval("#anim-clipwrap .pin", (el) => {
      const w = el.parentElement.querySelector("video").getBoundingClientRect(), r = el.getBoundingClientRect();
      return { dx: (r.left + r.width / 2 - w.left) / w.width, dy: (r.top + r.height / 2 - w.top) / w.height, hidden: el.hidden };
    });
    return { src, pin };
  };
  const one = await pinAt(p, "S2", 0.25, 0.4, "the cup falls too early");
  out.clip = one.src;
  out.pin1280 = { dx: Math.abs(one.pin.dx - 0.25), dy: Math.abs(one.pin.dy - 0.4), hidden: one.pin.hidden };
  out.notesOpen = await p.locator(".anim .shot-grid .shot[data-pick='S2'] .chip.warn").count();
  out.sendLabel = await p.locator("#anim-send").textContent().catch(() => null);
  const m = await open(400);
  out.narrow = await m.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
  const two = await pinAt(m, "S6", 0.7, 0.6, "slower walk");
  const pins = await m.$$eval("#anim-clipwrap .pin", (els) => els.map((el) => {
    const w = el.parentElement.querySelector("video").getBoundingClientRect(), r = el.getBoundingClientRect();
    return { dx: (r.left + r.width / 2 - w.left) / w.width, dy: (r.top + r.height / 2 - w.top) / w.height };
  }));
  out.pin400 = { dx: Math.abs(pins[0].dx - 0.7), dy: Math.abs(pins[0].dy - 0.6) };
  out.narrowAfter = await m.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
  if (shot) await m.screenshot({ path: `${shot}-400.png`, fullPage: true });
  out.sendLabel2 = await m.locator("#anim-send").textContent();
  await m.click("#anim-send");                                              // one request with S2 and S6
  await m.waitForFunction(() => !document.querySelector("#anim-send") || document.querySelector("#anim-lot"), null, { timeout: 30000 });
  await browser.close();
  console.log(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
