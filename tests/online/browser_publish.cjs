// The Publish block of a job page in a real browser (specs/011 T025). Called by test_publish_view.py.
// argv: base email password jobId. Exit 77 = no browser.
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, email, password, jobId] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const ctx = await browser.newContext({ viewport: { width: 360, height: 740 } });
  await ctx.grantPermissions(["clipboard-read", "clipboard-write"], { origin: base });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(`${base}/#/login`);
  await page.waitForSelector("text=Forgot your password?");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click("button[type=submit]");
  await page.waitForSelector("#acct >> text=films left this month");
  await page.goto(`${base}/#/jobs/${jobId}`);
  await page.waitForSelector("#publish .pub-card");
  const cards = await page.locator("#publish .pub-card").count();
  await page.locator("#publish button.copy").first().click();
  await page.waitForSelector("#publish button.copy >> text=Copied");
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  const fits = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
  const text = await page.locator("#publish").innerText();
  await browser.close();
  console.log(JSON.stringify({ errors, cards, copied, fits, text }));
})().catch((e) => { console.error(e); process.exit(1); });
