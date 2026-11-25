// specs/034: the Cast step of an After Effects film job page, in a real browser.
//   node browser_cast.cjs <base> <job id> [screenshot.png]   (exit 77 = no browser)
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, jid, shot] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const p = await browser.newPage({ viewport: { width: 1280, height: 1100 } });
  const out = { errors: [] };
  p.on("pageerror", (e) => out.errors.push(String(e)));
  await p.goto(`${base}/#/jobs/${jid}`);
  try { await p.waitForSelector("#rail-slot .rail button[data-step='Cast']", { timeout: 20000 }); }
  catch (e) { if (shot) await p.screenshot({ path: shot, fullPage: true }); console.error(p.url(), (await p.locator("body").innerText()).slice(0, 800), out.errors); throw e; }
  out.castGate = await p.locator("#rail-slot .rail button[data-step='Cast'] .gate").count();
  await p.waitForSelector(".cast-split .who button", { timeout: 20000 });
  out.characters = await p.locator(".cast-split .who button").count();
  out.pictures = await p.locator(".cast-split .fr img, .cast-split .fr video").count();
  out.missing = await p.locator(".cast-split .fr.missing").count();
  out.groups = await p.locator(".cast-split .cast-sheet h3").allTextContents();
  out.approveCastDisabled = await p.$eval("#approve", (x) => x.disabled).catch(() => null);
  out.saveBox = await p.locator(".cast-save input").count();
  out.toggleCast = await p.locator("#point-toggles input[value='cast']").count();
  if (shot) await p.screenshot({ path: shot, fullPage: true });
  // pins (T027): click a spot, the pin lands on it (within 2 % of the picture), at 1280 px and at 400 px
  const pinAt = async (page, fx, fy) => {
    const tile = page.locator(".cast-split .imgwrap[data-pick='front']").first();
    await tile.scrollIntoViewIfNeeded();
    const r = await tile.boundingBox();
    await page.mouse.click(r.x + r.width * fx, r.y + r.height * fy);
    await page.waitForSelector(".cast-split .pinbox #pin-note", { timeout: 10000 });
    await page.fill("#pin-note", `Hair: bigger curls ${fx}`);
    if (process.env.CAST_PINSHOT) await page.screenshot({ path: `${process.env.CAST_PINSHOT}-${fx}.png`, fullPage: true });
    await page.click("#pin-save");
    try { await page.waitForSelector(".cast-split .cast-notes li", { timeout: 60000 }); }
    catch (e) { throw new Error(`no note: ${await page.locator("#pin-msg").textContent().catch(() => "?")} ${out.errors}`); }
    await page.waitForSelector(".cast-split .imgwrap[data-pick='front'] .pin:not([hidden])", { timeout: 10000 });
    const t2 = await page.locator(".cast-split .imgwrap[data-pick='front']").first().boundingBox();
    const pb = await page.locator(".cast-split .imgwrap[data-pick='front'] .pin").first().boundingBox();
    const off = [Math.abs((pb.x + pb.width / 2 - t2.x) / t2.width - fx), Math.abs((pb.y + pb.height / 2 - t2.y) / t2.height - fy)];
    const notes = await page.locator(".cast-split .cast-notes li").count();
    await page.click(".cast-split .cast-notes [data-del]");
    await page.waitForSelector(".cast-split .cast-notes li", { state: "detached", timeout: 60000 });
    return { off: Math.max(...off), notes };
  };
  out.pin1280 = await pinAt(p, 0.3, 0.4);
  const ask = p.locator(".cast-split .fr.missing [data-ask]").first();
  await ask.click();
  await p.waitForSelector(".cast-split .fr.missing.noted [data-ask]", { timeout: 60000 });
  out.askLabel = (await p.locator(".cast-split .fr.missing [data-ask]").first().textContent()).trim();
  out.sendNotes = (await p.locator("#send-notes").textContent().catch(() => "")).trim();
  await p.click(".cast-split .fr.missing [data-ask]");
  await p.waitForSelector(".cast-split .fr.missing:not(.noted) [data-ask]", { timeout: 60000 });
  const small = await browser.newPage({ viewport: { width: 400, height: 900 } });
  small.on("pageerror", (e) => out.errors.push(String(e)));
  await small.goto(`${base}/#/jobs/${jid}`);
  await small.waitForSelector(".cast-split .imgwrap[data-pick='front'] img", { timeout: 20000 });
  out.pin400 = await pinAt(small, 0.6, 0.5);
  out.scroll400 = await small.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  await small.close();
  await p.click(".cast-split .who button[data-who='friend']");
  await p.waitForSelector(".cast-split .who button[data-who='friend'][aria-selected='true']", { timeout: 10000 });
  const btn = p.locator("#cast-who-act button");
  out.approveOne = await btn.count();
  if (out.approveOne) {
    await btn.click();
    await p.waitForSelector(".cast-split .who button[data-who='friend'] .chip.ok", { timeout: 60000 });
    out.friendApproved = true;
  }
  console.log(JSON.stringify(out));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
