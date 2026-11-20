// Screenshot a model sheet page (specs/028 T025): node sheet.mjs <page dir> <lib dir> <out.jpg>
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [dir, lib, out] = process.argv.slice(2);
const P = await import(pathToFileURL(path.join(lib, 'core/render/page.mjs')).href);
const { browser, page } = await P.openDemo(dir, { w: 1920, h: 1080 });
await page.waitForTimeout(800);
await page.evaluate(() => window.render(0.5));
await page.screenshot({ path: out, type: 'jpeg', quality: 88 });
await browser.close(); P.closeServer();
