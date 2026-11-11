# Research: Gói đăng YouTube (011)

## R1. Ai làm phần nào: agent viết dữ liệu, lệnh của xưởng làm tệp

**Decision**: Ở bước `Publish`, agent làm hai việc:
1. Viết `films/<tên>/publish/pack.json` (contracts/files.md) trong một lần `Write`.
2. Chạy `sh STUDIO/bin/studio publish <tên>`.

Lệnh này không gọi Claude. Nó dựng mọi tệp còn lại rồi kiểm theo FR-009. Nếu trượt, agent sửa `pack.json` một lần và chạy lại. Sau đó agent gọi `job done`, dù gói đạt hay trượt.

**Rationale**:
- Chi phí. Bài chạy thật của 010 tốn 7,92 triệu token, phần lớn là đọc lại bối cảnh ở mỗi lượt. Mỗi lượt của agent chính đọc lại khoảng 150–250 nghìn token từ bộ nhớ đệm. Bước Publish chỉ cần 2–4 lượt (viết `pack.json`, chạy lệnh, có thể sửa một lần), tức khoảng 3–5% việc (SC-004).
- Agent đã có sẵn bảng ảnh của bước Self-check trong bối cảnh, nên chọn được thời điểm cho thumbnail mà không phải đọc ảnh mới.
- Mọi tệp do code viết nên luôn đúng khuôn dạng. Chỉ phần chữ (tiêu đề, mô tả, tên chương, chữ trên ảnh) cần Claude.

**Alternatives considered**:
- Một `claude -p` riêng do worker chạy sau cổng QC, giống biên tập của 010. Cách này bị loại vì: phải gửi lại treatment, kịch bản và bảng ảnh; mã của việc đã bị thu hồi ở `finished()`; và cần thêm một đường gọi Claude ngoài agent.
- Để agent tự viết mọi tệp (`.srt`, mô tả có mốc chương). Cách này bị loại vì tốn token và dễ sai mốc thời gian.

## R2. Thumbnail: chính trang phim cộng một lớp chữ HTML

**Decision**: Viết `tools/filmcheck/thumbs.mjs`. Tệp này import `core/render/page.mjs` của thư viện và làm như sau:
1. Đọc cỡ phim bằng ffprobe trên `<tên>.mp4` để biết phim ngang hay dọc.
2. `openDemo(dir, {w, h})` ở đúng cỡ đã render phim (thường 1920×1080 hoặc 1080×1920).
3. Với mỗi thumbnail:
   - gọi `window.render(t)`;
   - chụp vùng sẽ đặt chữ để đo nền (R3);
   - chèn một `<div id="studio-thumb">` cố định trên cùng (`z-index` tối đa, `pointer-events:none`) với chữ, phông, màu, nền chữ và vị trí lấy từ `pack.json`;
   - chờ `document.fonts.ready`;
   - chụp PNG toàn khung, rồi xoá lớp chữ.
4. Thu nhỏ về 1280×720 (hoặc 720×1280) bằng `ffmpeg -vf scale=…:flags=lanczos`. Nếu PNG > 2 MB thì xuất JPEG chất lượng 90 với tên `thumbnail-n.jpg` (FR-002).
5. In JSON số đo của từng ảnh cho `publish.py`.

**Phông**: lấy `font` trong `pack.json`. Nếu không có thì lấy họ phông tính được của phần tử chữ lớn nhất trong `window.TEXTS(t)`, hoặc của `body` nếu trang không có `TEXTS`. `document.fonts.check()` phải đúng; nếu sai thì ghi lỗi "font not loaded".

**Rationale**: Ảnh có đúng phong cách của phim, vì cùng trang, cùng phông, cùng bộ máy (VII). Không cần công cụ vẽ ảnh mới. Không sửa thư viện (VI); `texts.mjs` của 010 đã dùng cách import này.

**Alternatives considered**:
- `still.mjs` rồi `ffmpeg drawtext`. Bị loại vì drawtext không có phông web của phim, khó căn chữ nhiều dòng, và không đo được hộp chữ.
- Render ở 1280×720 trực tiếp. Bị loại vì trang được dựng cho 1920×1080, đổi viewport có thể làm lệch bố cục.

**Kiểm khi implement (task đầu)**: chạy trên 2 phim có sẵn trong `films/`, kiểm rằng lớp chữ không làm trang lỗi và khung hình giống khung tương ứng của video (so trung bình màu, sai khác ≤ 3%). Nếu khác thì dừng và hỏi.

## R3. Đo "đọc được khi thu nhỏ"

**Decision**: Máy kiểm dùng 3 số đo, tất cả tính trên khung trước khi thu nhỏ:
- **Cỡ chữ**: chiều cao hộp dòng chữ / chiều cao ảnh ≥ 0,08, lấy từ `getBoundingClientRect` của từng dòng. Ở 320×180, mức này tương đương chữ cao khoảng 14 px.
- **Tương phản**: tính theo công thức độ sáng tương đối của WCAG 2.x.
  - Nền thật dưới hộp chữ được đo từ ảnh chụp trước khi phủ chữ: vẽ PNG lên `<canvas>` trong trang rồi `getImageData`, lấy độ sáng ở bách phân vị 10 và 90.
  - Nếu có nền chữ (màu `plate`, độ mờ `a`), nền hiệu dụng = `a·plate + (1−a)·nền`.
  - Tương phản = min(tỉ lệ với p10, tỉ lệ với p90), tức trường hợp xấu nhất. Đạt khi ≥ 4,5.
- **Ký tự thiếu phông**: `qc.missing_glyphs(film_dir, [chữ])` của 010.

**Rationale**: Đo được bằng số và lặp lại được (IV). Dùng p10 và p90 thay cho trung bình để nền loang lổ không lọt kiểm.

**Alternatives considered**: OCR trên ảnh 320×180. Bị loại vì cần thêm phần mềm (Tesseract) và kết quả không ổn định.

## R4. Chương

**Decision**:
- `pack.json` có `chapters: [{"from": "P01", "title": "…"}, …]`. Agent chọn các đoạn bắt đầu chương.
- `publish.py` lấy mốc bắt đầu = `at` của dòng đầu tiên thuộc đoạn đó trong `narration.json`. Chương đầu luôn ghi `0:00`.
- Mỗi chương kết thúc ở mốc của chương sau; chương cuối kết thúc ở thời lượng phim (ffprobe).
- Luật: `from` của chương đầu là đoạn đầu tiên; ít nhất 3 chương; mỗi chương ≥ 10 giây; mốc tăng dần; tên ≤ 40 ký tự.
- Viết theo dạng `m:ss Tên`, hoặc `h:mm:ss` khi phim từ 1 giờ.
- **Không áp dụng** khi phim < 30 giây, hoặc khi không có cách chia đoạn nào cho 3 chương ≥ 10 giây (máy thử mọi cách chia liền nhau). Khi đó `chapters` phải rỗng và mô tả không có phần chương. Ngược lại, `chapters` rỗng trong khi chia được là trượt.
- Phim không có `narration.json`: mục chương là "không áp dụng".

**Rationale**: Mốc chương lấy từ dữ liệu thật của giọng đọc, nên khớp phim. Agent chỉ đặt tên và chọn chỗ ngắt. Luật theo trang trợ giúp của YouTube về chương video.

## R5. Phụ đề

**Decision**:
- Chữ lấy từ `lines.json` (`lines_file` trong `narration.json`). 010 đã kiểm rằng các câu này đúng kịch bản đã đạt.
- Mỗi dòng giọng được chia thành khối theo câu, rồi theo dấu phẩy nếu khối dài quá 2×42 ký tự hoặc quá 7 giây. Chữ CJK tính 2 đơn vị mỗi ký tự.
- Thời gian lấy từ `qc.load_narration` (mốc tuyệt đối của từng từ ASR). Từ thứ i trong m từ của dòng chữ ánh xạ sang từ ASR thứ ⌊i·n/m⌋ trong n từ ASR. Khối bắt đầu ở mốc bắt đầu của từ ASR đầu tiên và kết thúc ở mốc kết thúc của từ ASR cuối cùng. Khối < 1 giây được kéo dài tới 1 giây nhưng không đè lên khối sau.
- Chữ SRT viết bằng code (khoảng 15 dòng), không gọi `srt.py` của thư viện, để test được không cần thư viện.
- Phim bỏ bước kịch bản: vẫn dùng `lines.json`. Phim không có `narration.json`: không có phụ đề.
- Máy kiểm: chữ của mọi khối ghép lại, chuẩn hoá bằng `qc._norm`, phải bằng chữ của `SCRIPT.md` (bằng `lines.json` nếu không có `SCRIPT.md`); ≤ 2 dòng; mỗi dòng ≤ 42 đơn vị; mỗi khối 1–7 giây; mốc tăng dần, không đè nhau.
- SC-006 (lệch ≤ 0,3 giây) được test trên dữ liệu mẫu.

**Alternatives considered**: Lấy `<tên>.srt` mà thư viện đã xuất. Bị loại vì đó là phụ đề đốt vào hình do agent thiết kế, có thể rút gọn và không bảo đảm khớp kịch bản.

## R6. Máy kiểm và kết quả

**Decision**:
- `publish.py check(film_dir)` trả `{pass, applicable, measures, problems}`, ghi vào `checks.json["publish"]` qua `report.update`, và thêm phần "Publish" vào `CHECKS.md`.
- Thumbnail không render được (không có trình duyệt hay thư viện) thì mục thumbnail là `not_checked` và tính là trượt, kèm lý do.
- Con số trong tiêu đề và mô tả: tách số viết bằng chữ số (gồm `1.2`, `1,200`, `45%`) và số tiếng Anh viết bằng chữ từ "ten" trở lên. Mỗi số phải có trong tập số của `SCRIPT.md` cộng `SOURCES.md`. Số tiếng Anh viết bằng chữ được đổi sang chữ số bằng một bộ đọc nhỏ: one … ninety-nine, hundred, thousand, million, billion. Tiếng Việt chỉ so số viết bằng chữ số.
- Tiêu đề > 60 đơn vị thì phải có chỗ ngắt (`:`, ` - `, ` — `, `|`, `?`, `!`) ở vị trí ≤ 60, để phần trước đứng riêng được (FR-003).
- Hashtag: 3–5 thẻ, mỗi thẻ dạng `#chữ` không có khoảng trắng, ≤ 30 ký tự.
- Không có `<` hoặc `>` trong tiêu đề và mô tả.
- Tên kênh tham chiếu: máy không kiểm được, vì phong cách đã học không lưu tên kênh. Lời dặn trong JOB.md và CLAUDE.md cấm điều này.

## R7. Việc online bị dừng ở bước Publish

**Decision**: Có một hàm chung `jobs.publish_cut(job_id, reason)`. Nó chỉ làm gì khi `job.step == "Publish"`:
- ghi `job.publish_cut = reason`;
- KHÔNG đổi trạng thái việc.

Ba nơi gọi hàm này:
- **proxy `over_cap`**: nếu `publish_cut` nhận việc thì chỉ thu hồi mã, không gọi `quotas.fail`. Agent mất quyền gọi Claude rồi tự thoát.
- **worker, watchdog và giới hạn thời gian một lượt**: dừng container, gọi `publish_cut`, rồi `finished()`.

Trong `worker.finished()`: nếu việc là phim, có `publish_cut` và chưa có `reported.done`, thì coi như agent đã `job done` với phim `input.film`, rồi chạy cổng QC như thường:
- QC đạt: việc `done`, và `qa.publish = {"pass": false, "cut": reason, …}` với phần gói đã có.
- QC trượt: không có vòng sửa (trần đã hết), việc lỗi do xưởng và trả lượt như 007.

**Rationale**: Theo câu trả lời Q4 của spec. Chỉ áp dụng ở bước Publish, nên không đổi luật trần token cho các bước khác.

## R8. Hiển thị online

**Decision**:
- **API**: 3 đường trong `server.py`, dùng chung cho local và online như `poster` và `srt`, đi qua `resources.film_dir`, nên quyền xem giống file phim (FR-014):
  - `GET /api/v1/films/{name}/publish`: JSON của gói, gồm tiêu đề, mô tả, tên các tệp và kết quả kiểm;
  - `GET /api/v1/films/{name}/publish/{file}`: chỉ nhận các tên trong danh sách cho phép (contracts/api.md);
  - `GET /api/v1/films/{name}/publish.zip`: dựng trong bộ nhớ bằng `zipfile`; gói nhỏ, dưới 10 MB.
- **Giao diện** (`app.js`):
  - Trang việc đã xong có mục `#publish`: lưới 3 ô, mỗi ô có ảnh, hướng, tiêu đề, nút "Copy title" và chữ trên ảnh; dưới lưới là mô tả với nút "Copy description", rồi các nút "Download subtitles", "Download pack" và tóm tắt kiểm.
  - Copy dùng `navigator.clipboard.writeText`; nếu không được thì chọn sẵn chữ.
  - `STAGES` thêm `Publish` sau `Self-check`.
- Không thêm công cụ MCP. Ai cần thì gọi REST với cùng mã (009), vì chưa có ai cần (II, YAGNI).
