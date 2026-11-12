# Research: QC theo từng cảnh trước khi render (020)

Mỗi mục: **Quyết định**, **Lý do**, **Đã cân nhắc**.

## R1. Mô hình nhận dạng chung của xưởng (FR-002)

**Quyết định**: tiếng Anh dùng `small.en`, mọi ngôn ngữ khác dùng `small` (faster-whisper, CPU, int8). Ghi ở **một** chỗ: `tools/asr.json` (`{"en": "small.en", "*": "small"}`). Lệnh mới `sh bin/studio voice asr <phim> [--lang L]` đọc file đó, rồi gọi `core/tts/asr_check.py` của thư viện với `--model` tương ứng. Thư viện không bị sửa (asr_check đã nhận `--model`). Công cụ học phong cách (`tools/style-learn/sl/speech.py`) cũng đọc `tools/asr.json`. `app models` (`host.py WHISPER_MODELS`) tải thêm `small.en` và `small`.

**Lý do**: số đo trên 70 dòng giọng của `pet-swap`. Đã chạy lại `small.en` trên `l01.wav` và được đúng các mốc của `voices/words.json`, nên file đó đúng là của `small.en`.

| Số đo (70 dòng) | `base.en` (`words.base.json`) | `small.en` (`words.json`) |
|---|---|---|
| \|từ cuối − độ dài file\| trung bình / lớn nhất | 0,26 s / 0,51 s | 0,16 s / 0,34 s |
| Từ ngắn hơn 0,06 s (mốc hỏng) | 108 | 34 |
| Khoảng nghỉ ≥ 0,8 s giả bên trong dòng | 18 | 1 |
| Từ đầu dòng có mốc âm | 69 | 69 |

`base.en` có 18 khoảng nghỉ giả, nên dùng nó thì tầng 0 sẽ báo lỗi sai. Mốc âm có ở cả hai mô hình, do asr_check thêm đoạn lặng vào đầu file trước khi nhận dạng. Vì thế vẫn phải chặn về 0 (FR-004).

**Đã cân nhắc**: dùng biến môi trường `WHISPER_MODEL` cho toàn xưởng. Bị loại vì biến này áp dụng cho mọi ngôn ngữ, mà `small.en` chỉ nghe được tiếng Anh nên asr_check sẽ dừng với phim tiếng Trung. `medium`: chậm hơn khoảng 3 lần và chưa có số đo cho thấy cần.

## R2. Câu theo kịch bản (FR-003, FR-004)

**Quyết định**: viết module mới `tools/filmcheck/rhythm.py`. Nó tách lời của mỗi dòng (`lines.json`, mà `qc` đã buộc phải khớp `SCRIPT.md`) thành câu theo dấu `. ? ! …` (và `。？！`). Rồi gắn từ đầu và từ cuối của mỗi câu lên từ của bản nhận dạng bằng `difflib.SequenceMatcher` trên từ đã chuẩn hoá. Cách này giống `films/pet-swap/timeline.py`, cách đã cho `pet-swap` đạt `qc`. Từ nằm trong khối `replace` (số, như "7" ↔ "seven") được chia theo tỉ lệ. Mốc được kẹp vào `[0, dur]` trước mọi phép đo.

**Lý do**: ở `pet-swap`, công cụ nhận dạng viết "at 7, but it sounds wrong," cho hai câu, nên `qc.sentences()` hiện tại nối hai câu thành một và báo cắt giả. Kịch bản là nguồn đúng duy nhất.

**Đã cân nhắc**: ép công cụ nhận dạng giữ dấu câu bằng `initial_prompt`. Bị loại vì không bảo đảm được.

## R3. Một bộ luật nhịp cho tầng 1 và `qc` (FR-006, FR-010)

**Quyết định**: chuyển `narration_measures` và các hằng ngưỡng từ `qc.py` sang `rhythm.py`, đổi đầu vào thành `(câu, từ, danh sách cảnh, dur)`, và thêm các luật mới:
- độ dài cảnh từ 1,1 s đến `shot_max` (mặc định 6 s);
- thời gian hiện phụ đề;
- thời gian đọc thẻ chữ.

`qc.measure` (tầng 4) gọi đúng hàm này. Mốc cắt khi đó lấy từ danh sách cảnh đã lưu ở tầng 1 (không còn dò cắt bằng `scdet` khi phim có danh sách cảnh). Một test chạy cả hai đường trên cùng dữ liệu và so kết quả.

**Lý do**: SC-005 chỉ đúng khi hai bên dùng cùng một code.

**Phim ngắn (edge case)**: `qc` hiện nay **không** có ngưỡng riêng cho phim ngắn. Plan hiểu edge case như sau: phim dưới 30 s dùng cùng ngưỡng nhịp, và bỏ qua phép so "số lần cắt mỗi phút" với phong cách (đếm trên dưới nửa phút thì không đáng tin). Người dùng đã duyệt (2026-11-12).

## R4. Đọc kế hoạch của phim mà không dựng hình (FR-005, FR-008)

**Quyết định**: viết `tools/filmcheck/plan.mjs`. Nó mở trang phim một lần bằng hàm `openDemo` của thư viện (như `texts.mjs`), không gọi `render(t)` cho từng khung, và đọc:
- `window.SHOTS`: các dòng `[t0, t1, set, id]`. Đây là định dạng `pet-swap` đang xuất. Bắt buộc với phim mới.
- `window.DUR`.
- `window.CUES` (`[[t0, t1, text]]`) nếu có; không có thì đọc `cues.json`, rồi `<phim>.srt`.
- `window.CARDS` (`[[t0, t1, id, text]]`) nếu có: thẻ chữ, dùng cho luật thời gian đọc.

Phim không có `CARDS`: tầng 1 chạy `readcheck.mjs` của thư viện (qua `sh bin/studio page readcheck`) và đọc kết quả. Cách này chậm hơn, nên báo cáo ghi "đọc thẻ chữ bằng readcheck". Kết quả đọc được lưu ở `.check/plan-input.json`, gắn với dấu vân tay nguồn, nên chạy lại khi nguồn chưa đổi chỉ tốn vài phần mười giây.

**Lý do**: phần tốn thời gian chỉ là mở trang (dựng thế giới 3D, chờ `READY`). Luật nhịp chạy bằng Python trong vài mili giây. Mục tiêu 10 s (FR-008) sẽ được đo trên `pet-swap` ở quickstart. Vượt mục tiêu thì báo trong kết quả kiểm chứng, không lặng lẽ bỏ qua.

**Đã cân nhắc**:
- Đọc `shots.json` riêng của `pet-swap`: không phải phim nào cũng có file này.
- Dò cắt từ bản xem trước độ phân giải thấp cho phim không có `SHOTS`: tốn một lần dựng hình, trái với mục đích của tầng 1. Theo nguyên tắc V, chọn nhánh "báo không có danh sách cảnh, chỉ chạy các luật không cần cảnh" mà spec cho phép.

## R5. Kiểm hình theo cảnh (FR-011 – FR-014)

**Quyết định**: viết `tools/filmcheck/shots.mjs`. Nó dùng cùng trình duyệt với `record.mjs` (biến `STUDIO_RENDER_MODE` và `PLAYWRIGHT_CHROME` do `render_env` đặt, nên GPU nếu có) ở 960×540. Với mỗi cảnh:
- gọi `render((t0+t1)/2)`; cảnh có thẻ chữ thì gọi thêm ở giữa khoảng thẻ hiện;
- chụp JPEG vào `.check/shots/<id>.jpg` và đọc `window.TEXTS(t)`;
- đo ngay trong trang bằng canvas `getImageData` (như `thumbs.mjs`), nên Python vẫn chỉ cần thư viện chuẩn.

Các số đo:
- **khung phẳng**: lượng tử hoá màu 4 bit mỗi kênh, rồi tính tỉ lệ của màu nhiều nhất, sau khi bỏ hộp chữ (`TEXTS`) và dải letterbox. Dải letterbox là các hàng trên và dưới có độ sáng < 0,03 và độ lệch < 0,01. Phẳng khi tỉ lệ > 0,60, hoặc độ lệch chuẩn độ sáng < 0,04. Cảnh có hộp chữ chiếm ≥ 2% khung thì không bị báo vì độ lệch thấp (nền thẻ chữ, US2 AC4);
- **quá tối hoặc cháy**: p50 độ sáng < 0,04, hoặc tỉ lệ điểm > 0,98 lớn hơn 0,25. Ngưỡng ghi đè được bằng `qc.json` của phong cách;
- **độ sáng p50, độ bão hoà p50**: dùng cho so phong cách;
- **chữ đè phụ đề**: hộp chữ không phải phụ đề cắt vùng phụ đề (mặc định 18% dưới của khung, ghi đè bằng `subtitle_zone` trong `qc.json`) lúc có phụ đề đang hiện;
- **chữ thiếu phông**: gọi lại `qc.missing_glyphs` trên chữ của `TEXTS` và phụ đề.

Bảng ảnh vẽ trong trang bằng canvas: mỗi ô có mã cảnh, ô lỗi viền đỏ, 6 cột, mỗi tấm tối đa 48 ô. Ghi ra `.check/shots/sheet-<n>.jpg`. Cách này không cần `drawtext` của ffmpeg, vốn phụ thuộc phông.

**Lý do**: dùng lại bộ dựng hình của 019 (hiến pháp VII), một lần mở trình duyệt. 192 ảnh × khoảng 0,4 s với GPU, tức khoảng 1,5 phút, dưới mức 3 phút (SC-003).

**Đã cân nhắc**: chụp bằng `page still` của thư viện rồi đo bằng Pillow. Bị loại vì mỗi ảnh phải mở trình duyệt một lần, và phải thêm gói Python.

## R6. Số đo phong cách (FR-013, FR-017)

**Quyết định**: viết `tools/filmcheck/stylerefs.py`. Nó đọc bảng "Key numbers" trong `my-styles/<slug>/EVIDENCE.md`: các hàng `luma p50`, `saturation p50`, `cuts/min`, `loudness range`, lấy cột khoảng `a–b`. Sau đó `my-styles/<slug>/qc.json` (nếu có) ghi đè từng khoá: `luma_p50`, `saturation_p50`, `cuts_per_min`, `loudness_range`, `shot_max`, `still_max`, `subtitle_zone`, `dark_p50`, `blown_share`. Phong cách thư viện không có hai file này, nên kết quả là "bỏ qua so phong cách".

Phép so dùng trung vị trên mọi ảnh giữa cảnh, theo trọng số độ dài cảnh. Với `pet-swap` và Dusk Hypothetical: độ sáng 0,13 nằm ngoài 0,198–0,299, bão hoà 0,53 nằm ngoài 0,319–0,504 (SC-004).

**Lý do**: EVIDENCE.md là bằng chứng mà style-learn đã ghi (hiến pháp VIII), không cần thêm bước học.

## R7. Cổng render và dấu vân tay (FR-009, FR-021)

**Quyết định**:
- `checks.json` có thêm mục `tiers`. Mỗi tầng ghi `fingerprint`, là SHA-256 trên các file nguồn của phim. Quy tắc bỏ file giống `tools/render/lib.mjs`, thêm `qc-exceptions.json` và `.check/`, nên đánh dấu ngoại lệ không làm hỏng các đoạn đã ghi. `lib.mjs` cũng thêm `qc-exceptions.json` vào danh sách bỏ qua.
- `sh bin/studio render` gọi `cli.py render-gate <phim>` trước khi chạy `record.mjs`. Cổng đạt khi `tiers.plan` và `tiers.shots` (chỉ phần luật khung) cùng `pass` và cùng dấu vân tay với nguồn hiện tại. Cảnh báo phong cách còn mở thì phải có `style_accept.reason`. Nếu không đạt: in lý do và lệnh cần chạy, mã thoát 1, chưa mở trình duyệt.
- Cờ `--skip-checks "<lý do>"` cho chạy luôn: ghi `tiers.render.skipped_checks` và một dòng vào `render.log`.

**Lý do**: cổng nằm trong lớp vỏ shell. `record.mjs` chỉ đổi để thêm tầng 3, phần còn lại của 019 giữ nguyên.

## R8. Kiểm từng đoạn trong lúc ghi (FR-016)

**Quyết định**:
- Sau khi mỗi đoạn được đổi tên thành `c_NNNN.mp4`, `record.mjs` gọi hàm trong module mới `tools/render/chunkcheck.mjs`. Hàm chạy `ffmpeg … -vf scale=320:-2,blackdetect=d=0.25:pix_th=0.06,freezedetect=n=0.003:d=0.5`, rồi ghi khoảng đen, khoảng đứng yên và đoạn đứng yên ở đầu và cuối đoạn vào `c_NNNN.json`.
- Hình đứng yên vượt qua ranh giới đoạn được nối khi hai đoạn kề nhau đều đã kiểm, vì các worker ghi lệch thứ tự. Ngưỡng là `still_max` của phong cách. Cảnh có ngoại lệ `still` thì bỏ qua.
- Đoạn lỗi: đặt `abort`, xoá đoạn lỗi và các đoạn **sau** nó, giữ các đoạn trước. Ghi `out/.chunks/STOPPED.json` (`{fingerprint, chunk_size, fps, size, first_bad, shot, at, rule}`), in mã cảnh và thời điểm, mã thoát 1.
- Cờ `--no-stop`: ghi hết, rồi liệt kê mọi lỗi ở cuối.

**Ghi lại sau khi sửa** (US4): sửa phim làm đổi dấu vân tay, nên theo 019 mọi đoạn sẽ phải ghi lại. Vì vậy, khi có `STOPPED.json` với cùng `chunk_size`, `fps` và `size`, `record.mjs` chép sang thư mục mới các đoạn đã đạt nằm hoàn toàn trước `first_bad` (và cũng trước mọi cảnh có dòng trong danh sách cảnh bị đổi so với lần trước, so bằng mã băm `SHOTS` lưu ở `STOPPED.json`). Log ghi "reused N chunks from the stopped run". Cờ `--fresh` để ghi lại tất cả. Xem Complexity Tracking.

**Đã cân nhắc**: kiểm toàn bộ video sau khi ghép (như `qc`). Bị loại vì không dừng sớm được.

## R9. Gói đăng dùng phụ đề của phim, thumbnail sạch (FR-018, FR-019)

**Quyết định**:
- `publish.subtitle_cues` lấy phụ đề từ `.check/plan-input.json` (chính các phụ đề tầng 1 đã kiểm, cùng dòng, cùng mốc), chỉ khi `tiers.plan` đạt với nguồn hiện tại. Nếu không: lỗi `subtitles_not_passed`, chỉ về `qc plan`. Phim cũ không có tầng 1 và không có phụ đề riêng thì vẫn dùng cách cắt hiện có, kèm ghi chú.
- `thumbs.mjs`, trước khi chụp: đặt `window.CLEAN = true`, rồi thêm CSS `body *{visibility:hidden} canvas,#studio-thumb,#studio-thumb *{visibility:visible}`. Mọi chữ dạng DOM (phụ đề, thẻ) đều ẩn, chỉ còn hình canvas và chữ của gói đăng. Phim vẽ chữ thẳng lên canvas phải tôn trọng `window.CLEAN` (hợp đồng trang).
- Kiểm SC-008: so vùng phụ đề của thumbnail với cùng khung chụp khi đã ẩn hết chữ (sai khác trung bình < 2/255).

## R10. Ngoại lệ (FR-015)

**Quyết định**: ghi ngoại lệ vào `films/<tên>/qc-exceptions.json`, mỗi mục `{shot, rule, reason, at}`, bằng lệnh `sh bin/studio qc except <phim> <mã cảnh> <luật> --reason "…"`. Không có dạng "mọi cảnh" hay "mọi luật": mã cảnh phải có trong `SHOTS`, luật phải nằm trong danh sách luật cho phép ngoại lệ (`flat`, `dark`, `blown`, `still`, `shot_long`, `text_over_subtitle`). Đánh dấu xong, tầng 1 và tầng 2 tính lại kết quả từ số đo đã lưu, không chụp lại.

## R11. Luồng làm phim (FR-020)

**Quyết định**: sửa luồng làm phim trong `CLAUDE.md` (bước 3 và mục Dựng hình) và trong `tools/runner/JOB.md`:
1. `voice asr`
2. `qc voice`
3. `qc plan`
4. `qc shots`
5. `render` (có tầng 3)
6. mux
7. `qc`
8. `publish`

Trang việc trên app hiện mỗi tầng như một bước con, dùng lại `job step` hiện có (không đổi API).
