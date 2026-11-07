// Admin page in a real browser (specs/007 T037). Called by test_admin.py. argv: base email password. Exit 77 = no browser.
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
  page.on("dialog", (d) => d.accept());
  await page.goto(`${base}/#/login`);
  await page.waitForSelector("text=Forgot your password?");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click("button[type=submit]");
  await page.waitForSelector("text=films left this month");
  await page.goto(`${base}/#/admin`);
  await page.waitForSelector("text=Save settings");
  await page.fill("#s-quota_films_default", "3");
  await page.click("text=Save settings");
  await page.waitForSelector("#msg >> text=Saved.");
  const row = page.locator("tr", { hasText: "cust@example.com" });
  await row.locator('input[data-f="quota_films"]').fill("7");
  await row.locator('input[data-f="quota_films"]').press("Tab");
  await page.waitForSelector("#acc-msg >> text=Saved.");
  await row.locator("button[data-lock]").click();
  await page.waitForSelector('tr:has-text("cust@example.com") >> text=Unlock');
  const wide = await page.evaluate(() => document.documentElement.scrollWidth);
  await browser.close();
  console.log(JSON.stringify({ errors, wide }));
})().catch((e) => { console.error(e); process.exit(1); });
