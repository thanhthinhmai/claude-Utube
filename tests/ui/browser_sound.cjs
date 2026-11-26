// specs/037 US3: the Sound panel of an AE film job page (Mix tab) and of the finished film page, in a real browser.
//   node browser_sound.cjs <base> <job id> <film>   (exit 77 = no browser)
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, jid, film] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const p = await browser.newPage({ viewport: { width: 400, height: 1000 } });
  const out = { errors: [] };
  p.on("pageerror", (e) => out.errors.push(String(e)));
  await p.goto(`${base}/#/jobs/${jid}`);
  await p.waitForSelector("#done-steps button[data-t='mix']", { timeout: 20000 });
  await p.click("#done-steps button[data-t='mix']");
  try { await p.waitForSelector("#sound-panel .sound-shot", { timeout: 20000 }); }
  catch (e) { console.error((await p.locator("body").innerText()).slice(0, 800), out.errors); throw e; }
  out.shots = await p.locator("#sound-panel .sound-shot").evaluateAll((x) => x.map((s) => s.dataset.shot));
  out.cues = await p.locator("#sound-panel .sound-cue").count();
  out.wide = await p.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  out.strip = { shots: await p.locator("#sound-panel .tl .sh").count(), fx: await p.locator("#sound-panel .tl .fx").count() };
  out.impact = await p.locator("#sound-panel .sound-impact").innerText().catch(() => "");
  // "Add a sound": search the library and listen before using a hit; ▶ turns into ■ while it plays
  await p.click("#sound-panel .sound-shot[data-shot='S1'] .sound-add summary");
  await p.fill("#sound-panel input[data-q='S1']", "glass break");
  await p.press("#sound-panel input[data-q='S1']", "Enter");
  await p.waitForSelector("#sound-panel [data-hits='S1'] button[data-huse]", { timeout: 20000 }).catch(() => {});
  out.hits = await p.locator("#sound-panel [data-hits='S1'] button[data-huse]").count();
  if (!out.hits) out.hitsText = await p.locator("#sound-panel [data-hits='S1']").innerText().catch((e) => String(e));
  const pre = p.locator("#sound-panel [data-hits='S1'] button[data-hpre]").first();
  if (out.hits) {
    await pre.click(); out.preOn = await pre.innerText();
    await pre.click(); out.preOff = await pre.innerText();
  }
  const play = p.locator("#sound-panel button[data-play='S1']");
  await play.click();
  out.playOn = await p.waitForFunction(() => document.querySelector("#sound-panel button[data-play='S1']").textContent === "■ Stop",
    null, { timeout: 5000 }).then(() => true, () => false);
  if (out.playOn) {
    await play.click();
    await p.waitForFunction(() => document.querySelector("#sound-panel button[data-play='S1']").textContent === "▶ Play", null, { timeout: 3000 }).catch(() => {});
    out.playOff = await play.innerText();
  }
  await p.fill("#sound-panel input[data-note='S2']", "The crash is late");
  await p.click("#sound-panel button[data-nadd='S2']");
  await p.waitForSelector("#send-sound-notes", { timeout: 30000 }).then(() => { out.send = true; }, () => { out.send = false; });
  out.sendText = out.send ? await p.locator("#send-sound-notes").innerText() : "";
  out.approveDisabled = await p.locator(".approve-bar #approve").isDisabled().catch(() => null);
  out.noteShown = await p.locator("#sound-panel .sound-shot[data-shot='S2'] .sound-note").count();
  await p.goto(`${base}/#/films/${film}`);
  await p.waitForSelector("#sound-slot .sound-shot", { timeout: 20000 }).catch(() => {});
  out.filmShots = await p.locator("#sound-slot .sound-shot").count();
  out.filmNotes = await p.locator("#sound-slot .sound-note").count();
  out.filmEdits = await p.locator("#sound-slot button[data-rm]").count();
  console.log(JSON.stringify(out));
  await browser.close();
})().catch((e) => { console.error(String(e)); process.exit(1); });
