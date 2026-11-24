// Settings → Usage tiles and charts in a real browser (specs/033 T002). Called by test_admin.py.
// argv: base email password expectJSON. Prints one JSON line {errors, info}. Exit 77 = no browser.
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, email, password, expectJson] = process.argv.slice(2);
const want = JSON.parse(expectJson);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const errors = [], info = {};
  const check = (ok, what) => { if (!ok) errors.push(what); };
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, colorScheme: process.env.DARK ? "dark" : "light" });
  page.on("pageerror", (e) => errors.push("pageerror " + String(e)));
  page.on("console", (m) => { if (m.type() === "error" && !/status of 40[134]/.test(m.text())) errors.push("console " + m.text()); });
  await page.goto(`${base}/#/login`);
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click("button[type=submit]");
  await page.waitForSelector("text=films left this month");
  await page.goto(`${base}/#/settings/usage`);
  await page.waitForSelector(".tiles .tile");
  const tiles = await page.$$eval(".tile", (ts) => ts.map((t) => t.textContent.replace(/\s+/g, " ").trim()));
  info.tiles = tiles;
  check(tiles.length === 3, "3 tiles");
  want.tiles.forEach((w, i) => check(tiles[i] && tiles[i].includes(w), `tile ${i} has ${w}: ${tiles[i]}`));
  const cols = async () => page.$$eval("#ch-usage .col", (c) => c.length);
  check(await page.$$eval(".chart", (c) => c.length) === 1, "one chart");
  check(await cols() === 30, "30 columns by default");
  check((await page.textContent("#ch-usage .section-title")) === "Requests per day", "requests by default");
  const legendCalls = await page.$eval("#ch-usage .legend", (l) => l.textContent.replace(/\s+/g, " "));
  info.legendCalls = legendCalls;
  check(legendCalls.includes("Claude 3") && legendCalls.includes("API key 1"), "legend counts requests");
  await page.hover("#ch-usage .col[data-i='29']");                  // tip on today's column
  const tip = await page.$eval("#ch-usage .chart-tip", (t) => (t.hidden ? "" : t.textContent));
  info.tip = tip;
  check(/Total\s*3/.test(tip), "tip shows today's total 3");
  // the same chart switched to tokens, in place
  await page.click("#ch-usage [data-metric='tokens']");
  await page.waitForFunction(() => document.querySelector("#ch-usage .section-title").textContent === "Tokens per day");
  check(page.url().includes("metric=tokens"), "kind in address");
  check(await page.$$eval(".chart", (c) => c.length) === 1, "still one chart");
  const legend = await page.$eval("#ch-usage .legend", (l) => l.textContent.replace(/\s+/g, " "));
  info.legend = legend;
  want.legend.forEach((w) => check(legend.includes(w), `legend has ${w}`));
  await page.click("#ch-usage [data-table]");
  const tbl = await page.$eval("#ch-usage .table-wrap", (t) => (t.hidden ? "" : t.querySelector("tr:nth-child(2)").textContent.replace(/\s+/g, " ")));
  info.table = tbl;
  check(tbl.includes("3,500"), "table first row (today) total 3,500 tokens");
  // 7 days keeps the kind; a reload keeps both
  await page.click("[data-range='7']");
  await page.waitForFunction(() => document.querySelectorAll("#ch-usage .col").length === 7);
  check(page.url().includes("range=7") && page.url().includes("metric=tokens"), "range and kind in address");
  await page.reload();
  await page.waitForSelector("#ch-usage .col");
  check((await page.textContent("#ch-usage .section-title")) === "Tokens per day" && await cols() === 7, "reload keeps range and kind");
  const lead = await page.$$eval("p.lead", (ps) => ps.map((x) => x.textContent).join(" | "));
  info.lead = lead;
  check(lead.includes("Last 7 days: 4 Claude calls"), "totals follow the range");
  // a wrong custom range
  await page.fill("#use-from", "2026-11-10");
  await page.fill("#use-to", "2026-11-01");
  await page.click("#use-apply");
  check((await page.textContent("#use-msg")).includes("on or before"), "bad range message");
  // phone width
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(300);
  const w = await page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
  info.width = w;
  check(w[0] <= w[1], `no sideways scroll at 390px (${w})`);
  if (process.env.SHOT) { await page.setViewportSize({ width: 1280, height: 900 }); await page.goto(`${base}/#/settings/usage`); await page.waitForSelector(".tile"); await page.screenshot({ path: process.env.SHOT, fullPage: true }); }
  await browser.close();
  console.log(JSON.stringify({ errors, info }));
})();
