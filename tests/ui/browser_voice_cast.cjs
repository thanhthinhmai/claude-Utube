// specs/036 T042: the Voice step of a film job page with speakers, in a real browser (quickstart §6).
//   node browser_voice_cast.cjs <base> <job id>   (exit 77 = no browser)
let pw;
try { pw = require("playwright-core"); } catch { process.exit(77); }
const [base, jid] = process.argv.slice(2);
(async () => {
  let browser;
  try { browser = await pw.chromium.launch(process.env.STUDIO_CHROME ? { executablePath: process.env.STUDIO_CHROME } : {}); }
  catch { process.exit(77); }
  const p = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
  const out = { errors: [] };
  p.on("pageerror", (e) => out.errors.push(String(e)));
  await p.goto(`${base}/#/jobs/${jid}`);
  await p.waitForSelector("#done-steps button[data-t='voice']", { timeout: 20000 });
  await p.click("#done-steps button[data-t='voice']");
  try { await p.waitForSelector(".edit-voice .vline", { timeout: 20000 }); }
  catch (e) { console.error((await p.locator("body").innerText()).slice(0, 800), out.errors); throw e; }
  out.speakers = await p.locator(".edit-voice .spk").evaluateAll((x) => x.map((r) => r.dataset.sp));
  out.groups = await p.locator(".edit-voice .spk[data-sp='narrator'] .spk-voice optgroup").evaluateAll((g) => g.map((x) => x.label));
  out.picker = await p.$eval("#v-voice", (x) => x.value);
  out.facts = await p.locator("#done-body .facts").innerText().catch(() => "");
  out.notApplied = await p.locator(".edit-voice .vline .tone >> text=not applied with this voice").count();
  out.tones = await p.locator(".edit-voice .vline .emo-in").count();
  const line = p.locator(".edit-voice .vline[data-id='L03']");
  await line.locator(".fx-in").selectOption("phone");
  await line.locator("[data-tone]").click();
  await p.waitForFunction(() => /voice-tone L03/.test(document.getElementById("job-log")?.textContent || ""), null, { timeout: 30000 })
    .then(() => { out.toneLogged = true; }, () => { out.toneLogged = false; });
  console.log(JSON.stringify(out));
  await browser.close();
})().catch((e) => { console.error(String(e)); process.exit(1); });
