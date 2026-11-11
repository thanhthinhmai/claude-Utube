# Tasks: Gói đăng YouTube cho mỗi phim

**Input**: `specs/011-publish-pack/` (spec.md, plan.md, research.md, data-model.md, contracts/cli.md, contracts/files.md, contracts/api.md, quickstart.md). Tính năng này xây trên 010 (`tools/filmcheck/`, `checks.json`, `narration.json`, cổng QC của worker) và trên 007–009 (việc online, trang việc).

**Tests**: có. FR-012 đòi một gói mẫu cố ý lỗi cho mỗi luật, và SC-001, SC-002, SC-003, SC-006 cần test tự động. Test không cần mạng và không tốn hạn mức:
- phim mẫu (trang HTML nhỏ có `window.render`, `narration.json`, `words.json`, `lines.json`, mp4 tạo bằng ffmpeg) được tạo ngay trong test, ở `tests/filmcheck/.tmp/`;
- phần trình duyệt bỏ qua khi máy không có playwright-core hoặc Chromium.

**Luật chung cho mọi task**:
- Không sửa `lib/` (hiến pháp VI). Không commit media.
- Lệnh `publish` không gọi Claude và không cần mạng.
- Chữ in ra màn hình bằng tiếng Anh, ngắn.
- Sau mỗi phase, 5 bộ test phải đạt: `tests/run.sh`, `tests/learn/run.sh`, `tests/ui/run.sh`, `tests/filmcheck/run.sh`, `tests/online/run.sh`. Commit sau mỗi phase.

## Phase 1: Setup

- [X] T001 Kiểm mục "Kiểm khi implement" của research.md R2 và ghi kết quả vào mục mới "Kết quả kiểm T001" ở cuối `specs/011-publish-pack/research.md`. Cách kiểm: viết thử một script nháp trong scratchpad, dùng `openDemo` của `lib/lemo-opuscar/core/render/page.mjs`, chạy trên 2 phim có sẵn trong `films/`. Cần trả lời:
  - (a) chèn một `<div>` cố định trên cùng rồi gọi `window.render(t)` có làm trang lỗi không, và chữ có nằm trên hình không;
  - (b) ảnh chụp (không có lớp chữ) ở thời điểm t có giống khung t của `<tên>.mp4` không: lấy khung bằng ffmpeg, so trung bình màu, sai khác phải ≤ 3%;
  - (c) PNG 1920×1080 thu về 1280×720 nặng bao nhiêu byte.

  **Nếu (a) hoặc (b) khác research thì dừng ở đây và hỏi người dùng** (hiến pháp II).
- [X] T002 [P] Thêm lệnh `publish <film> [--check-only] [--json]` vào parser của `tools/filmcheck/cli.py`, tạm thời trả mã 2 với dòng "not built yet". Trong `bin/studio`: thêm `publish` vào `case` (chuyển tới `cmd_filmcheck`) và thêm dòng vào `usage`. Tạo `tools/filmcheck/publish.py` rỗng có docstring trỏ tới specs/011.
- [X] T003 [P] Trong `tests/filmcheck/samples.py`, thêm `make_publish_film(dir, *, narration=True, script=True, vertical=False, seconds=50)`. Hàm này tạo một phim mẫu gồm:
  - `index.html` có `window.READY` và `window.render(t)` (vẽ nền đổi màu theo t cùng một chữ), cùng `window.TEXTS`;
  - `<tên>.mp4` tạo bằng ffmpeg đúng thời lượng, cỡ 1920×1080 hoặc 1080×1920;
  - `SCRIPT.md` 5 đoạn, có số "3,000" và "ten thousand";
  - `SOURCES.md` có số "1.2 million";
  - `lines.json`, `voices/words.json`, `voices/dur.json`, `narration.json` khớp nhau;
  - `publish/pack.json` hợp lệ theo contracts/files.md.

  Thêm `bad_pack(kind)`: mỗi `kind` sửa `pack.json` hoặc tệp phim để sinh đúng một mã lỗi của contracts/cli.md.

## Phase 2: Foundational

- [X] T004 Trong `tools/filmcheck/report.py`:
  - `empty()` có `"publish": None`; `load()` giữ khoá này;
  - `markdown()` thêm phần `**Publish:** pass|fail`, với bảng mã lỗi và số đo, dòng "not applicable" cho chương và phụ đề khi không áp dụng, và dòng `cut` khi có;
  - thêm `THRESHOLDS_PUBLISH` cho các ngưỡng của contracts/cli.md.

  Test trong `tests/filmcheck/test_publish.py::Report`: `script check` của 010 ghi sau `publish` không làm mất mục `publish`, và ngược lại.
- [X] T005 Trong `tools/filmcheck/publish.py`, viết `read_pack(film_dir) -> dict`. Hàm kiểm khuôn dạng của `pack.json` theo data-model.md và báo lỗi bằng `PublishError` (mã thoát 2) khi:
  - `titles` không đúng 3 mục, hoặc mỗi mục thiếu `angle`, `text` hay `thumb`;
  - thiếu `thumb.t` hoặc `thumb.text`;
  - `hook` không phải danh sách chuỗi;
  - `chapters` không phải danh sách `{from, title}`;
  - `hashtags` không phải danh sách chuỗi.

  Giá trị mặc định của thumbnail: `position` = `"bottom"`, `color` = `"#ffffff"`, `plate` = `"#000000"`, `plate_opacity` = `0.6`. Các luật về độ dài và số **không** kiểm ở đây; chúng thuộc máy kiểm (US2).

## Phase 3: User Story 1 - Nhận gói đăng cùng với phim (P1) 🎯 MVP

**Goal**: `sh bin/studio publish <phim>` viết đủ tệp của gói từ `pack.json`. Agent online và hướng dẫn làm phim local có bước `Publish`.

**Independent Test**: Phim mẫu 50 giây → `publish` thoát 0 hoặc 1 (không phải 2). `publish/` có `thumbnail-1..3.png`, `thumbs.json`, `titles.md`, `description.md`, `subtitles.srt`, `PUBLISH.md`. Mô tả có `0:00` và nguồn từ `SOURCES.md`. Phụ đề ghép lại bằng chữ kịch bản.

### Tests for User Story 1

- [X] T006 [P] [US1] Trong `tests/filmcheck/test_publish.py`, viết test cho chương, phụ đề và mô tả, chạy trên dữ liệu của T003 và không cần trình duyệt:
  - mốc chương = `at` của dòng đầu mỗi đoạn, chương đầu ghi `0:00`;
  - phim 25 giây: chương "không áp dụng";
  - khối phụ đề ≤ 2 dòng × 42 đơn vị, dài 1–7 giây, chữ ghép lại bằng `SCRIPT.md`, lệch ≤ 0,3 giây so với từ ASR đầu (SC-006);
  - `description.md` đúng thứ tự của contracts/files.md, bỏ dòng `fiction` và `provided:`, mỗi nguồn ghi một lần;
  - `titles.md` và `PUBLISH.md` có 3 cặp; phim không có `narration.json` thì `PUBLISH.md` có mục `## Missing`.
- [X] T007 [P] [US1] Trong `tests/filmcheck/test_thumbs.py`, viết test cho thumbnail. Bỏ qua khi không có `node` và `lib/lemo-opuscar/node_modules/playwright-core`. Cần kiểm:
  - phim mẫu ngang → 3 ảnh 1280×720; phim dọc → 720×1280;
  - `thumbs.json` có `text_height_ratio` > 0 và `contrast` > 0;
  - chữ trắng trên nền trắng không có `plate` → `contrast` < 1,5.

### Implementation for User Story 1

- [X] T008 [US1] Trong `tools/filmcheck/publish.py`, viết `chapters(film_dir, pack) -> (list, applicable)` theo R4:
  - mốc lấy từ `qc.load_narration`, thời lượng từ `qc.probe_duration`;
  - hàm `can_split(paragraph_starts, duration)` thử mọi cách chia liền nhau để biết có chia được ≥ 3 chương, mỗi chương ≥ 10 giây hay không;
  - định dạng `m:ss`, hoặc `h:mm:ss` khi phim từ 1 giờ.
- [X] T009 [US1] Trong `tools/filmcheck/publish.py`, viết `subtitle_cues(film_dir) -> list|None` và `write_srt(cues, path)` theo R5:
  - chữ lấy từ `lines.json` qua `narration.json["lines_file"]`, thời gian lấy từ `qc.load_narration`;
  - chia khối theo câu, rồi theo dấu phẩy khi khối dài quá 84 đơn vị hoặc quá 7 giây; CJK tính 2 đơn vị;
  - ánh xạ từ chữ sang từ ASR bằng ⌊i·n/m⌋;
  - khối < 1 giây được kéo tới 1 giây nhưng không đè lên khối sau;
  - không có `narration.json` hoặc `lines_file` thì trả `None`.
- [X] T010 [US1] Trong `tools/filmcheck/publish.py`, viết `sources_lines(film_dir)` (đọc bằng `script.read_sources` của 010, bỏ `fiction`, `provided:` và `no factual claims`, bỏ trùng theo đường dẫn). Viết thêm `write_titles`, `write_description` và `write_publish_md` theo đúng mẫu của contracts/files.md. Mục `## Missing` ghi từng phần thiếu và lý do (FR-001a).
- [X] T011 [US1] Viết `tools/filmcheck/thumbs.mjs` theo R2 và R3. Cách gọi: `node thumbs.mjs <film dir> <lib dir> <job.json> <out dir>`, trong đó `job.json` = `[{t, text, position, color, plate, plate_opacity, font}]`. Các bước:
  - import `core/render/page.mjs`;
  - `openDemo` ở cỡ của mp4 (Python truyền qua `job.json`);
  - với mỗi ảnh: `render(t)`, chụp vùng chữ để đo p10 và p90 độ sáng nền qua `<canvas>`, chèn `#studio-thumb`, chờ `document.fonts.ready`, đo `getBoundingClientRect`, tính độ tương phản WCAG có nền chữ, chụp PNG toàn khung, xoá lớp chữ;
  - in một dòng JSON `{"thumbs": [...]}`.

  Phông: dùng `font` nếu có, không thì phông của phần tử chữ lớn nhất trong `TEXTS(t)`, không nữa thì phông của `body`. `document.fonts.check` sai thì ghi `"font_loaded": false`.
- [X] T012 [US1] Trong `tools/filmcheck/publish.py`, viết `render_thumbs(film_dir, pack, lib) -> list`:
  - chạy `thumbs.mjs`;
  - thu nhỏ từng ảnh bằng `ffmpeg -vf scale=1280:720:flags=lanczos` (720:1280 với phim dọc);
  - ảnh ≥ 2 000 000 byte thì xuất lại JPEG `-q:v 2` với tên `thumbnail-n.jpg`;
  - thêm `missing_glyphs` bằng `qc.missing_glyphs(film_dir, [text])`;
  - viết `thumbs.json`.

  Không có `node` hoặc thư viện thì trả lỗi `thumb_not_rendered` kèm lý do; không ném ngoại lệ.
- [X] T013 [US1] Trong `tools/filmcheck/publish.py`, viết `build(film_dir, lib)`:
  - xoá mọi tệp trong `publish/` trừ `pack.json`;
  - gọi T008–T012;
  - trả danh sách lỗi dựng (thường rỗng).

  Trong `tools/filmcheck/cli.py`, viết `cmd_publish`: `read_pack` → `build`, rồi tạm thời ghi `checks.json["publish"]` với `pass` = không có lỗi dựng (US2 thay bằng máy kiểm đầy đủ); in kết quả; mã 0, 1 hoặc 2 theo contracts/cli.md.
- [X] T014 [US1] Trong `tools/runner/JOB.md`:
  - thêm `Publish` vào danh sách tên giai đoạn;
  - thêm mục "The Publish step" ở ngay trước `job done`, gồm: `job step <id> Publish`; viết `films/<name>/publish/pack.json` trong một lần `Write`, chọn 3 thời điểm từ bảng ảnh Self-check đã có và không xem thêm ảnh; 3 tiêu đề theo 3 hướng, mỗi tiêu đề có một chữ trên ảnh bổ sung chứ không lặp tiêu đề; con số chỉ lấy từ SCRIPT.md hoặc SOURCES.md; viết bằng ngôn ngữ của phim; không nêu tên kênh nào; không có `<` hay `>`;
  - chạy `sh STUDIO/bin/studio publish <name>`; mã 1 thì sửa `pack.json` một lần rồi chạy lại; sau đó `job done` dù gói đạt hay không.
  - Câu về vòng sửa QC: sau khi render lại thì chạy lại `publish` trước `job done`.
- [X] T015 [US1] Trong `tools/runner/agent.py`, lời nhắc vòng sửa QC và bản sửa phim ("Request changes") phải nhắc chạy lại `studio publish <name>` trước `job done`. Bản sửa không chép `publish/` của phim cũ (`publish` viết lại cả bộ). Test trong `tests/online/test_agent_thrift.py`: lời nhắc vòng sửa có chữ `publish`.
- [X] T016 [US1] Trong `tests/online/fake_agent.py`, thêm bước `Publish` cho mọi phim: `job step Publish`, viết `pack.json` hợp lệ (dùng chung mẫu với `tests/filmcheck/samples.py`), chạy `studio publish`. Phim giả không có trang dựng hình, nên `fake_agent` tự viết 3 PNG nhỏ (1280×720, tạo bằng ffmpeg) cùng một `thumbs.json` hợp lệ, rồi chạy `studio publish <name> --check-only`. Như vậy gói giả đạt máy kiểm. Thêm thẻ `[publish-bad]`: viết một tiêu đề dài 120 ký tự.
- [X] T017 [P] [US1] Trong `CLAUDE.md`, luồng làm phim thêm bước 3a "Gói đăng" sau Self-check: viết `publish/pack.json`, chạy `sh bin/studio publish <tên>`, sửa một vòng, báo lỗi còn lại bằng một dòng khi giao. Thêm `Publish` vào danh sách tên giai đoạn. Ghi lệnh `publish <phim>` cho phim cũ (FR-001a). Thêm `publish` vào dòng `bin/studio` ở mục Cấu trúc. Trong `specs/003-studio-ui/contracts/skill-integration.md`, thêm `Publish` vào danh sách tên giai đoạn của phim.

**Checkpoint**: US1 chạy được ở local trên phim mẫu và trên 1 phim có sẵn trong `films/`.

## Phase 4: User Story 2 - Máy kiểm gói đăng trước khi giao (P2)

**Goal**: mọi luật FR-009 có số đo; gói trượt không chặn việc; bị dừng ở bước Publish thì vẫn giao phim.

**Independent Test**: gói mẫu đạt → 0 lỗi; mỗi `bad_pack(kind)` → đúng một mã lỗi (SC-002); `--check-only` < 10 giây (SC-003); việc giả `[publish-bad]` và `[publish-cap]` vẫn `done`.

### Tests for User Story 2

- [X] T018 [P] [US2] Trong `tests/filmcheck/test_publish.py::Rules`, viết một test cho mỗi mã lỗi của contracts/cli.md (`files_missing` … `subtitles_cue`), dùng `bad_pack(kind)`. Gói mẫu đạt thì `problems == []`. Mục thumbnail dùng `thumbs.json` viết tay, để không cần trình duyệt. Đo thời gian `--check-only` < 10 giây trên phim 60 giây.
- [X] T019 [P] [US2] Trong `tests/online/test_publish_step.py`, viết test cho worker:
  - (a) việc giả thường → `qa.publish.pass == true`, có `problems`, `titles` (3 chuỗi) và `files`;
  - (b) `[publish-bad]` → việc `done`, `qa.publish.pass == false`, lượt không được trả;
  - (c) `[publish-cap]`: `fake_agent` gọi `job step Publish`, rồi test đặt trần token thấp để proxy `over_cap` → việc `done`, `qa.publish.cut` có chữ "token";
  - (d) watchdog ở bước Publish → việc `done` với `cut`;
  - (e) chạm trần ở bước `Render` → việc vẫn `failed` như trước (luật cũ không đổi).

### Implementation for User Story 2

- [X] T020 [US2] Trong `tools/filmcheck/publish.py`, viết `check(film_dir, *, pack=None) -> dict` theo contracts/cli.md và data-model.md (PublishCheck). Các luật:
  - đếm đơn vị (CJK tính 2);
  - `title_break` với các chỗ ngắt `:`, ` - `, ` — `, `|`, `?`, `!` ở vị trí ≤ 60;
  - `thumb_repeats_title`: chuẩn hoá chữ thường, bỏ dấu câu, chuỗi ≥ 3 từ liền nhau (≥ 6 ký tự với CJK);
  - `number_unsourced`: tách số viết bằng chữ số (`3,000`, `1.2`, `45%` thành giá trị số) và số tiếng Anh viết bằng chữ từ ten trở lên, đọc bằng bộ đọc nhỏ one…ninety-nine, hundred, thousand, million, billion; so với tập số của `SCRIPT.md` cộng `SOURCES.md`;
  - `thumb_font` khi `font_loaded` là `false`;
  - `language`, `hashtags`, `angle_brackets`, `hook_length`, `description_length`;
  - `chapters` theo R4;
  - `subtitles_text` so bằng `qc.norm_words` (đổi tên công khai cho `qc._norm`, giữ tên cũ làm bí danh); `subtitles_cue`;
  - mục thumbnail đọc `thumbs.json` và đo lại cỡ ảnh và dung lượng.

  `applicable` theo FR-001a. Ghi kết quả bằng `report.update`.
- [X] T021 [US2] Trong `tools/filmcheck/cli.py`, `cmd_publish` dùng `check()` thay cho kết quả tạm của T013. `--check-only` bỏ qua `build`. `--json` in đúng `checks.json["publish"]`. Mã thoát 0 hoặc 1 theo `pass`.
- [X] T022 [US2] Trong `tools/studio/studio/jobs.py`, viết `publish_cut(job_id, reason) -> bool`: chỉ khi việc là phim, chưa ở trạng thái cuối và `step == "Publish"` thì ghi `publish_cut` cùng một dòng log, rồi trả `True`. Trong `tools/runner/proxy.py`, `over_cap`: nếu `jobs.publish_cut(job_id, "the job reached its token limit during the Publish step")` thì chỉ `revoke`, không gọi `quotas.fail` (R7).
- [X] T023 [US2] Trong `tools/runner/worker.py`:
  - `check_runs`: nhánh watchdog và nhánh giới hạn thời gian gọi `jobs.publish_cut(...)`. Nếu nhận thì dừng container rồi gọi `self.finished(job_id, rc)` thay cho `failed`;
  - `finished()`: việc phim có `publish_cut` và chưa có `reported.done` → coi như đã `job done` với phim `input.film`. Bỏ vòng sửa QC trong trường hợp này: QC trượt thì `failed` như cũ;
  - viết `publish_summary(runner, work, film, cut)`: chạy `studio publish <film> --check-only --json` qua `runner.exec`, rồi trả `{pass, cut, applicable, problems, titles, files}`, hoặc `None` khi không có `publish/pack.json` và không có `cut`. Gọi hàm này sau khi `quality()` đạt và ghi vào `qa.publish`. Kết quả này **không** đổi `qa.pass`;
  - log việc thêm một dòng "Publish check: pass" hoặc "Publish check: N problems".
- [X] T024 [US2] Trong `tests/online/fake_agent.py`, thêm thẻ `[publish-cap]`: sau `job step Publish`, gọi proxy liên tục tới khi bị từ chối, rồi thoát mã khác 0 mà không gọi `job done`.

**Checkpoint**: US1 và US2 chạy đúng. Gói trượt hoặc bị dừng không làm mất phim.

## Phase 5: User Story 3 - Lấy gói đăng trên trang việc (P3)

**Goal**: mục "Publish" trên trang việc với ảnh, nút copy và nút tải (contracts/api.md).

**Independent Test**: việc giả đã xong → API trả JSON của gói; người khác nhận 404; trong trình duyệt 360 px có 3 thẻ, copy tiêu đề ra đúng chữ, và tải được `.srt` và `.zip`.

### Tests for User Story 3

- [X] T025 [P] [US3] Trong `tests/online/test_publish_view.py`, viết test API:
  - `GET /films/{name}/publish` đúng khuôn dạng;
  - `/publish/pack.json` và `/publish/../x` → 404;
  - `/publish.zip` có đúng các tệp được phép và `<name>.srt`;
  - tài khoản khác → 404.

  Thêm `tests/online/browser_publish.cjs`: đăng nhập, mở trang việc, thấy `#publish` có 3 thẻ ảnh; bấm "Copy title" (cấp quyền clipboard cho trình duyệt) và đọc lại đúng chữ; màn hình 360 px không có thanh cuộn ngang (`scrollWidth <= clientWidth`); không có `pageerror`.

### Implementation for User Story 3

- [X] T026 [US3] Trong `tools/studio/studio/resources.py`:
  - `PUBLISH_FILES = re.compile(r"^(thumbnail-[123]\.(png|jpg)|subtitles\.srt|titles\.md|description\.md|PUBLISH\.md)$")`;
  - `publish_file(name, file)` (404 khi tên không khớp hoặc tệp không có);
  - `publish_view(name)` đọc `pack.json`, `description.md` và `checks.json["publish"]`, trả JSON theo contracts/api.md (404 khi không có `PUBLISH.md`);
  - `publish_zip(name) -> bytes` dựng bằng `zipfile`.
- [X] T027 [US3] Trong `tools/studio/studio/server.py`, thêm 3 đường `GET` của contracts/api.md, cạnh `/films/{name}/poster`, với đúng loại nội dung và `Content-Disposition`.
- [X] T028 [US3] Trong `tools/studio/studio/web/app.js`:
  - `STAGES` thêm `"Publish"` sau `"Self-check"`;
  - viết `publishHtml(job)` theo contracts/api.md (3 thẻ ảnh, nút Copy title, `<pre>` mô tả với nút Copy description, Download subtitles, Download pack, dòng kết quả kiểm và `cut`);
  - nút copy dùng `navigator.clipboard.writeText`, không được thì chọn sẵn chữ; nút đổi thành "Copied" trong 2 giây;
  - mọi chữ của người dùng đi qua hàm escape có sẵn;
  - giữ `@ts-check` sạch (`sh tests/ui/run.sh`).

  Trong `tools/studio/studio/web/style.css`, viết lưới thẻ một cột ở màn hình ≤ 600 px.

**Checkpoint**: cả 3 story chạy đúng.

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T029 [P] Viết quickstart mục 2 trên một phim có sẵn trong `films/`: chạy `sh bin/studio publish <phim>` thật, xem 3 thumbnail. Ghi kết quả (mã thoát, lỗi còn lại nếu có, thời gian chạy) vào cuối `specs/011-publish-pack/quickstart.md`.
- [ ] T030 Chạy đủ 5 bộ test. Đối chiếu từng FR-001 … FR-017 và SC-001 … SC-006 với code và test; ghi bảng đối chiếu vào cuối `specs/011-publish-pack/tasks.md`. SC-004 và SC-005 cần bài chạy thật (quickstart mục 3), nên **hỏi người dùng trước khi chạy**, vì tốn tiền.
  - 2026-11-11: bảng đối chiếu đã ghi. Người dùng chọn gộp trước; bài chạy thật (SC-004, SC-005) để cho lần làm phim kế tiếp.

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 → US2 → US3 → Polish. Phải có T001 rồi mới làm T011 và T012.
- US2 cần US1 (máy kiểm đọc các tệp do `build` viết). US3 cần tệp của US1 và `qa.publish` của US2.
- Trong US1: T008, T009, T010 và T011 làm song song được (khác hàm, khác tệp: T011 là `.mjs`). T012 cần T011. T013 cần T008–T012. T014–T017 cần T013.
- Trong US2: T020 → T021. T022 → T023. T024 làm song song với T022.

## Parallel Example: User Story 1

```text
T006 test_publish.py (chương, phụ đề, mô tả)   ‖  T007 test_thumbs.py
T011 thumbs.mjs   ‖  T008/T009/T010 trong publish.py (cùng tệp, nên làm lần lượt)
T017 CLAUDE.md + skill-integration.md   ‖  T014 JOB.md
```

## Implementation Strategy

1. **MVP**: Phase 1 + 2 + US1. Đã dùng được ở local: lệnh `publish` làm đủ tệp cho phim mới và phim cũ.
2. **US2**: thêm máy kiểm và luật "không mất phim" cho bản online.
3. **US3**: hiển thị trên trang việc.
4. Polish: chạy thật ở local; bài chạy online chỉ làm khi người dùng đồng ý.

## Đối chiếu sau implement (T030)

| Yêu cầu | Code | Kiểm chứng |
|---|---|---|
| FR-001 bước Publish sau Self-check, luôn làm; làm lại sau vòng sửa QC | JOB.md, agent.py, worker.py (lời nhắc vòng sửa), CLAUDE.md 3a | test_publish_step (a) có dòng `Publish` trong log |
| FR-001a phim cũ ở local | `publish` chạy với phim không có narration hay script | test_publish `test_old_film_without_narration`; T029 trên `banh-mi-dem` |
| FR-002 3 thumbnail cùng hướng, < 2 MB, phông của phim, 3 thời điểm | thumbs.mjs, `render_thumbs` | test_thumbs (ngang, dọc), Rules `thumb_size`, `thumb_same_time`, `thumb_font` |
| FR-003 3 tiêu đề, ≤ 100, ngắt trong 60, số có nguồn, không `<>` | `check()` | Rules `title_count`, `title_length`, `title_break`, `number_unsourced`, `angle_brackets` |
| FR-004 mô tả đúng thứ tự, nguồn, hashtag, ≤ 5000 | `description_text` | `test_description_order_and_sources`, `test_fiction_and_provided_not_listed`, Rules `hook_length`, `description_length`, `hashtags` |
| FR-005 chương theo luật YouTube | `chapters`, `can_split` | `test_chapters_from_paragraph_starts`, `test_short_film_has_no_chapters`, Rules `chapters` |
| FR-006 phụ đề khớp kịch bản, 2×42, 1–7 giây | `subtitle_cues`, `write_srt` | `test_subtitles_match_script_and_timing`, `test_long_sentence_is_split`, Rules `subtitles_text`, `subtitles_cue` |
| FR-007 PUBLISH.md gộp 3 cặp | `write_publish_md` | `test_titles_and_publish_md` |
| FR-008 ngôn ngữ của phim | luật `language` | Rules `language` |
| FR-009 máy kiểm mọi mục | `check()` | `test_each_bad_pack_fails_one_rule` (22 mã), `test_every_rule_has_a_bad_pack` |
| FR-010 gói trượt hoặc bị dừng vẫn giao phim | `jobs.publish_cut`, proxy `over_cap`, worker | test_publish_step (b), (c), (d); (e) luật cũ ở bước khác giữ nguyên |
| FR-011 kết quả trong checks.json, CHECKS.md | report.py | `Report.test_publish_and_script_results_live_together` |
| FR-012 gói mẫu cố ý lỗi cho mỗi luật | samples.py, `BAD` | như FR-009 |
| FR-013 mục Publish trên trang việc | app.js `fillPublish`, server.py | test_publish_view `test_api`, `test_job_page_in_a_browser` |
| FR-014 chỉ chủ việc và admin | `resources.film_dir` theo tài khoản | `test_someone_else_cannot_see_it`; tests/ui `test_publish_pack` |
| FR-015 làm lại khi sửa phim | revise prompt không chép `publish/`; `build` viết lại cả bộ | lời nhắc trong agent.py; `build` xoá tệp cũ (OWN_FILES) |
| FR-016 token tính vào việc | mọi lần gọi đi qua proxy | có sẵn từ 008 |
| FR-017 không đăng YouTube, không ảnh AI, không tên kênh | không có code đăng; thumbnail chỉ từ trang phim; lời dặn JOB.md, CLAUDE.md | đọc lại code |
| SC-001 mọi phim có gói hoặc có lý do | worker `publish_summary` | test_publish_step (a)–(d) |
| SC-002 bắt đúng 100% lỗi cố ý | | Rules |
| SC-003 `--check-only` < 10 giây | | `test_check_only_is_fast` |
| SC-004 ≤ 5% token, ≤ 3 phút | | **chưa đo**: cần bài chạy thật (quickstart mục 3), tốn tiền, chờ người dùng đồng ý |
| SC-005 đạt trong ≤ 1 vòng sửa; dán vào YouTube không phải sửa | | **chưa đo**: như SC-004, cộng bước kiểm bằng tay trên YouTube Studio |
| SC-006 phụ đề khớp 100%, lệch ≤ 0,3 giây | | `test_subtitles_match_script_and_timing` |

## Phase 7: Convergence

- [X] T031 Add a test in tests/online/test_agent_thrift.py that the QC fix-round message (tools/runner/worker.py) and the revise prompt (tools/runner/agent.py) both tell the agent to run `studio publish` again per T015 / FR-001 (missing)
- [X] T032 Add a test in tests/filmcheck/test_thumbs.py that a thumbnail over the size limit is saved as `thumbnail-n.jpg` and still passes `thumb_size` per FR-002 (partial)
