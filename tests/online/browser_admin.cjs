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
  await page.waitForSelector("#acct >> text=films left this month");   // phone width: the account menu is in the top bar
  await page.goto(`${base}/#/admin`);                       // the old address opens Settings → General
  await page.waitForSelector("text=Save settings");
  if (await page.locator("text=Sign-up open").count()) errors.push("sign-up setting still shown");
  await page.fill("#s-quota_films_default", "3");
  await page.click("text=Save settings");
  await page.waitForSelector("#msg >> text=Saved.");
  await page.click(".tabs >> text=Usage");
  const row = page.locator("tr", { hasText: "cust@example.com" });
  await row.locator('input[data-f="quota_films"]').fill("7");
  await row.locator('input[data-f="quota_films"]').press("Tab");
  await page.waitForSelector("#acc-msg >> text=Saved.");
  await page.click(".tabs >> text=Users");
  const user = page.locator(".users li", { hasText: "cust@example.com" });
  await user.locator("summary").click();
  await user.locator("button[data-act=toggle]").click();
  await page.waitForSelector('.users li:has-text("cust@example.com") >> text=Off');
  await page.click("#add-user");
  await page.fill("#u-email", "new@example.com");
  await page.fill("#u-password", "another good password");
  await page.click("#user-form button[type=submit]");
  await page.waitForSelector("text=Added new@example.com. Give them the password.");
  await page.waitForSelector('.users li:has-text("new@example.com") >> text=Member');
  const added = page.locator(".users li", { hasText: "new@example.com" });
  await added.locator("summary").click();
  await added.locator("button[data-act=role]").click();          // Make owner (the dialog is accepted)
  await page.waitForSelector('.users li:has-text("new@example.com") >> text=Owner');
  await page.locator(".users li", { hasText: "new@example.com" }).locator("summary").click();
  await page.locator(".users li", { hasText: "new@example.com" }).locator("button[data-act=remove]").click();
  await page.waitForSelector('.users li:has-text("new@example.com")', { state: "detached" });
  const wide = await page.evaluate(() => document.documentElement.scrollWidth);
  await browser.close();
  console.log(JSON.stringify({ errors, wide }));
})().catch((e) => { console.error(e); process.exit(1); });
