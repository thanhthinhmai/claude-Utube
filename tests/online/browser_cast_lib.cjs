// specs/034 T050: the Cast page of the app (the channel's cast), a preview with a newer rig, Update, Approve.
//   node browser_cast_lib.cjs <base> <email> <password> [screenshot prefix]   (exit 77 = no browser)
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, email, password, shot] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const out = { errors: [] };
  for (const width of [1280, 400]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    page.on("pageerror", (e) => out.errors.push(String(e)));
    await page.goto(`${base}/#/login`);
    await page.fill("#email", email);
    await page.fill("#password", password);
    await page.click("button[type=submit]");
    await page.waitForSelector("#acct summary.user-btn", { state: "attached" });
    await page.goto(`${base}/#/cast`);
    await page.waitForSelector(".cast-lib .card");
    out[`cards${width}`] = await page.locator(".cast-lib .card").count();
    out[`chips${width}`] = await page.locator(".cast-lib .card .chip").allTextContents();
    if (width === 1280) {
      if (shot) await page.screenshot({ path: `${shot}-list.png`, fullPage: true });
      await page.click(".cast-lib .card");
      await page.waitForSelector(".lib-compare");
      out.compare = await page.locator(".lib-compare h2").allTextContents();
      if (shot) await page.screenshot({ path: `${shot}-preview.png`, fullPage: true });
      await page.click("#lib-update");
      await page.waitForSelector("#lib-approve");
      out.afterUpdate = await page.locator(".lib-compare h2").allTextContents();
      await page.click("#lib-approve");
      await page.waitForSelector(".lib-compare", { state: "detached" });
      out.head = (await page.locator("p.lead").textContent()).trim();
    } else {
      await page.click(".cast-lib .card");
      await page.waitForSelector(".notebox");
      out.scroll400 = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      if (shot) await page.screenshot({ path: `${shot}-400.png`, fullPage: true });
    }
    await page.close();
  }
  console.log(JSON.stringify(out));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
