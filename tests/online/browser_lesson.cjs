// "Save this as a lesson" on a finished film's job page (specs/012 T027). Called by test_channels_api.py.
// argv: base email password channelJobId plainJobId. Exit 77 = no browser.
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, email, password, chanJob, plainJob] = process.argv.slice(2);
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
  await page.goto(`${base}/#/jobs/${plainJob}`);
  await page.waitForSelector("#changes");
  const plainHasBox = await page.locator("#change-lesson").count();
  await page.goto(`${base}/#/jobs/${chanJob}`);
  await page.waitForSelector("#changes");
  await page.click("#changes summary");
  const label = await page.locator("label:has(#change-lesson)").innerText();
  await page.check("#change-lesson");
  await page.fill("#change-note", "The ending is too fast");
  await page.click("#send-changes");
  await page.waitForFunction((old) => /^#\/jobs\//.test(location.hash) && !location.hash.endsWith(old), chanJob);
  const newJob = decodeURIComponent(page.url().split("#/jobs/")[1]);
  await browser.close();
  console.log(JSON.stringify({ errors, plainHasBox, label, newJob }));
})().catch((e) => { console.error(e); process.exit(1); });
