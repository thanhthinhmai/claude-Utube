// Answer a question and ask for changes on the job page (specs/007 T043). Called by test_film_dialog.py.
// argv: base email password jobId. Exit 77 = no browser.
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
  await page.waitForSelector("#acct >> text=films left this month");   // phone width: the account menu is in the top bar
  await page.goto(`${base}/#/jobs/${jobId}`);
  await page.waitForSelector("text=The studio has a question", { timeout: 30000 });
  await page.fill("#answer", "Orange, with a red scarf");
  await page.click("#send-answer");
  await page.waitForSelector("text=Download the film", { timeout: 60000 });
  await page.click("#changes summary");
  await page.fill("#change-note", "A slower ending");
  await page.click("#send-changes");
  await page.waitForFunction((id) => !location.hash.endsWith(id), jobId);
  const newJob = page.url().split("/#/jobs/")[1];
  await page.waitForSelector("text=Download the film", { timeout: 60000 });
  await browser.close();
  console.log(JSON.stringify({ errors, newJob }));
})().catch((e) => { console.error(e); process.exit(1); });
