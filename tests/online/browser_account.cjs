// Account page in a real browser (specs/007 T040). Called by test_us4.py. argv: base email password newPassword.
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, email, password, newPassword] = process.argv.slice(2);
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
  await page.click(`#acct >> text=${email}`);
  await page.waitForSelector("text=Change password");
  await page.uncheck("#notify");
  await page.waitForSelector("#notify-msg >> text=Saved.");
  await page.fill("#old", password);
  await page.fill("#new", newPassword);
  await page.click("text=Change password");
  await page.waitForSelector("text=Your password is changed.");
  await page.fill("#del-pw", newPassword);
  await page.click("text=Delete my account");
  await page.waitForSelector("text=Account deleted");
  const wide = await page.evaluate(() => document.documentElement.scrollWidth);
  await browser.close();
  console.log(JSON.stringify({ errors, wide }));
})().catch((e) => { console.error(e); process.exit(1); });
