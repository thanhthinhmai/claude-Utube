// specs/025 SC-003: the Done so far section follows the job live and keeps the open section. Called by
// test_done_so_far.py: node browser_done_live.cjs <base> <job id> <ready file>. Exit 77 = no browser.
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const fs = require("fs");
const [base, jid, ready] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(`${base}/#/jobs/${jid}`);
  await page.waitForSelector("#done-steps button[data-t='shots']:not([disabled])", { timeout: 10000 });
  await page.click("#done-steps button[data-t='shots']");
  await page.waitForSelector(".sheet-img");
  await page.waitForSelector("text=Live updates on", { timeout: 10000 });
  fs.writeFileSync(ready, "1");
  const t0 = Date.now();
  const changed = await page.waitForSelector("#done-steps button[data-t='selfcheck'].st-done", { timeout: 12000 })
    .then(() => Date.now() - t0).catch(() => null);
  const kept = await page.locator(".sheet-img").count();
  const step = await page.locator("#step-panel .step-name").innerText();
  await browser.close();
  console.log(JSON.stringify({ errors, changed, kept, step }));
})().catch((e) => { console.error(e); process.exit(1); });
