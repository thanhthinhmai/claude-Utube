# Contract: lệnh CLI (020)

Mã thoát chung, giống `qc` của specs/010:
- **0**: đạt;
- **1**: có lỗi (in mỗi lỗi một dòng);
- **2**: không đo được (thiếu file, phim hỏng).

Mọi lệnh nhận `--json` và khi đó in object kết quả tầng ([data-model.md](../data-model.md)).

## `sh bin/studio voice asr <phim> [--lang en|zh|…]`
- Chạy `core/tts/asr_check.py` của thư viện trên `films/<phim>/lines.json` và `voices/`, với `--model` lấy từ `tools/asr.json` theo ngôn ngữ. Ngôn ngữ lấy theo thứ tự: `--lang`, rồi `CHANNEL_BRIEF`, rồi mặc định `en`.
- In dòng `model: <tên>`.
- Thay cho việc gọi thẳng asr_check trong luồng làm phim.

## `sh bin/studio qc voice <phim>`: tầng 0
- Đầu vào: `lines.json`, `voices/*.wav`, `voices/words.json`, `voices/dur.json`.
- Luật: `pause_in_line` (≥ 0,8 s giữa hai từ của cùng dòng, được `silencedetect` trên file wav xác nhận), `asr_mismatch` (từ lệch lời, như asr_check), `tail_mismatch` (|từ cuối − dur| > 0,5 s).
- Dòng ghi `"recorded": true` trong `lines.json` (giọng người dùng tự thu): vẫn báo, nhưng lời khuyên là "kiểm lại bản thu" thay cho "tạo lại dòng".
- Dòng ra mẫu: `✗ l17 at 2.31 s  pause_in_line 0.86 s ≥ 0.8 s  → regenerate l17`.
- Chạy 70 dòng mất ≤ 30 s. Tầng này không nhận dạng lại giọng, chỉ đọc `words.json`.

## `sh bin/studio qc plan <phim>`: tầng 1
- Đầu vào: trang phim (`SHOTS`, `DUR`, `CUES`, `CARDS`), `narration.json`, `lines.json`, `voices/words.json`.
- Luật: bảng "plan" trong [checks.md](checks.md).
- Dòng ra mẫu: `✗ P27.2 312.48 s  cut_in_sentence 0.12 s < 0.4 s  "The neighbours start…"  → cut at ≥ 314.06 s`.
- Phim không có `SHOTS`: in `! no shot list (window.SHOTS): shot rules skipped`, rồi chỉ chạy `silence`, `pause_between_paras`, `tail`, `cue_short`, `card_read`.
- Phim không có giọng: chỉ chạy `shot_short`, `shot_long`, `tail` (tính từ cảnh cuối), `card_read`.

## `sh bin/studio qc shots <phim>`: tầng 2
- Trước khi chạy: in số ảnh và thời gian ước tính (`192 frames · gpu · ≈ 80 s`).
- Ghi ra `.check/shots/<id>.jpg`, `.check/shots/sheet-<n>.jpg`, và `tiers.shots` trong `checks.json`.
- Luật khung (`block`): `flat`, `dark`, `blown`, `missing_glyph`, `text_over_subtitle`. Luật phong cách (`warn`): `style_luma`, `style_saturation`, `style_cuts_per_min`.
- Dòng cuối mẫu: `✗ shots: 3 frame problem(s) · 2 style warning(s) · sheet .check/shots/sheet-1.jpg`.

## `sh bin/studio qc accept-style <phim> --reason "<một dòng>"`
- Ghi `tiers.shots.style_accept`. Từ chối (mã 2) khi `--reason` rỗng hoặc khi không có cảnh báo phong cách nào.

## `sh bin/studio qc except <phim> <mã cảnh> <luật> --reason "<lý do>"`
- Thêm ngoại lệ vào `qc-exceptions.json`, rồi tính lại `pass` của tầng `plan` và `shots` từ số đo đã lưu.
- `qc except <phim> --list`: liệt kê ngoại lệ. `qc except <phim> <mã cảnh> <luật> --remove`: bỏ một ngoại lệ.
- Mã 2 khi: mã cảnh không có, luật không được phép ngoại lệ, hoặc thiếu lý do.

## `sh bin/studio qc <phim>` (hoặc `qc final <phim>`): tầng 4
- Như specs/010, với các thay đổi:
  - luật nhịp lấy từ `rhythm.py`;
  - mốc cắt lấy từ danh sách cảnh của tầng 1 (khi có);
  - thêm `loudness_range` (`warn`, so với phong cách) và `av_sync` (|độ dài tiếng − độ dài hình| ≤ 0,1 s).
- Ghi `checks.json → film` như cũ, và `tiers.final`.
- Báo cáo liệt kê mọi cảnh báo phong cách còn mở, kèm lý do đã chấp nhận (FR-013).
- `voice`, `plan`, `shots`, `except`, `accept-style` và `final` là từ dành riêng. Phim mang một trong các tên đó thì gọi bằng `qc final <phim>`.

## `sh bin/studio render <phim> [như 019] [--skip-checks "<lý do>"] [--no-stop] [--fresh]`
- Trước khi mở trình duyệt, kiểm cổng (`cli.py render-gate`). Không đạt thì in ví dụ sau, mã 1:
  ```
  ✗ render: the plan check has not passed for the current film (run: sh bin/studio qc plan <phim>)
  ✗ render: 2 style warnings are open (run: sh bin/studio qc accept-style <phim> --reason "…")
  ```
- `--skip-checks "<lý do>"`: chạy luôn. Ghi `render: checks skipped — <lý do>` vào `render.log` và `tiers.render.skipped_checks`. Lý do rỗng thì mã 2.
- Tầng 3 bật mặc định. Đoạn lỗi làm lệnh dừng với dòng `✗ render: chunk 14 (P27.2, 141.0 s) black_frames 0.40 s`, mã 1.
- `--no-stop`: ghi hết, rồi in mọi lỗi của tầng 3 ở cuối. Mã 1 nếu có lỗi.
- `--fresh`: không dùng lại các đoạn của lần bị dừng (R8).
