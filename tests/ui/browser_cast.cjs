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
