# HANDOFF 037-sound-per-shot (2026-11-26)

## Done
- Worktree `~/claude-Utube-037`, branch `037-sound-per-shot`, not pushed, no PR. Never commit `.specify/feature.json`.
- Commits: 73aca89 (US2 library, Freesound, proxy, Settings), 21d238d (US1 sound plan + mix, before 035), 3a69146 (US4 learn sfx).
- Uncommitted after 3a69146 (commit by name once T040 is scored): `tools/style-learn/sl/audioset.py` (PHRASES, NON_EFFECT,
  groups), `tools/style-learn/sl/sfxlearn.py` (two-level trust `agree()`, CLAP on phrases, `trust`/`n_sure` in summary,
  score overlap for silences), `tests/learn/test_sfxlearn.py` (16 OK), `specs/037-sound-per-shot/research.md` (R8 tuning),
  `data-model.md` (trust field).
- Sonniss: all 14 parts in `E:\SoundLibrary\Sonniss\GDC2024` (28 GB) + `GDC2026` (7.5 GB), zips deleted. Indexed into the
  real studio library (~/.local/share/claude-utube/sound): 956 sounds, 0 broken, 8.4 s (SC-007 data). Searches OK; no
  good "ball bounce" in the packs.
- `deps sound` installed into tools/.venv (symlink to main repo venv): torch 2.15 cpu, demucs 4.1, transformers 5.24;
  pip only added packages.

## In progress
- T040 real run on references/voice-check/a.wav with the two-level trust rule (background). Output:
  scratchpad `voicecheck.sfx.json`; layers cached in scratchpad `vc-stems/layers.npz` (sig `fx=dbo:`), word times in
  `voicecheck.sfx.words.json` (whisper). Rerun:
  `cd tools/style-learn && ../.venv/bin/python learn.py sfx --file ~/claude-Utube/references/voice-check/a.wav --words <scratch>/voicecheck.sfx.words.json --out <scratch>/voicecheck.sfx.json --stems <scratch>/vc-stems`
  then `sx.score(r, tests/learn/data/voicecheck_expect.json)`. Scratch = /tmp/claude-1000/-home-thinhmt-claude-Utube/c9dc545e-3243-4b74-8025-18de0bf17201/scratchpad
- Earlier scores: strict agree 0–1/5. Probe: CLAP phrases right on bubbles 0.74, basketball 0.94, crowd 0.96; AST right on
  glass ("Smash, crash" 0.18) but CLAP said coins → glass likely stays missed (CLAP veto).

## Next
1. Score T040; if ≥ 4/5 mark T040 [X]; else write the result honestly in quickstart "Kết quả" + R8. Commit named files.
2. T027/T051: real film plan on a copy of ae-sleepless-test (mix.py → music only), using the real Sonniss index.
3. ⟂035 tasks (T028–T031, T041–T048) wait for 035 merge + rebase.
4. T049, T050 (CLAUDE.md, tools/CLAUDE.md), T052 run all suites (tests/run.sh, render, learn, ui, filmcheck, online, ae),
   open PR (never merge). Then /speckit-converge.

## Tests last run
- learn 118 OK (before trust change; test_sfxlearn 16 OK after); filmcheck test_soundplan OK; full filmcheck 392 OK,
  online 246 OK (earlier this session).

## Traps
- `pkill -f <pattern>` kills our own shell when the pattern is in the command line (exit 144): use pgrep + kill <pid>.
- downloads.sonniss.com and the .torrent files are behind Cloudflare: browser only (the user downloaded them).
- transformers 5: CLAP get_*_features return an object (`pooler_output`), processor arg is `audio=`; wrap in no_grad.
- segs.json of voice-check is sentence-level: `learn sfx --file` re-transcribes to word times automatically.
- Style template lives at `my-styles/<s>/template.json` (not kit/); sound plan reads film `kit/template.json` or
  `film.json → style`.

## User decisions (this session)
- Two-level trust for learn sfx ("Hai mức tin"): sure / likely, both in the style rules with trust marked.
- Sonniss: user downloaded in the browser to E:\SoundLibrary\Sonniss; Claude unzips and deletes zips.
