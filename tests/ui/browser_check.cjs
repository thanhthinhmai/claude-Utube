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
  // Library (004): filter, search, state kept in the address, detail, Use this style
  const ctx = await browser.newContext({ permissions: ["clipboard-read", "clipboard-write"] });
  const lp = await ctx.newPage();
  lp.on("pageerror", (e) => errors.push(String(e)));
  await lp.goto(`${base}/#/library`);
  await lp.waitForSelector(".lib-card");
  const cards = async () => lp.locator(".lib-card").count();
  if ((await cards()) !== 2) throw new Error("library cards: " + (await cards()));
  await lp.click('.chip[data-g="Graphic & Type"]');
  if ((await cards()) !== 1) throw new Error("group filter");
  await lp.click('.chip[data-g=""]');
  await lp.fill("#lib-q", "deco");
  if ((await cards()) !== 1) throw new Error("search");
  await lp.reload();
  await lp.waitForSelector(".lib-card");
  if ((await cards()) !== 1 || (await lp.inputValue("#lib-q")) !== "deco") throw new Error("state not kept after reload");
  await lp.click(".lib-card h3");
  await lp.waitForSelector("text=Style rules");
  await lp.click("button.use");
  await lp.waitForSelector("text=Copied");
  const clip = await lp.evaluate(() => navigator.clipboard.readText());
  if (!clip.includes("Art Deco")) throw new Error("clipboard: " + clip);
  // clipboard blocked → the prompt is shown to copy by hand
  await lp.evaluate(() => { navigator.clipboard.writeText = () => Promise.reject(new Error("blocked")); });
  await lp.click("button.use");
  const box = await lp.inputValue(".prompt-box");
  if (!box.includes("Art Deco")) throw new Error("fallback box: " + box);
  // My styles: Use this style and a link to the base style in the Library
  await lp.goto(`${base}/#/styles/demo-style`);
  await lp.click('a[href="#/library/art-deco"]');
  await lp.waitForSelector("text=Style rules");
  await ctx.close();
  await browser.close();
  if (errors.length) throw new Error(errors.join("\n"));
  console.log("ok");
})().catch((e) => { console.error(e); process.exit(1); });
