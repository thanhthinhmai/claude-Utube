// Claude accounts page in a real browser (specs/008 T015). Called by test_claude_login.py. argv: base email password.
// Exit 77 = no browser. Prints {errors, wide, shot} as the last line.
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, email, password, shot] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const page = await browser.newPage({ viewport: { width: 360, height: 740 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("dialog", (d) => d.accept());
  page.on("popup", (p) => p.close().catch(() => {}));
  await page.goto(`${base}/#/login`);
  await page.waitForSelector("text=Welcome back");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click("button[type=submit]");
  await page.waitForSelector("#acct summary.user-btn");
  await page.goto(`${base}/#/admin/claude`);
  await page.waitForSelector("text=No Claude account signed in. Jobs cannot run.");
  await page.waitForSelector("text=Jobs cannot run until you sign in.");
  if (await page.locator("#add").count()) errors.push("Add account shown before the first account signs in");
  await page.click('li[data-slot="1"] .acc-actions button[data-act=login]');
  await page.waitForSelector('li[data-slot="1"] >> text=Signing in');
  await page.waitForSelector("text=Open the sign-in");
  await page.fill("#code", "good-owner@x.test");
  await page.click("#code-form button[type=submit]");
  await page.waitForSelector('li[data-slot="1"] >> text=owner@x.test');
  await page.waitForSelector('li[data-slot="1"] >> text=Usage not read yet');
  await page.waitForSelector(".summary >> text=1 ready");
  if (await page.locator("text=Jobs cannot run").count()) errors.push("warning still shown after sign-in");
  await page.click("#add");                                   // a new account opens its sign-in straight away
  await page.waitForSelector('li[data-slot="2"] >> text=Signing in');
  await page.fill("#code", "good-owner@x.test");               // the same Claude account again
  await page.click("#code-form button[type=submit]");
  await page.waitForSelector('li[data-slot="2"] >> text=Same Claude account as Claude');
  await page.click('li[data-slot="2"] details.menu summary');
  await page.click('li[data-slot="2"] .menu-list button[data-act=remove]');
  await page.waitForSelector('li[data-slot="2"]', { state: "detached" });
  await page.click('li[data-slot="1"] details.menu summary');
  await page.click('li[data-slot="1"] .menu-list button[data-act=logout]');
  await page.waitForSelector("text=No Claude account signed in. Jobs cannot run.");
  await page.click('li[data-slot="1"] .acc-actions button[data-act=login]');   // leave the sign-in open for the picture
  await page.waitForSelector("#code");
  if (shot) await page.screenshot({ path: shot, fullPage: true });
  await page.click("#acct summary.user-btn");                 // owner's menu on a phone: AI accounts, Settings, Log out
  await page.waitForSelector("#acct >> text=Owner");
  await page.click("#acct .menu-list >> text=Settings");
  await page.waitForSelector("text=Save settings");
  const wide = await page.evaluate(() => document.documentElement.scrollWidth);
  await page.click("#acct summary.user-btn");
  await page.click("#acct >> text=Log out");
  await page.waitForSelector("text=Welcome back");

  await browser.close();
  console.log(JSON.stringify({ errors, wide }));
})().catch((e) => { console.error(e); process.exit(1); });
