// Mở trang Việc và trang Duyệt trong trình duyệt thật, bấm "Đồng ý". Gọi từ test_browser.py.
// Mã 77 = không có trình duyệt (bỏ qua test).
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
  if (!(await page.title()).includes("(1) chờ duyệt")) throw new Error("tab title: " + (await page.title()));
  await page.goto(`${base}/#/reviews/${rid}`);
  await page.click('#decide button[data-v="approve"]');
  await page.waitForSelector("text=Đã duyệt", { timeout: 5000 });
  await browser.close();
  if (errors.length) throw new Error(errors.join("\n"));
  console.log("ok");
})().catch((e) => { console.error(e); process.exit(1); });
