// The Channels pages and the channel choice of the new-film form in a real browser (specs/012 T021).
// Called by test_channels_api.py. argv: base email password style. Exit 77 = no browser.
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, email, password, style] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const page = await browser.newPage({ viewport: { width: 360, height: 740 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("dialog", (d) => d.dismiss());
  await page.goto(`${base}/#/login`);
  await page.waitForSelector("text=Forgot your password?");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click("button[type=submit]");
  await page.waitForSelector("#acct >> text=films left this month");
  await page.goto(`${base}/#/channels`);
  await page.waitForSelector("text=New channel");
  await page.fill("#c-name", "Tea Time");
  await page.fill("#c-slug", "tea-time");
  await page.fill("#c-seconds", "35");
  await page.selectOption("#c-style", style);
  await page.click("button[type=submit]");
  await page.waitForSelector("#profile");
  await page.click("text=Add a lesson");
  await page.fill("#l-what", "Cheap tricks in titles");
  await page.fill("#l-why", "Nothing checked it");
  await page.fill("#l-stop", "No clickbait words");
  await page.fill("#l-rule", "phrase:you won't believe");
  await page.click("#l-add");
  await page.waitForSelector("table.lessons >> text=Cheap tricks in titles");
  const lessons = await page.locator("table.lessons").innerText();
  const fits = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
  await page.goto(`${base}/#/new`);
  await page.waitForSelector("#f-channel");
  await page.fill("#seconds", "12");
  await page.selectOption("#f-channel", "tea-time");
  const seconds = await page.inputValue("#seconds");
  await browser.close();
  console.log(JSON.stringify({ errors, lessons, fits, seconds }));
})().catch((e) => { console.error(e); process.exit(1); });
