# Tasks: 041 After Effects builds in batches

- [X] T001 Test: fake AE, 7 shots, batch 3 → 3 runs, joined master, contiguous marks, merged keys (tests/ae/test_ae.py)
- [X] T002 `settings()` reads `batchShots` (ae.json, STUDIO_AE_BATCH, 30) (tools/ae/local.py)
- [X] T003 `build()` batches above the size, joins masters by copy, offsets marks (tools/ae/local.py)
- [X] T004 `ae status` shows the batch size (tools/ae/cli.py)
- [X] T005 Docs: tools/CLAUDE.md AE section, film-make skill note
- [X] T006 Run all 8 test suites
