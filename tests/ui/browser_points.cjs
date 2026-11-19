// specs/026 T057: the step rail and a paragraph edit on a film job page, in a real browser.
//   node browser_points.cjs <base> <job id>   (exit 77 = no browser)
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
  await p.waitForSelector("#rail-slot .rail button", { timeout: 20000 });
  await p.waitForSelector(".edit-script .para", { timeout: 20000 });
  out.steps = await p.locator("#rail-slot .rail button").count();
  out.gates = await p.locator("#rail-slot .gate").count();
  out.waiting = await p.locator("#rail-slot .rail-head .badge").innerText();
  await p.click(".edit-script .para[data-p='P03'] [data-edit]");
  out.lockedWhileEditing = await p.$eval("#approve", (x) => x.disabled);
  await p.fill(".edit-script .para[data-p='P03'] textarea", "By day three, you begin to see things that are not there.");
  await p.click(".edit-script .para[data-p='P03'] [data-check]");
  await p.waitForSelector(".edit-script .para[data-p='P03'] .pass, .edit-script .para[data-p='P03'] .fail", { timeout: 60000 });
  out.result = await p.locator(".edit-script .para[data-p='P03'] .row span").last().innerText();
  out.impact = await p.locator("#impact .chip").count();
  out.lockedAfter = await p.$eval("#approve", (x) => x.disabled);
  await p.waitForFunction(() => /Edit script-para P03/.test(document.getElementById("job-log")?.textContent || ""), null, { timeout: 15000 });
  out.logged = true;
  out.toggles = await p.locator("#point-toggles input").count();
  out.scriptLocked = await p.$eval("#point-toggles input[value='script']", (x) => x.disabled);   // waiting: locked
  await p.check("#point-toggles input[value='mix']");
  await p.waitForFunction(() => document.querySelectorAll("#rail-slot .gate").length === 3, null, { timeout: 15000 });
  out.gatesAfter = await p.locator("#rail-slot .gate").count();
  console.log(JSON.stringify(out));
  await browser.close();
})().catch((e) => { console.error(String(e)); process.exit(1); });
