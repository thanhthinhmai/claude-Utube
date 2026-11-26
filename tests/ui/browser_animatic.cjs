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
  await p.click(".anim .shot-grid .shot >> nth=1");                          // a shot plays its clip
  await p.waitForSelector(".anim .shot-grid .shot video", { timeout: 10000 });
  out.clip = await p.$eval(".anim .shot-grid .shot video", (v) => v.getAttribute("src"));
  const m = await open(400);
  out.narrow = await m.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
  if (shot) await m.screenshot({ path: `${shot}-400.png`, fullPage: true });
  await browser.close();
  console.log(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
