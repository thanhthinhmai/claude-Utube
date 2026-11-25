# The cast of an After Effects film (specs/034)

`films/<film>/cast/cast.json`, written by Claude after the script is approved, before the voice:

```json
{"version": 1, "channel": "<channel or null>", "save_to_library": true,
 "characters": [
  {"id": "hero", "name": "You (hero)", "role": "hero", "kind": "one", "rig": "ball@1",
   "spec": {"hoodie": "#e8604c", "pants": "#262a3d", "shoes": "#f4f2ee", "headColor": "#141418",
            "hat": {"kind": "beanie", "color": "#4f7a4a"}, "stripe": null, "tie": null, "hood": true, "brows": false},
   "needs": {"expressions": [{"key": "wide", "label": "Wide-eyed", "para": "P01"}],
             "poses": [{"key": "guitar", "label": "Guitar", "para": "P02"}], "walk": true},
   "from_library": null, "approved": null},
  {"id": "classmates", "name": "Classmates ×2", "role": "background", "kind": "group", "rig": "ball@1",
   "members": [{"hoodie": "#4f7fc8"}, {"hoodie": "#c8a24f", "scale": 0.9}],
   "needs": {"expressions": [], "poses": [], "walk": false}, "from_library": null, "approved": null}]}
```

- `id` `[a-z0-9-]{1,32}`, unique; `name` ≤ 40; `role` hero | support | background; at most 10 characters.
- `kind` one (with `spec`) or group (with 2–8 `members`, each a spec).
- `rig`: a version listed by `sh bin/studio ae rigs` (locked in `tools/ae/rigs.lock`).
- spec keys: `hoodie`, `pants`, `shoes`, `headColor`, `rimColor` (#rrggbb), `hat` `{kind: beanie|cap|curly|puffs|bun|none, color}`,
  `stripe`, `tie` (#rrggbb or null), `hood` (bool), `brows` (false | true | "angry" | "worried"), `scale` (0.6–1.4).
- `needs`: only what this script asks for, each with its paragraph id. Keys come from the rig's catalog
  (`tools/ae/kit/rigs/<family>/v<N>/catalog.json`); a key outside it stays "No picture yet" on the sheet.
- `approved` is written by `cast approve` or the job page, never by hand.

Commands: `cast check <film>` · `ae sheet <film> [--only id,id]` (exit 3: After Effects not ready) ·
`cast status <film>` · `cast approve <film> (<id>…|--all) --source chat` (only after the user approved in the chat).
In shots, draw a character with `CU.char("<id>", {dur, view, keys, walk, …})`.
