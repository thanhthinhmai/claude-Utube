// The Topics block of a channel page and "Make a film" from a topic (specs/013 T016). Called by test_topics_api.py.
// argv: base email password. Exit 77 = no browser.
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
  await page.waitForSelector("text=Forgot your password?");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click("button[type=submit]");
  await page.waitForSelector("#acct >> text=films left this month");
  await page.goto(`${base}/#/channels/honey`);
  await page.waitForSelector("#topics table.topics");
  const table = await page.locator("#topics table.topics").innerText();
  const fits = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
  await page.click("#t-make");
  await page.waitForSelector("#idea");
  await page.waitForFunction(() => document.getElementById("idea").value.length > 0);
  const idea = await page.inputValue("#idea");
  const channel = await page.inputValue("#f-channel");
  await browser.close();
  console.log(JSON.stringify({ errors, table, fits, idea, channel }));
})().catch((e) => { console.error(e); process.exit(1); });
