// Every on-screen text of a film, for the missing-glyph check (specs/010 R7). Uses the library's page helper the
// same way core/render/readcheck.mjs does; nothing in the library is changed.
//   node tools/filmcheck/texts.mjs <film dir> <lib dir> [--step 0.25]
// Prints {"texts": [..unique strings..]} or {"texts": null} when the page has no window.TEXTS.
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [dir, lib] = process.argv.slice(2);
const i = process.argv.indexOf('--step');
const STEP = i > 0 ? +process.argv[i + 1] : 0.25;
const page_ = await import(pathToFileURL(path.join(lib, 'core/render/page.mjs')).href);
page_.requireDemo(dir);
const { browser, page } = await page_.openDemo(dir, { w: 1920, h: 1080 });
const res = await page.evaluate(({ STEP }) => {
  if (typeof window.TEXTS !== 'function' || !(window.DUR > 0)) return null;
  const seen = new Set();
  for (let t = 0; t <= window.DUR; t += STEP) {
    window.render(t);
    for (const b of window.TEXTS(t) || []) if (b && b.text) seen.add(String(b.text));
  }
  return [...seen];
}, { STEP });
await browser.close();
page_.closeServer();
console.log(JSON.stringify({ texts: res }));
