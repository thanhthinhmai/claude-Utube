# Số đo "trước" (specs/027, T002–T003)

Ngày 2026-11-19, worktree `027-kit-craft-upgrade` tại commit 2d2a7f9 (kit 023).

## Test gốc (T002)

| Bộ | Kết quả |
|---|---|
| `sh tests/run.sh` | PASS 87/87 |
| `sh tests/filmcheck/run.sh` | OK |
| `sh tests/learn/run.sh` | OK |
| `sh tests/ui/run.sh` | OK (0 fail) |
| `sh tests/render/run.sh` (gồm test của kit) | 29 + 28 pass, 0 fail |

Ghi chú: `node --test my-styles/*/kit/test/*.test.mjs` chạy thẳng sẽ lỗi `ERR_MODULE_NOT_FOUND three`. Test của kit phải chạy qua `tests/render/run.sh` (có hook nạp `three`).

## Khung tham chiếu cho FR-013 / SC-008 (T003)

`films/kit-post/base/<phim>/t_<giây>.jpg` (không vào git), chụp ở 960×540 bằng `sh bin/studio page still <phim> 10 60 120 200 290`. Gồm `pause-ten-seconds` và `hundred-words` (phim 1 phút: các mốc sau 60 s là khung cuối).

## Thời gian dựng (T003, so cho SC-006)

`sh bin/studio page clip pause-ten-seconds --from 0 --to 10` (GPU, kit 023): **22,9 s** tổng (gồm mở trình duyệt). Mốc so ở T031/T040 đo cùng lệnh, cùng máy.

## Tay nghề của phút đầu pause-ten-seconds (0:00–1:00, kit 023)

23 cảnh; 15 cảnh có người; 22 cảnh không phải thẻ.

| Tỉ lệ | Giá trị | Cách đếm |
|---|---|---|
| action | **0** (0/15) | act chỉ là cử chỉ (look, nod, lean-in, tilt-head, point…) |
| prop | 0,133 (2/15) | tư thế `hold-*` |
| outdoor | 0,091 (2/22) | `street`, `stadium` |
| ots | 0 (0/22) | máy `ots` |

Bối cảnh: `custom:cafe` 12, `custom:watch` 6, còn lại mỗi bối cảnh 1.

## US3 (T031, T035), 2026-11-19

- AO cost, 100 frames of films/kit-acting at 1920×1080 on the GPU (page still, includes the browser start): no AO 16.3 s, AO 16 samples 22.6 s (+63 ms a frame), AO 8 samples 17.7 s (+14 ms a frame). Kept 8 samples.
- FR-013 / SC-008: the 5 reference frames of films/pause-ten-seconds and films/hundred-words drawn again with their own copied kits are byte-identical to T003 (10/10).
