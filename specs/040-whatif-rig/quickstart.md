# Quickstart: kiểm 040

1. Test: `sh tests/ae/run.sh && sh tests/blender/run.sh` (rồi đủ 8 bộ test của xưởng).
2. Bảng mẫu `ball@3` (AE thật): phim thử `films/rig040-proof` (`engine: "ae"`, `cast/cast.json` có `hero` kid áo vàng, `mum` adult, `baby` toddler, rig `ball@3`) → `sh bin/studio ae sheet rig040-proof`. Đo tỉ lệ trên ảnh toàn thân bằng `specs/040-whatif-rig/measure_sheet.py` → mọi số trong khoảng SC-002.
3. Ảnh đặt cạnh khung mẫu: ghép `references/whatif-long/proof/out/ref.jpg` + ảnh bảng mẫu (chỉ để xem, ảnh ghép nằm trong `references/whatif-long/proof/out/`).
4. Phòng: shot Blender `k.set("kitchen")`, `k.set("livingroom")` → `sh bin/studio blender build rig040-proof --still --quarter --shots …` (3 góc mỗi phòng); đo luma/contrast/saturation → trong khoảng FR-010.
5. Khung chứng minh: một shot 6 s (phòng khách, hero + mum, máy đẩy có ease 1,7 %/s) → `ae build` (GPU) → `learn compare whatif-long --ref … --ours … --round 1` và `--clip`.

## Kết quả (2026-11-28)
- Bảng mẫu `ball@3` (AE thật, `films/rig040-proof`): cao hero 3,27 · mum 3,28 · baby 2,22 đầu; mắt 0,229; chân 0,24; bàn tay 0,229 / 0,24 / 0,219 bề ngang đầu → trong khoảng SC-002. Ảnh ghép `references/whatif-long/proof/out/rig3_vs_ref.jpg`.
- Phòng (¼ cỡ, Blender 5.2.5, GPU Intel UHD 730), 3 góc mỗi phòng: bếp luma 0,496–0,542, tương phản 0,179–0,182, bão hoà 0,223–0,252; phòng khách 0,459–0,523 / 0,172–0,181 / 0,216–0,246 → trong khoảng FR-010 (`rooms040.jpg`). Cách đạt: look `Very High Contrast`, phơi sáng −1,4, màu pha về xám (`SOFT` 0,66 bếp, 0,5 phòng khách).
- Khung chứng minh: S8 phòng khách (hero + mum) và S9 bếp (mum + baby) dựng bằng `ae build` (lớp nhân vật AE + Blender GPU). Máy đo bằng camtrack: S8 10,1 % · 1,78 %/s · ease 0,15/0,52/0,86; S9 10,0 % · 1,77 %/s · ease 0,17/0,52/0,86. `learn compare` ảnh S9 với `ref.jpg` (khung mẫu là cảnh bếp): luma Δ 0,031 · bão hoà Δ 0,033 · rất tối Δ 3,7 điểm % · màu khớp 4/4 → đạt (vòng 3; vòng 1 S8 phòng khách so với khung bếp: màu 2/4, vòng 2 S9 bị lưng ghế che). `learn compare --clip` báo máy đứng vì chỉ số trượt khung không thấy zoom vào giữa (nhật ký sửa #1 của bộ mẫu); số máy lấy từ camtrack.
- T008: shot AE S1 (con đi bộ cầm giỏ qua `CU.carry`, mẹ đổi lo → cười, em bé vẫy) dựng được; CHECK lộ mép nền đã nới nền.
- Test: `tests/run.sh`, `render`, `learn`, `ui`, `license`, `ae` (86), `blender` (28) qua; `filmcheck` (509) và `online` (255) có 2 test ghi cứng ball@2 là rig mới nhất → sửa theo `rigs.latest("ball")`, chạy lại qua; `test_plan_run` lệch thời gian 5,8 s/5 s khi máy bận, chạy lại qua.
