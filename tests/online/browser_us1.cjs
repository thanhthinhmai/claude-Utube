// Online US1 in a real browser (specs/007 T027, SC-001, SC-007). Called by test_us1.py; prints one JSON line.
// argv: base email password of a member the owner added (specs/008: no public sign-up). Exit 77 = no browser.
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, email, password] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const page = await browser.newPage({ viewport: { width: 360, height: 740 } });    // phone width
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  const t0 = Date.now();
  await page.goto(`${base}/#/`);
  await page.waitForSelector("text=Sign in to continue.");     // guests land on the login page
  if (await page.locator("text=Create an account").count()) errors.push("public sign-up link still shown");
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click("button[type=submit]");
  await page.waitForSelector("#acct >> text=films left this month");   // phone width: the account menu is in the top bar
  await page.click("text=Make a film");
  await page.waitForSelector(".pick label");
  await page.click(".pick label >> nth=0");
  await page.fill("#idea", "A small fox finds a lantern [slow 2]");
  await page.fill("#seconds", "20");
  await page.click("button[type=submit]");
  await page.waitForSelector("text=Current step");
  const tSubmit = Date.now();
  const wide = await page.evaluate(() => document.documentElement.scrollWidth);
  await page.waitForSelector("text=Render", { timeout: 60000 });
  const renderSeen = Date.now();
  await page.waitForSelector("text=Download the film", { timeout: 60000 });
  const href = await page.getAttribute("text=Download the film", "href");
  // Learn a style (US2): the rights box carries the constitution's wording; the upload form is one click away
  await page.goto(`${base}/#/learn`);
  await page.waitForSelector("text=I confirm that I have the right");
  await page.click("text=From my own videos");
  await page.waitForSelector("#files", { state: "visible" });
  if (await page.locator("video").count()) throw new Error("a <video> on the learn page");
  await browser.close();
  console.log(JSON.stringify({ order_ms: tSubmit - t0, render_seen: renderSeen / 1000, href, wide, errors }));
})().catch((e) => { console.error(e); process.exit(1); });
