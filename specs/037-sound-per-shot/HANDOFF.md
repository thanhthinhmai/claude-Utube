# HANDOFF 037-sound-per-shot (2026-11-26)

## Done
- Worktree `~/claude-Utube-037`, branch `037-sound-per-shot`. Never commit `.specify/feature.json`.
- Commits: 73aca89 (US2 library, Freesound, proxy, Settings), 21d238d (US1 sound plan + mix), 3a69146 (US4 learn sfx),
  86ac89d (direction A: style `actions` = sure only, likely → `hints`; `sound shot on|off`; silences start at the word end;
  Freesound asked when < 3 strong local hits).
- Last batch (T027, T049–T051, T055): `tests/filmcheck/test_no_media.py` (SC-005), CLAUDE.md + tools/CLAUDE.md sections,
  SC-007 in quickstart (956 files: full index 31.3 s ≈ 5.5 min / 10,000; re-index 2.0 s), real film moved over,
  soundmix loudness (one gain from voice + music to −14 LUFS, true-peak limiter −2.5 dBTP; was −19 LUFS / +0.8 dBTP).
- Real film `~/claude-Utube/films/ae-sleepless-test` (outside git): `mix.py` is music only (old one `mix.py.orig`),
  `sound/plan.json` 9 Sonniss cues + 1 silence, `animatic/keys.json` by hand; backups of render.mp4, mix.wav, audio.m4a,
  the final mp4 and CREDITS in `pre037/`. Final film now −13.6 LUFS, true peak −2.3 dB.
- Picture-matched CC0 scoring of learn sfx: ~1.5/9; voice-check 3/5. SC-003 (5/5) not met, written in R8 and quickstart;
  the user chose direction A (Claude picks sounds by the picture; the user reviews per shot).

## Sound review before 035 (branch `037-sound-review`, worktree `~/claude-Utube-037b`, from 037-sound-per-shot)
- `soundnotes.py` + `sound notes …`; edit ops `cue-set|cue-rm|cue-add|shot-set|sound-note-add|sound-note-delete`;
  `sound` block in steps; Sound panel (Mix tab + film page); `/films/{film}/sound…` routes; fix job target sound
  (agent prompt, worker finish/merge); soundmix writes `<film>.mp4` via temp file (hard link trap, T057).
- Tests: `tests/filmcheck/test_soundnotes.py`, `tests/ui/test_sound_api.py` + `browser_sound.cjs`,
  `tests/online/test_sound_fix_job.py`. Tasks T041–T045, T047, T057 [X]; T046 partly; T056 (after 035) added.

## Next
1. PR #46 open (all 8 suites passed at 2ece081). Never merge it.
2. ⟂035: T028–T031, T046 rest, T048, T056 wait for 035 to merge; then rebase 037-sound-review and wire the animatic gate.
3. /speckit-converge.

## Traps
- A fix job's work copy hard-links the customer's `.mp4` files: never write them in place.
- Test AE films need `ae/shots.jsx` or `points.is_ae` is False (film.json fails to load).
- `sound … --dir` is the film folder itself, not its parent.
- `sound mix` remuxes `out/render.mp4` and `<film>.mp4`: back them up on a real film first.
- AAC adds ~1 dB true peak over the WAV: hence the −2.5 dBTP ceiling.
- Never feed audio containing Sonniss sounds to any model (AST/CLAP/Demucs/Whisper), test mixes included (FR-013b).
- `pkill -f <pattern>` kills our own shell when the pattern is in the command line: use pgrep + kill <pid>.
- transformers 5: CLAP features return an object (`pooler_output`), processor arg is `audio=`.
- Freesound key: `FREESOUND_API_KEY` in the worktree's own `.env` (never print it).

## User decisions
- Two-level trust (sure/likely); direction A; per-shot sound on/off; Sonniss-AI test results deleted.
- Freesound calls approved for the CC0 test and gap filling.
