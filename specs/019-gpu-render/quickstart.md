# Quickstart: validate 019-gpu-render

Reference machine: the WSL2 machine of research.md (Intel UHD 730). Commands from the repo root.

## 0. Automated tests (any machine, no GPU needed)

```sh
sh tests/render/run.sh        # wrapper flags, probe decisions, fingerprint, chunk resume, GPU-loss fallback (software browser)
sh tests/run.sh               # status / deps / config cases
sh tests/filmcheck/run.sh && sh tests/ui/run.sh
```

## 1. Detection and status (US1, SC-006)

```sh
sh bin/studio status                      # expect: ✓ dựng hình   GPU · ANGLE (… D3D12 (Intel(R) UHD Graphics 730) …)
DISPLAY= sh bin/studio status             # expect: · dựng hình   phần mềm · không có màn hình đồ hoạ
PLAYWRIGHT_BROWSERS_PATH=/tmp/empty sh bin/studio status   # expect: ✗ … thiếu Chromium đầy đủ → sh bin/studio deps gpu
sh bin/studio config render software && sh bin/studio status   # expect: · … phần mềm · do cấu hình
sh bin/studio config render auto
```
Each `status` returns in ≤ 30 s (`time`).

## 2. Record a long film with the GPU (US1, SC-001)

```sh
time sh bin/studio render pet-swap --fps 30
ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 films/pet-swap/out/video.mp4   # 17153
head -1 films/pet-swap/out/render.log     # render: gpu · ANGLE (…) · 17153 frames · …
```
Pass: ≤ 40 min, 17,153 frames. (`pet-swap` keeps its own `render_gpu.mjs`; this run only measures the studio command.)

## 3. Checks use the GPU (US2, SC-002)

```sh
time sh bin/studio qc pet-swap            # finishes, no timeout, ≤ 5 min
python3 -c "import json;print(json.load(open('films/pet-swap/checks.json'))['film']['measures']['render'])"
sh bin/studio page still pet-swap 66 333 --out /tmp/q
```

## 4. Interruption and resume (US3, SC-004)

```sh
sh bin/studio render pet-swap --fps 30 &  # close one Chrome window by hand at ~1 min
wait; grep -c "reopening the browser" films/pet-swap/out/render.log   # ≥ 1, video still 17153 frames
sh bin/studio render pet-swap --fps 30 & sleep 120; kill %1; sh bin/studio render pet-swap --fps 30   # header: "(k already done)", k > 0
```

## 5. GPU vs software output (SC-005)

```sh
sh bin/studio page still pet-swap 20 66 120 200 260 333 400 450 500 540 --out /tmp/cmp/gpu
STUDIO_RENDER_MODE=software sh bin/studio page still pet-swap 20 66 120 200 260 333 400 450 500 540 --out /tmp/cmp/sw
# mean absolute difference per channel ≤ 8/255 (research R4 measured 1.38)
```

## 6. No software fallback mixing (US1 scenario 6)

Covered by `tests/render/run.sh` (forces GPU mode with a software browser: the log shows `GPU lost … re-recording everything in software` and the video has the right frame count).

## 7. Desktop app (US4, SC-008), manual on the reference machine

1. Build the Linux core (`desktop/core-build/build-linux.sh`) and the installer from this branch; install in Host mode.
2. Settings → Worker shows `Rendering: GPU · ANGLE (… Intel(R) UHD Graphics 730 …)`.
3. Give a 30 s 3D film; the job log has `render: gpu`; record time ≤ 1/5 of the same film with `config render software`.
4. A Client (018) connected to this Host shows the same line.

## 8. Guards (SC-007)

```sh
git status --porcelain lib/ | wc -l       # 0
```
No `apt`/`brew` call in any studio command (grep in tests/render/run.sh).
