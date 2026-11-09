// Settings → Worker in a real browser, phone width (specs/009 T010). argv: base email password.
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, email, password] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const page = await browser.newPage({ viewport: { width: 360, height: 740 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(`${base}/#/login`);
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click("button[type=submit]");
  await page.waitForSelector("#acct summary.user-btn");
  await page.goto(`${base}/#/settings/worker`);
  await page.waitForSelector("text=Running · idle");
  await page.waitForSelector("text=jobs queued");
  await page.waitForSelector(".latest >> text=A fox");
  let refreshed = false;
  page.on("request", (r) => { if (r.url().endsWith("/api/v1/admin/worker")) refreshed = true; });
  await page.waitForTimeout(5600);
  const wide = await page.evaluate(() => document.documentElement.scrollWidth);
  await browser.close();
  console.log(JSON.stringify({ errors, wide, refreshed }));
})().catch((e) => { console.error(e); process.exit(1); });
