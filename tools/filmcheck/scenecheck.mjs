// @ts-check
// specs/026 R9: check a film's scene table (scenes.json) with the film's own kit (kit/plan.js check() and its
// catalogue), so the job page and the film page follow one set of rules.
//   node tools/filmcheck/scenecheck.mjs <film dir> [scenes file]   →   {"ok": true} | {"ok": false, "error": "S07: …"}
// The kit imports three.js only in film.js; plan.js is plain, so no browser and no resolve hook are needed.
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [dir, file] = process.argv.slice(2);
const say = (/** @type {any} */ o) => { process.stdout.write(JSON.stringify(o) + '\n'); process.exit(o.ok ? 0 : 1); };
if (!dir) say({ ok: false, error: 'usage: scenecheck.mjs <film dir> [scenes file]' });
const kit = path.join(dir, 'kit', 'plan.js');
if (!fs.existsSync(kit)) say({ ok: false, error: 'the film has no kit (kit/plan.js)' });
let doc;
try { doc = JSON.parse(fs.readFileSync(file || path.join(dir, 'scenes.json'), 'utf8')); }
catch (e) { say({ ok: false, error: `scenes.json cannot be read: ${/** @type {Error} */ (e).message}` }); }
if (!doc || typeof doc !== 'object' || !Array.isArray(doc.scenes)) say({ ok: false, error: 'scenes.json: {custom: [...], scenes: [...]}' });
const custom = Array.isArray(doc.custom) ? doc.custom : [];
for (const s of doc.scenes) {
  const m = typeof (s && s.set) === 'string' && /^custom:(.+)$/.exec(s.set);
  if (m && !custom.includes(m[1])) say({ ok: false, error: `${s.id}: custom set "${m[1]}" is not declared in scenes.json custom` });
}
try {
  const { check } = await import(pathToFileURL(kit).href);
  check(doc.scenes);
} catch (e) { say({ ok: false, error: String(/** @type {Error} */ (e).message || e) }); }
say({ ok: true, scenes: doc.scenes.length });
