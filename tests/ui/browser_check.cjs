// Opens the Jobs and Review pages in a real browser and clicks "Approve". Called by test_browser.py.
// Exit 77 = no browser (test is skipped).
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, jid, rid] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(`${base}/#/`);
  try { await page.waitForSelector(".job", { timeout: 5000 }); } catch (e) { throw new Error("no job card: " + (await page.content()).slice(0, 1500)); }
  if (!(await page.title()).includes("(1) to review")) throw new Error("tab title: " + (await page.title()));
  await page.goto(`${base}/#/reviews/${rid}`);
  await page.click('#decide button[data-v="approve"]');
  await page.waitForSelector("text=Decided:", { timeout: 5000 });
  await browser.close();
  if (errors.length) throw new Error(errors.join("\n"));
  console.log("ok");
})().catch((e) => { console.error(e); process.exit(1); });
