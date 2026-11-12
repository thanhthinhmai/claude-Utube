// @ts-check
// The film's plan, read from its page without drawing frames (specs/020 T014, research R4, contracts/film-page.md).
// Uses the library's page helper like texts.mjs; nothing in the library is changed.
//   node tools/filmcheck/plan.mjs <film dir> <lib dir>
// Prints one JSON line {dur, shots, cues, cards}: shots [[t0, t1, set, id]], cues [[t0, t1, text]],
// cards [[t0, t1, id, text]]; a value the page does not export is null.
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [dir, lib] = process.argv.slice(2);
const P = await import(pathToFileURL(path.join(lib, 'core/render/page.mjs')).href);
P.requireDemo(dir);
const { browser, page } = await P.openDemo(dir, { w: 1920, h: 1080 });
const res = await page.evaluate(() => {
  const w = /** @type {any} */ (window);
  const arr = (/** @type {any} */ v) => (Array.isArray(v) ? v : null);
  return { dur: typeof w.DUR === 'number' ? w.DUR : null, shots: arr(w.SHOTS), cues: arr(w.CUES), cards: arr(w.CARDS) };
});
await browser.close();
P.closeServer();
console.log(JSON.stringify(res));
