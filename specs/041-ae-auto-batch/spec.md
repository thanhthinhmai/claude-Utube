# Feature Specification: After Effects builds in batches

**Feature Branch**: `041-ae-auto-batch` · **Created**: 2026-11-28 · **Status**: Draft · **Level**: Light

## User Scenarios & Testing

### User Story 1 - A long film builds without running out of memory (Priority: P1)

A 163-shot After Effects film (8.7 min) built as one project needed about 15 GB of RAM on a 16 GB machine. After
Effects paged and stalled at the MASTER assembly for over two hours. Built by hand in batches of 30 shots, the same
draft took 23–30 min. Every long AE build (`ae build`, `ae render`, `ae draft`, `ae fix` with many shots) should split
itself into batches, join the batch videos, and hand back one result, as if it were one project.

**Independent Test**: build a fake-AE film of 7 shots with a batch size of 3: three AE runs, one joined `master.mp4`
whose length is the sum of the batches, and marks that follow on from batch to batch.

**Acceptance Scenarios**:

1. **Given** a film with more shots than the batch size, **When** the shots are built, **Then** After Effects runs
   once per batch, and the result has one master video, every shot's mark (offset by the earlier batches), all
   keys and checks.
2. **Given** a build with no more shots than the batch size, **When** it runs, **Then** nothing changes from today
   (one run, same result).
3. **Given** a batch fails, **When** the build stops, **Then** the error is the same `AeError` as today.

### Edge Cases

- Batch size 0 or missing: the default (30). `ae.json → batchShots` or `STUDIO_AE_BATCH` sets it.
- Blender shots and cast layers keep their own paths (only `local.build` batches).

## Requirements

- **FR-001**: `local.build` splits the shot list into batches of `batchShots` (default 30) when there are more shots.
- **FR-002**: The batch videos are joined without a new encode; marks are offset by the length of the earlier
  batches; keys and checks are merged; `duration` is the total.
- **FR-003**: The batch size is read from `ae.json → batchShots`, else `STUDIO_AE_BATCH`, else 30, and shown by
  `ae status`.
- **FR-004**: A build at or under the batch size is unchanged.

## Success Criteria

- **SC-001**: The fake-AE test of 7 shots in batches of 3 passes: 3 runs, joined length = sum, marks contiguous.
- **SC-002**: All 8 test suites pass.
- **SC-003**: The lie-sense final render (163 shots) completes in batches without an `ae_stalled` stop.

## Assumptions

- The batch masters share codec settings (one render template), so the concat demuxer can join them by copy.
