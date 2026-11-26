# Research: Điểm duyệt Animatic (035)

## R1. Nguồn thời lượng shot

- **Decision**: `films/<phim>/timing.json` giữ số khung của mỗi shot (theo thứ tự `film.json → shots`) và lịch sử. Bộ dựng có `CU.shotFrames("S2")` đọc `data/timing.json` (gói bởi `bundle.py`); mã phim gọi hàm này thay cho mảng riêng. Khi không có `timing.json`, `CU.shotFrames` trả `undefined` và mã phim cũ dùng giá trị của nó, rồi lần dựng đầu ghi `timing.json` từ thời lượng thật đo được trong `shots_<proj>.json` (tự chuyển phim cũ). `ae-sleepless-test` được sửa tay: `CU.FR` đọc `CU.shotFrames`, `mix.py` đọc `timing.json`.
- **Rationale**: một nguồn cho bản nháp, đề xuất, Sound, bản đẹp (FR-017); Undo cần lịch sử; app sửa JSON an toàn hơn sửa JSX.
- **Alternatives**: sửa `CU.FR` bằng regex (giòn); để AE tự kéo dài comp (không đổi được thời điểm câu).

## R2. Mốc câu khi đổi thời lượng

- **Decision**: mỗi câu thuộc shot chứa phần lớn thời lượng câu (theo mốc `narration.json → lines[].at` và độ dài trong `voices/dur.json`). Khi shot đổi thời lượng, câu giữ khoảng cách tới đầu shot của nó: `at_mới = t0_mới(shot) + (at_cũ − t0_cũ(shot))`. `narration.json` được ghi lại cùng lúc với `timing.json`, nguyên tử, dưới một khoá tệp.
- **Rationale**: lời và hình dời cùng nhau; không cần đọc lại giọng; `qc.py` và `rhythm.py` đọc `narration.json` như cũ.
- **Alternatives**: gắn câu vào khung tuyệt đối (vỡ khi shot trước đổi); để Sound tự đặt lại (Sound sau Animatic, quá muộn cho phần trăm lặng).

## R3. Đề xuất khớp shot

- **Decision**: với shot có câu, `end_đích = cuối câu cuối (từ cuối cùng của words.json, nếu không có thì at + dur) + 0,45 s`, làm tròn tới khung. Đề xuất khi |end_đích − end_hiện| > 1 khung: bớt (âm) hoặc thêm (dương). Câu kéo qua đường cắt thuộc shot chứa phần lớn của nó, và không đề xuất nào cắt trước khi câu cuối của shot kết thúc. Shot không có câu: không đề xuất. Shot mới < 1 s: cờ `very_short`. Đề xuất bị bỏ ghi `skipped_for` = băm (thời lượng shot + mốc câu của shot); hiện lại khi băm đổi (FR-013).
- **Rationale**: đúng hành vi đã duyệt trên bản mẫu ("Each shot now ends 0.45 s after its last line"); dùng từ cuối thay vì cuối tệp âm thanh để bỏ đuôi lặng trong tệp giọng.
- **Alternatives**: một nút áp cả phim (người dùng đã bỏ); tối ưu toàn cục theo phần trăm lặng (khó giải thích từng thay đổi).

## R4. Phần trăm lặng giống bước kiểm phim

- **Decision**: `animatic.silence()` dựng danh sách từ (film time) bằng chính `qc.narration_lines` + `rhythm.clamp_words`, rồi gọi `rhythm.measure(..., shots=…)` và lấy `silence_ratio`; giới hạn `rhythm.SILENCE_MAX` (0,20). Tính sau mỗi nhận/bỏ/Undo từ dữ liệu, không cần dựng.
- **Rationale**: SC-003 (≤ 1 điểm phần trăm so với bước kiểm phim) đạt chắc vì cùng một hàm.
- **Alternatives**: đo trên âm thanh của bản nháp (chậm, phải dựng mới đo được).

## R5. Chuyển động bị mất hoặc phải dồn

- **Decision**: `build_core.jsx` sau khi dựng mỗi shot quét đệ quy mọi thuộc tính có keyframe của các lớp trong comp shot (`CU.keyScan`, ES3) và ghi `keys_<proj>.json`: `{shot: [{layer, prop, t0, t1}]}` (giây trong shot). Bản nháp và bản đẹp đều ghi; `ae draft` chép vào `animatic/keys.json`. Đề xuất bớt: chuyển động có `t0 ≥ end_mới` → `drop`; có `t0 < end_mới < t1` → `squeeze`, tỉ lệ = (t1 − t0)/(end_mới − t0), hoặc `clip` nếu tỉ lệ > 2 (bị cắt dở). Tên hiện cho người dùng là `layer · prop` (ví dụ "Hand R · Rotation").
- **Rationale**: FR-014 cần biết chuyển động nằm ở đâu; chỉ AE biết keyframe sau khi chạy mã phim.
- **Alternatives**: bắt mã phim tự khai chuyển động (Claude quên); so điểm ảnh khung cuối (không biết tên chuyển động).
- **Ghi chú**: việc **thực sự dồn** chuyển động khi nhận đề xuất `squeeze` không làm tự động ở 035: đề xuất chỉ báo; nhận thì shot bị cắt và chuyển động bị cắt dở/mất như đã báo. Muốn dồn, người dùng ghim ghi chú để Claude sửa mã shot (US3). Ghi rõ trên trang.

## R6. Bản nháp nhanh

- **Decision**: `CU.DRAFT = true` (từ `ae draft`) đặt `MASTER.resolutionFactor = [4,4]`, render item `setSettings({"Quality": "Draft", "Resolution": [4,4], "Motion Blur": "Off for all layers"})` (hiệu ứng vẫn bật để bố cục đúng), khung 480×270 H.264. Hiệu ứng nặng (Camera Lens Blur, Glow) được tắt bằng cờ `CU.DRAFT` trong các hàm của kit nếu có. Kiểm thực tế trên AE: nếu `setSettings` không có trên bản AE của người dùng, rơi về `applyTemplate("Draft Settings")` + `resolutionFactor`. Đo thời gian bản nháp so với bản đẹp ở quickstart (SC-001).
- **Rationale**: ¼ độ phân giải giảm ~16 lần số điểm ảnh; bố cục, chuyển động và thời lượng vẫn đúng.
- **Alternatives**: chuỗi ảnh tĩnh + giọng (không thấy chuyển động); render bản đẹp rồi thu nhỏ (không nhanh hơn).

## R7. Dựng lại chỉ shot đổi

- **Decision**: `ae draft --shots S2,S6` dựng các shot đó vào một MASTER, rồi `splice.py` ghép vào `animatic/draft.mp4` theo mốc của `timing.json`. Khi thời lượng shot đổi, mọi khung sau đó dời: `splice` lấy khung cũ theo **shot** (không theo số khung tuyệt đối) cho các shot không dựng lại. Thêm chế độ `splice.by_shot()` vào `splice.py`.
- **Rationale**: SC-005 (shot khác giống hệt từng điểm ảnh) và nhanh.
- **Alternatives**: dựng lại cả phim mỗi lần (chậm); để bản nháp lệch thời lượng (người dùng duyệt sai).

## R8. Giọng tạm trong bản nháp

- **Decision**: `ae draft` trộn giọng bằng ffmpeg từ `narration.json` + `voices/*.wav` (`adelay` + `amix`, chuẩn hoá −16 LUFS), không nhạc, không hiệu ứng. Clip từng shot = cắt `draft.mp4` theo `timing.json` (kèm tiếng), khung đại diện ở 50% shot.
- **Rationale**: không phụ thuộc `mix.py` của từng phim (thư viện), đủ để nghe nhịp; Sound (037/026) làm bản trộn thật sau.
- **Alternatives**: chạy `mix.py` của phim (chậm, có thể chưa có, đọc thời lượng cứng).

## R9. Ghi chú và sửa nền

- **Decision**: tách phần ghim của `castnotes.py` (034) thành `pins.py` (đọc/ghi nguyên tử theo `base`, ghim `x,y` %, ghi chú chung, lô, trả lời, chờ lượt sau). `animatic/notes.json` dùng nó với khoá shot và thêm `at` (giây trong shot). "Send notes to Claude": trong việc làm phim → quyết định `revise` của yêu cầu duyệt `animatic` (Claude của việc đó sửa mã các shot có ghi chú, `ae draft --shots …`, trả lời từng ghi chú); ngoài việc → app tạo việc `fix` `target: "animatic"` (như `target: "cast"`, 034).
- **Rationale**: cùng trải nghiệm với Cast; không có mẫu ghi chú thứ ba.
- **Alternatives**: dùng `shot-notes.json` của 029 (dành cho video đã dựng, không có ghim x/y, sẽ lẫn hai loại ghi chú).

## R10. Điểm duyệt và đồ thị bước

- **Decision**: thêm điểm `animatic` vào `points.POINTS`; với phim AE: `AE_ON` thêm `animatic`, điểm `shots` bị ẩn (trạng thái `skipped` lý do "AE films review the animatic"). `steps.STEPS` thêm "Animatic" sau "Voice" (chỉ hiện cho AE, như "Cast"); với AE, "Look/Picture/Shots" ẩn. `GRAPH`: Voice → Animatic; Cast → Animatic; Animatic → Mix, Render. Cổng: `ae render` (bản đẹp) gọi `points.gate(d, "animatic")`. "Approve anyway": `point approve animatic --anyway` chỉ nhận từ `source: ui` hoặc lệnh có `--anyway` do người dùng gõ; ghi `{anyway: true, silence: 0.25}` vào bản duyệt. Agent bị chặn tự duyệt bằng luật hiện có (classifier, specs/026) và JOB.md.
- **Rationale**: theo FR-001…FR-005, FR-010; cùng cơ chế điểm duyệt specs/026.

## R11. Vân tay của điểm animatic

- **Decision**: `fingerprint(d, "animatic")` = băm `timing.json → frames` + `narration.json` + `animatic/notes.json` (chỉ ghi chú mở) + băm mã phim (`ae/*.jsx`, `cast/cast.json`). Bản duyệt cũ thành `stale` khi một trong số này đổi → "Must run again" đúng FR-004/FR-005.
