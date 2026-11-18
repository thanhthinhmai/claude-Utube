// specs/025: opens a film job page in a real browser and reads the "Done so far" section. Called by test_done_so_far.py,
// and by hand with a screenshot folder: node browser_done.cjs <base> <job id> [shots dir]. Exit 77 = no browser.
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, jid, shots] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  const snap = async (name) => { if (shots) await page.screenshot({ path: `${shots}/${name}.png`, fullPage: true }); };
  const out = { errors };
  await page.goto(`${base}/#/jobs/${jid}`);
  await page.waitForSelector("#done-steps button", { timeout: 10000 });
  out.steps = await page.$$eval("#done-steps button", (bs) => bs.map((b) => ({
    text: b.textContent.trim(), state: b.className.replace("st-", ""), disabled: b.disabled })));
  out.script = await page.locator("#done-body .facts").innerText();
  out.excerpt = await page.locator("#done-body .script p").count();
  await snap("1-script");
  await page.click("[data-open='SCRIPT.md']");
  await page.waitForSelector("#done-more pre");
  out.fullScript = (await page.locator("#done-more").innerText()).length;
  await page.click("#done-steps button[data-t='voice']");
  await page.waitForSelector("table.lines");
  out.voice = await page.locator("#done-body .facts").innerText();
  out.voiceRows = await page.locator("table.lines tbody tr").count();
  await snap("2-voice");
  await page.click(".seg button[data-f='say']");
  out.respelledRows = await page.locator("table.lines tbody tr").count();
  out.readAs = await page.locator("table.lines .say").count();
  const t0 = Date.now();
  await page.click("table.lines .play:not([disabled])");
  out.playing = await page.waitForFunction(() => {
    const b = document.querySelector("table.lines .play.on"); return !!b;
  }, null, { timeout: 3000 }).then(() => Date.now() - t0).catch(() => null);
  await snap("3-respelled");
  if (await page.locator("#done-steps button[data-t='shots']:not([disabled])").count()) {
    await page.click("#done-steps button[data-t='shots']");
    await page.waitForSelector(".sheet-img");
    out.shots = await page.locator("#done-body .facts").innerText();
    out.sheetButtons = await page.locator("[data-s]").count();
    await snap("4-shots");
    await page.click("#done-mode button[data-m='grid']");
    out.thumbs = await page.locator(".thumb").count();
    await page.click(".thumb img");
    out.lightbox = await page.locator(".done-zoom").count();
    await page.click(".done-zoom");
    await snap("5-grid");
  }
  if (await page.locator("#done-steps button[data-t='mix']:not([disabled])").count()) {
    await page.click("#done-steps button[data-t='mix']");
    await page.waitForSelector("#done-body audio");
    out.mix = await page.locator("#done-body .facts").innerText();
    out.audio = await page.locator("#done-body audio").count();
  }
  if (await page.locator("#done-steps button[data-t='render']:not([disabled])").count()) {
    await page.click("#done-steps button[data-t='render']");
    await page.waitForSelector("#done-body .chunks");
    out.render = await page.locator("#done-body .facts").innerText();
    out.chunks = await page.locator(".chunks i").count();
    out.chunksDone = await page.locator(".chunks i.d").count();
    await snap("6-render");
  }
  await browser.close();
  console.log(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
