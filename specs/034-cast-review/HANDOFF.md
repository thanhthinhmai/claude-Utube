# HANDOFF 034-cast-review (2026-11-25, from session 217a72f1 to claude-utube-82)

## Done
- Branch `034-cast-review`, worktree `/home/thinhmt/claude-Utube-034`, 8 commits (latest fd5dad6), clean tree, not pushed, no PR. 52/54 tasks.
- Tests after US4: run.sh 87/87; ae 34 OK; ui 83 OK + 44/44 browser; filmcheck 308 with 1 flaky `test_tiers.test_fingerprint` (mtime cache, pre-existing, passes alone 2/3); online: still running in session e2 (one "ERROR: Exception in ASGI application" line in log, unknown).

## Open
- T053: run the 5 suites, mark [X].
- T054 quickstart with real AE: §2 done (`ae sheet ae-sleepless-test --dir …/films/ae-sleepless-test`: 20 pictures in 30 s, SC-001; checked by eye). §3 notes → "Send notes to Claude" (needs app + a Claude fix job: ask the user first). §4 approve --save + cast use (needs `app start`, writes the real library ~/.local/share/claude-utube: ask first). §5 needs a temp rig ball@2 (covered by test_rigs).
- Then /speckit-converge, open PR (never merge), tell claude-utube-6f (035) the PR is open: 6f rebases and splits pins.py out of castnotes.py.

## Traps
- `ae sheet` with a full path says "bad film name": use the film name + `--dir`.
- Cut frames by frame index, not -ss (fixed in fd5dad6).
- actions.command puts key=value pairs before options (argparse drops pairs after --text-file).
- Test POSTs need json={} or 403 csrf.
- sqlite3.Row has no .get: use a["email"].
- Browser at 400 px: account menu hidden, wait with {state: "attached"}.
- Test film films/ae-sleepless-test now uses CU.char/CU.rig("ball@1") with cast/cast.json (hero, friend, classmates×4); old version in ae.pre034/ and film.pre034.json.

## User decisions
- Worktree and implement approved; clarify answers B, A, B, B. Animatic moved to 035; Cast library only in the app.
- Merge order agreed with 035: 034 → 036 → 035. 036 does not touch steps.py, points.py, castnotes.py.
