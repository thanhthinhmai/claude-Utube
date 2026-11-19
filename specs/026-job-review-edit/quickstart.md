# Quickstart: kiểm chứng điểm duyệt và chỉnh sửa

## Chuẩn bị

- `sh bin/studio status` sẵn sàng; `sh bin/studio deps voice music`; `sh bin/studio deps ui`.
- Phim thử: chép `films/hundred-words` sang `films/review-trial`, đổi `SCENES` trong `index.html` sang `scenes.json` (một lần, theo `contracts/film-files.md`), chạy `sh bin/studio channel attach review-trial <kênh>` để có `reviews.on`.

## 1. Cổng Script (US1, SC-002)

```sh
sh bin/studio point status review-trial                # script: on, not_reached hoặc stale
sh bin/studio voice make review-trial                  # ✗ bị chặn, in lệnh cần chạy
sh bin/studio point approve review-trial script --source chat
sh bin/studio voice make review-trial --only L01       # chạy
```

Mong đợi: lần chạy đầu mã 1 kèm lý do; sau khi duyệt thì chạy được.

## 2. Sửa đoạn trên trang (US1, SC-001)

```sh
sh bin/studio ui open
sh bin/studio job start --kind film --name review-trial --film review-trial --points script,shots
sh bin/studio review request <mã> --kind script --film review-trial --summary films/review-trial/SCRIPT.md
```

Trên trang việc:

1. Thanh tiến trình hiện "Waiting for you: Script".
2. Sửa đoạn P3 rồi bấm "Run script check": điểm mới hiện trong vòng 30 s, và cột "If you change this" có Voice → Publish.
3. Nút Approve khoá cho tới khi kiểm đạt.
4. Bấm Approve: `point status` có `script: approved`, và `review wait` trả mã 0.

## 3. Sửa cảnh (US2)

1. `sh bin/studio qc plan review-trial && sh bin/studio qc shots review-trial`
2. Trên trang, mở khung Shots và đổi máy của một cảnh. Lựa chọn chỉ gồm các tên có trong `kit/catalog.json`.
3. Ảnh mới của cảnh đó hiện trong vòng 2 phút, và nhãn "changed" còn tới khi bấm "Run shot check".
4. `sh bin/studio render review-trial` bị chặn khi chưa duyệt Shots. Duyệt xong thì cổng mở.

## 4. Thay đổi không hợp lệ (SC-003)

```sh
sh tests/filmcheck/run.sh          # test_edit: tên ngoài danh mục, base cũ, mức tiếng ngoài dải, bận → mã 2/4/5, tệp không đổi (so SHA-256 trước và sau)
```

## 5. Giọng và trộn (US3, US4, SC-004)

1. Sửa `say` của một dòng rồi bấm "Remake line": chỉ `voices/<id>.wav` của dòng đó đổi (so mtime các tệp khác), và chữ trong `lines.json` giữ nguyên.
2. Đổi mức nhạc: `out/mix.wav` mới; dấu `all` không đổi, nên Shots vẫn `approved`.

## 6. Online (SC-005)

```sh
sh tests/online/run.sh             # test_actions: việc waiting_review không có container chạy; action chạy trong container không proxy; duyệt → queued → agent tiếp đúng điểm
```

## 7. Toàn bộ

```sh
sh tests/run.sh && sh tests/render/run.sh && sh tests/ui/run.sh && sh tests/filmcheck/run.sh && sh tests/online/run.sh
```

Thử thật (SC-006): làm một phim 5 phút bằng chat, có ít nhất một lần sửa ở Script và một lần ở Shots trên trang, và không phải dựng hình lại.

## Kết quả kiểm chứng

### US1, 2026-11-19 (máy local, WSL2; phim `films/review-trial` chép từ `hundred-words`): **đạt**

- Mục 1: `voice make` bị chặn (mã 1, in lệnh `point approve …`). Sau khi duyệt thì chạy (`STUDIO_TTS_DRY`, mã 0).
- Mục 2, trên trình duyệt thật (Playwright, cổng 8787):
  - thanh tiến trình có 10 bước, nhãn REVIEW ở Script và Shots, dòng "Waiting for you: Script";
  - sửa P03 rồi "Run script check": lưu và chấm 10/10 trong **0,84 s** (SC-001: < 30 s); Voice chuyển "Must run again"; cột "If you change Script" có đủ 7 bước;
  - nút Approve khoá khi còn ô sửa chưa kiểm; bấm Approve thì bước Script hiện "Approved", `review wait` trả mã 0, `voice make` chạy được.
- Online (`tests/online/test_review_points_online.py`, `RUNNER=local`): việc chờ duyệt không giữ container; người khác nhận 404; sau khi duyệt, việc chạy lại trong < 60 s (SC-005) và đi tới xong.

### US2, 2026-11-19 (cùng phim, đã đổi sang `scenes.json`, 21 cảnh, GPU Intel UHD 730): **đạt**

- `qc plan` 4 s; `qc shots` 53 s (0 lỗi khung, 7 cảnh báo phong cách).
- Trên trình duyệt thật:
  - khung Shots mở thẳng khi đang chờ duyệt;
  - ô chọn máy chỉ có tên trong `catalog.json`;
  - đổi máy của S02: lưu, kiểm kế hoạch và vẽ lại ảnh trong **5,6 s** (lần đầu 19 s; SC-001: < 2 phút); S02 có nhãn "changed" và nút duyệt khoá với lý do "Run the shot check…";
  - "Run shot check" xong trong 74 s (đạt, còn 2 cảnh báo cho cả phim);
  - giữ phong cách kèm lý do thì nút duyệt mở; bấm "Approve and render" thì bước Shots hiện "Approved".
- `render-gate`: trước khi duyệt báo "style warning(s) are open"; sau khi duyệt trả mã 0.
- Lỗi tìm thấy khi thử thật và đã sửa:
  - bản xem trước vẽ cả thẻ chữ của cảnh khác;
  - trang tự vẽ lại làm mất nhãn "changed";
  - trạng thái "waiting" che trạng thái thật của bước;
  - cảnh báo cho cả phim không có nút giữ;
  - mẫu tên ảnh của 025 không nhận mã cảnh 2 chữ số.

### US3, 2026-11-19 (cùng phim, 39 dòng, Kokoro thật): **đạt**

- Khung Voice mở thẳng khi đang chờ duyệt: chọn giọng, tốc độ, nghe từng dòng, ô `say`, "Save say", "Remake line".
- Sửa `say` của l001 rồi "Remake line": chỉ `voices/l001.wav` đổi (l002 giữ giờ cũ), chữ của kịch bản giữ nguyên, mất **7,3 s**.
- `voice make --changed`: đổi chữ 2 dòng thì đúng 2 tệp được làm lại (test, SC-004). `qc voice` báo `script_mismatch` khi lời đọc lệch kịch bản (FR-007).

### US4, 2026-11-19 (cùng phim): **đạt**

- `edit review-trial mix music=none sfx=-6`: trộn lại bằng tiếng thật trong **14 s**; chỉ Self-check và Publish phải làm lại; dấu hình không đổi (test).
- Test âm thanh: chọn `music: none` thì đoạn lặng giữa các câu nhỏ hơn 10 lần so với có nhạc.
- Khi làm, "nhạc giữa các nhịp" được hiểu là mức giảm nhạc khi có lời (`duck_db`, research R11).

### US5, 2026-11-19 (bản chép của `aged-backward`): **đạt**

- `edit … publish chosen=2`: lưu trong 0,3 s; `PUBLISH.md` xếp tiêu đề 2 lên đầu, ghi "(chosen)"; kiểm gói đăng chạy lại (ở bản chép báo phụ đề cũ, đúng là "lưu được, kiểm chưa đạt", mã 1).
- Test: `chosen` ngoài 1–3 bị từ chối; hashtag phải có 3–5 cái; đổi gói đăng không làm bước nào phải làm lại.

### Toàn bộ, 2026-11-19

- `tests/run.sh` 87/87 · `tests/render` đạt (gồm 30 test bộ dựng) · `tests/filmcheck` 253 đạt · `tests/ui` 56 + 33 test trình duyệt đạt · `tests/online` 199 đạt (sau khi sửa lỗi tràn ngang ở 360 px do thanh tiến trình).
- `test_api.test_fifty_jobs_under_two_seconds` đôi khi trượt (49/50), vì mã việc trùng khi tạo 50 việc trong một giây. Lỗi này có từ trước 026.
- SC-006 (một phim 5 phút làm thật, có sửa ở Script và Shots): **chưa chạy**. Cần một lượt làm phim thật bằng Claude, tốn lượt gọi.

### T061 / SC-006, 2026-11-19–20 (`films/internet-down-week`, 243 s, 69 cảnh, GPU 60 fps): **đạt một phần**

- **Script:** biên tập viên Claude hết 2 vòng sửa ở 7,5/10, không còn P1. Chủ phim (qua chat) sửa 6 đoạn bằng `edit script-para` rồi duyệt. Agent làm tiếp; luật "unchanged" không đánh trượt các đoạn chủ phim đã sửa.
- **Shots:** tầng 2 tìm 7 cảnh cận bị mờ trước khi dựng hình. Đổi máy sang `mid-eye` bằng `edit shot`, kiểm lại thì hết mờ (cảnh báo độ sâu 17 → 1). Giữ S022 tối kèm lý do, chấp nhận phong cách, duyệt. Dựng hình không phải làm lại vì các lỗi này.
- **Lọt qua điểm duyệt:** S059 (hội trường "212 người" mà trống, vì máy `wide-high` không thấy khán đài). Lỗi có trên bảng ảnh nhưng người duyệt chỉ đọc số đo mà không xem ảnh. Sửa lỗi này phải dựng hình lại.
- **Chỗ yếu của xưởng tìm thấy:**
  - `CREDITS` nằm trong dấu `all` nên làm mất duyệt Shots;
  - trộn tiếng mất 260 phút khi chạy cùng lúc với dựng hình (52 phút);
  - lời phụ đề khoảng 84 ký tự làm gói đăng báo "line over 42";
  - lần duyệt của agent thay chủ phim bị bộ kiểm tra an toàn chặn, đúng như mong muốn.
