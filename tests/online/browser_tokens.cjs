// Your account → API tokens in a real browser, phone width (specs/009 T015). argv: base email password.
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, email, password] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const ctx = await browser.newContext({ viewport: { width: 360, height: 740 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("dialog", (d) => d.accept());
  await page.goto(`${base}/#/login`);
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click("button[type=submit]");
  await page.waitForSelector("#acct summary.user-btn");
  await page.goto(`${base}/#/account`);
  await page.waitForSelector("text=No tokens yet.");
  if (await page.locator("#tok-role").count()) errors.push("a member sees the Owner role choice");
  await page.click("#tok-new");
  await page.fill("#tok-name", "laptop");
  await page.selectOption("#tok-exp", "never");
  await page.waitForSelector("#tok-never:not([hidden])");
  await page.click("#tok-form button[type=submit]");
  await page.waitForSelector("text=Copy it now: it is shown only this once.");
  const secret = (await page.textContent("#tok-value")).trim();
  for (const label of ["Copy token", "Copy MCP command", "Copy for an agent"]) await page.waitForSelector(`text=${label}`);
  await page.waitForSelector(".tokens >> text=laptop");
  await page.waitForSelector(".tokens >> text=never ends");
  await page.click("summary >> text=For agents");
  await page.waitForSelector("text=claude mcp add --transport http film-studio");
  const wide = await page.evaluate(() => document.documentElement.scrollWidth);
  await page.reload();
  await page.waitForSelector(".tokens >> text=laptop");
  const shownAgain = (await page.content()).includes(secret);
  await page.click(".tokens details.menu summary");
  await page.click(".tokens button[data-act=revoke]");
  await page.waitForSelector(".tokens >> text=Revoked");
  await browser.close();
  console.log(JSON.stringify({ errors, wide, secret, shownAgain }));
})().catch((e) => { console.error(e); process.exit(1); });
