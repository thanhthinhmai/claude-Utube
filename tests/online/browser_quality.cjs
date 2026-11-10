// Job page Quality block and the script editor setting in a real browser (specs/010 T030). Called by
// test_quality_view.py. argv: base email password jobId. Exit 77 = no browser.
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, email, password, jobId] = process.argv.slice(2);
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
  await page.goto(`${base}/#/jobs/${jobId}`);
  await page.waitForSelector("#quality >> text=Quality");
  const quality = await page.locator("#quality").innerText();
  await page.goto(`${base}/#/settings/general`);
  await page.waitForSelector("text=Save settings");
  await page.selectOption("#s-editor_model", "sonnet");
  await page.click("text=Save settings");
  await page.waitForSelector("#msg >> text=Saved.");
  await browser.close();
  console.log(JSON.stringify({ errors, quality }));
})().catch((e) => { console.error(e); process.exit(1); });
