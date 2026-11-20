// Print kit/catalog.json from the kit's own name lists, so the catalogue never drifts from the code (specs/028 T006).
//   node my-styles/sketch-explainer/kit/tools/catalog.mjs > my-styles/sketch-explainer/kit/catalog.json
import { readFileSync } from 'node:fs';
globalThis.document = /** @type {any} */ ({});
const { CATALOG } = await import('../film.js');
const { DEFAULTS } = await import('../camera.js');
const ver = JSON.parse(readFileSync(new URL('../catalog.version.json', import.meta.url), 'utf8'));
const out = {
  version: ver.version,
  ...CATALOG,
  defaults: {
    line_weight: { value: '0.0052 × frame width for a person in a medium shot (12.5 character units)', evidence: 'EVIDENCE.md → visual report §Outlines 2' },
    camera: { ...DEFAULTS, evidence: 'EVIDENCE.md → Key numbers (push 33%, pull 23%, still 22%, push 3.3 %/s), proof frame round 3 (hold 0.3, drift)' },
    acting: { first_s: 0.15, gap_s: [2.0, 2.75], event_s: 1.25, evidence: 'EVIDENCE.md → in-frame motion 0.93, inner events 0.41/s' },
    set_saturation_max: { value: 0.15, evidence: 'EVIDENCE.md → saturation median 0.118' },
    shot_sizes: { med: 0.47, wide: 0.19, huge: 0.14, cu: 0.11, ecu: 0.03, inserts: 0.2, evidence: 'shots.json' },
  },
  hero_default: { hoodie: '#c9773f', hair: 'messy', hairCol: '#3a2a20' },
  avoid_hero: {},
};
console.log(JSON.stringify(out, null, 1));
