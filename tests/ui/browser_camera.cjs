// specs/039: the Camera page of an After Effects film job page, in a real browser.
//   node browser_camera.cjs <base> <job id> [screenshot prefix]   (exit 77 = no browser)
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
    try {
      await p.waitForSelector("#rail-slot button[data-step='Camera']", { timeout: 30000 });
      if (!(await p.locator(".cam").count())) await p.click("#rail-slot button[data-step='Camera']");
      await p.waitForSelector(".cam .shot-grid .shot", { timeout: 30000 });
    } catch (e) { if (shot) await p.screenshot({ path: `${shot}-fail.png`, fullPage: true }); console.error((await p.locator("body").innerText()).slice(0, 800), out.errors); throw e; }
    return p;
  };
  const p = await open(1280);
  out.shots = await p.$$eval(".cam .shot-grid .shot", (els) => els.map((x) => x.dataset.cam));
  out.star = (await p.locator(".cam .shot-grid .star").count()) === out.shots.length;
  await p.click(".cam .shot[data-cam='S1']");
  await p.waitForSelector("#cam-box .cam-opt", { timeout: 10000 });
  out.options = await p.locator("#cam-box .cam-opt").count();
  out.refs = await p.locator("#cam-box .cam-ref img").count();
  // ▶ animates the still to the end window
  await p.click("#cam-box [data-prev='1']");
  await p.waitForTimeout(150);
  out.preview = await p.$eval("#cam-box .cam-opt[data-n='1'] .cam-still img", (img) => img.style.transform.startsWith("scale(") && !!img.dataset.playing);
  // "Use this" on option 2
  await p.click("#cam-box [data-use='2']");
  await p.waitForSelector("#cam-box .cam-opt.on[data-n='2']", { timeout: 60000 });
  out.chosen = Number(await p.$eval("#cam-box .cam-opt.on", (x) => x.dataset.n));
  // pin a note on S2 option 1
  await p.click(".cam .shot[data-cam='S2']");
  await p.waitForSelector("#cam-box[data-shot='S2'] .cam-still", { timeout: 10000 });
  const still = p.locator("#cam-box .cam-opt[data-n='1'] .cam-still");
  await still.scrollIntoViewIfNeeded();
  const box = await still.boundingBox();
  await still.click({ position: { x: box.width * 0.3, y: box.height * 0.4 } });
  await p.waitForSelector("#cam-pin-note", { timeout: 5000 });
  await p.fill("#cam-pin-note", "slower push");
  await p.click("#cam-pin-save");
  await p.waitForFunction(() => [...document.querySelectorAll("#cam-box .anim-notes li")].some((x) => x.textContent.includes("slower push")), null, { timeout: 30000 });
  out.noteShown = await p.locator(".cam .shot[data-cam='S2'] .dot-note").count();
  out.sendText = await p.locator("#cam-send").textContent().catch(() => null);
  out.approveDisabled = await p.$eval("#approve", (x) => x.disabled).catch(() => null);
  if (shot) await p.screenshot({ path: `${shot}-1280.png`, fullPage: true });
  const m = await open(400);
  await m.click(".cam .shot[data-cam='S1']");
  await m.waitForSelector("#cam-box .cam-opt", { timeout: 10000 });
  out.wide = await m.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  if (shot) await m.screenshot({ path: `${shot}-400.png`, fullPage: true });
  await browser.close();
  console.log(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
