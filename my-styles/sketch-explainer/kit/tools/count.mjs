// Count a film's shot sizes, runs, sets and moves from its page (specs/028 T020, SC-003).
//   node my-styles/sketch-explainer/kit/tools/count.mjs <film dir> <lib dir> [--json]
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const [dir, lib, flag] = process.argv.slice(2);
const P = await import(pathToFileURL(path.join(lib, 'core/render/page.mjs')).href);
const { browser, page } = await P.openDemo(dir, { w: 960, h: 540 });
const info = await page.evaluate(() => /** @type {any} */ (window).SCENE_INFO || []);
await browser.close(); P.closeServer();
const shots = info.filter(s => s.size !== 'card'), n = shots.length;
const share = {}; for (const s of shots) share[s.size] = (share[s.size] || 0) + 1;
let run = 1, worst = n ? 1 : 0, changes = 0;
for (let i = 1; i < n; i++) { if (shots[i].size === shots[i - 1].size) { run++; worst = Math.max(worst, run); } else { run = 1; changes++; } }
const moves = {}; for (const s of shots) moves[s.move] = (moves[s.move] || 0) + 1;
const out = { shots: n, sizes: Object.fromEntries(Object.entries(share).map(([k, v]) => [k, +(v / n).toFixed(3)])), medium: +((share.med || 0) / n).toFixed(3),
  longest_same_size: worst, size_change_share: n > 1 ? +(changes / (n - 1)).toFixed(3) : 0, sets: new Set(shots.map(s => s.set)).size,
  moves: Object.fromEntries(Object.entries(moves).map(([k, v]) => [k, +(v / n).toFixed(3)])), dur: +info.reduce((a, s) => a + s.dur, 0).toFixed(2) };
if (flag === '--json') console.log(JSON.stringify(out));
else {
  console.log(`${out.shots} shots · ${out.dur} s · medium ${(out.medium * 100).toFixed(0)}% · longest same size ${out.longest_same_size} · size changes ${(out.size_change_share * 100).toFixed(0)}% · ${out.sets} sets`);
  console.log('sizes', out.sizes, 'moves', out.moves);
  const ok = out.medium >= 0.4 && out.medium <= 0.55 && out.longest_same_size <= 4;
  console.log(ok ? '✓ within the measured shot grammar (SC-003: 40–55% medium, ≤ 4 in a row)' : '✗ outside the measured shot grammar');
}
