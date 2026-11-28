# Plan: After Effects builds in batches (041, Light)

- `tools/ae/local.py`: `settings()` adds `batchShots` (ae.json → env `STUDIO_AE_BATCH` → 30). `build()` resolves the
  shot list (film.json `shots` when None); above the batch size it calls the current single build (`_build_one`)
  per batch, then `_join(parts, folder)` with `ffmpeg -f concat -c copy` into `<work>/<rid>-joined/master.mp4`.
  Marks `[t0, t1, …]` offset by the summed batch `duration`; keys merged; checks appended; log joined.
- `tools/ae/cli.py` `ae status`: print the batch size.
- Test: `tests/ae/test_ae.py` fake AE, 7 shots, `batchShots` 3.
- Constitution: no `lib/` change; AE stays open between runs (the same `run_folder`); no new dependency.
