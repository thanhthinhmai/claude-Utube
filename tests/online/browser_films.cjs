// Films page shows films being made with their stages (Films → In progress). argv: base email password.
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
  await page.goto(`${base}/#/films`);
  await page.waitForSelector("text=In progress");
  const cls = async (st) => page.locator(".stages li", { hasText: st }).first().getAttribute("class");
  const got = { Treatment: await cls("Treatment"), Voice: await cls("Voice"), Look: await cls("Look"), Render: await cls("Render") };
  const storyboard = await page.locator(".stages li", { hasText: "Storyboard" }).count();
  const wide = await page.evaluate(() => document.documentElement.scrollWidth);
  await browser.close();
  console.log(JSON.stringify({ errors, got, storyboard, wide }));
})().catch((e) => { console.error(e); process.exit(1); });
