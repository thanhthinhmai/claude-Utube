# Tasks: Giao diện và API của xưởng (giai đoạn 1)

**Input**: Design documents from `specs/003-studio-ui/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (api-v1.md, cli.md, skill-integration.md), quickstart.md

**Tests**: Bắt buộc theo hiến pháp IV. `sh tests/ui/run.sh` (unittest + TestClient + subprocess), offline.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [ ] T001 Tạo `tools/requirements-ui.txt` (`fastapi`, `uvicorn`, `markdown`, `httpx`); thêm `.studio/` vào `.gitignore`
- [ ] T002 Thêm `deps ui` vào `bin/studio` (tạo `tools/.venv` nếu chưa có, cài tầng `ui`, đánh dấu bằng checksum như `deps learn`)
- [ ] T003 Thêm `ui …`, `job …`, `review …` vào `bin/studio`: chạy `tools/.venv/bin/python tools/studio/studio_cli.py`; chưa cài thì báo `sh bin/studio deps ui`, mã 1
- [ ] T004 [P] Tạo khung `tools/studio/studio_cli.py` (argparse theo contracts/cli.md) và gói `tools/studio/studio/__init__.py` (`VERSION`)
- [ ] T005 [P] Tạo `tests/ui/run.sh` và `tests/ui/helpers.py` (dự án tạm qua `STUDIO_ROOT` với `films/`, `references/`, `my-styles/` mẫu; phim mẫu bằng ffmpeg; `.srt` mẫu)

## Phase 2: Foundational

- [ ] T006 Viết `tools/studio/studio/store.py`: gốc dự án (`STUDIO_ROOT` ghi đè được), thư mục `.studio/{jobs,reviews}`, ghi nguyên tử (tmp + `os.replace`), tạo độc quyền (tmp + `os.link`), khoá `fcntl.flock` theo mã, đọc danh sách
- [ ] T007 Viết `tools/studio/studio/jobs.py` theo data-model.md: `id` dạng `j-YYYYMMDD-HHMMSS-xxxx`; `owner = "local"`; `kind ∈ {learn, film}`; `name` 1–80 ký tự; `step` ≤ 120 ký tự; `progress {done ≤ total}`; `log` 50 dòng cuối, mỗi dòng ≤ 300 ký tự; trạng thái lưu và `inactive` khi `running` mà `now − updated_at > 600 s`; chuyển trạng thái theo sơ đồ
- [ ] T008 Viết `tools/studio/studio/reviews.py` theo data-model.md: tạo (`style-1`/`style-2`, đọc `proof/compare.json` cho `style-2`, `final_round`), quyết định đầu tiên thắng (`AlreadyDecided`), góp ý bắt buộc ≥ 3 ký tự khi `revise`, `accept_anyway`/`stop` chỉ khi `style-2` và `final_round`, ghi `waiting.last_poll_at`, việc ⇄ `waiting_review` / `waiting_resume` / `running`
- [ ] T009 Viết `tools/studio/studio/resources.py`: liệt kê phim, bộ tham chiếu, phong cách riêng; kiểm mã `[a-z0-9-]{1,60}`, tên ảnh ghép `v\d{2}_\d{4}\.jpg`, tên ảnh chứng minh `(ref|ours_r\d+_[\d.]+)\.jpg`; `resolve()` phải nằm trong thư mục gốc; bỏ `origin`, `title`, `channel`, `handle`, `source_id` khỏi dữ liệu bộ tham chiếu; `.srt` → WebVTT
- [ ] T010 Viết `tools/studio/studio/server.py` (khung): app FastAPI, `/api/v1/health`, middleware `Host` (localhost/127.0.0.1 + cổng), nguồn loopback, `POST` cần `X-Studio: 1` + JSON, lỗi `{"error": {code, message}}` tiếng Việt, phục vụ `tools/studio/studio/web/` ở `/`
- [ ] T011 [P] Viết `tests/ui/test_store_jobs_reviews.py`: ghi nguyên tử, `inactive` (giả thời gian), quyết định đầu tiên thắng giữa 2 tiến trình, ràng buộc giá trị và góp ý
- [ ] T012 [P] Viết `tests/ui/test_security.py`: `Host` lạ → 403 `bad_host`; `POST` thiếu `X-Studio` → 403 `csrf`; tên tệp có `..`, `/`, `%2e%2e` → 400/404; máy chủ chỉ nghe `127.0.0.1` (kiểm qua launcher)

**Checkpoint**: Lưu trữ, quy tắc và bảo mật nền sẵn sàng.

## Phase 3: User Story 1 - Theo dõi việc (P1) 🎯 MVP

**Goal**: Việc bắt đầu trong khung chat hiện trên giao diện, tự cập nhật.

**Independent Test**: `job start` → máy chủ tự bật → trang Việc thấy việc; `job step` → bước đổi trong < 5 s; `job fail` → trạng thái lỗi và thông báo.

- [ ] T013 [P] [US1] `tests/ui/test_jobs_api.py`: `GET /jobs` (mới nhất trước, lọc `status`/`kind`), `GET /jobs/{id}`, 404, danh sách 50 việc < 2 s (SC-008)
- [ ] T014 [P] [US1] `tests/ui/test_cli_jobs.py`: `job start` in mã và URL, bật máy chủ < 5 s (SC-001, SC-002) và không bật bản thứ hai; `job step --progress 3/5`; `progress` sai → mã 2; `job run` giữ mã thoát, gửi nhịp sống (khoảng nhịp rút ngắn khi kiểm thử), 50 dòng cuối vào nhật ký; `job done/fail/stop`; `ui status/stop`
- [ ] T015 [P] [US1] `tests/ui/test_events.py`: SSE gửi `job.updated` trong < 5 s sau `job step`; có `: ping`
- [ ] T016 [US1] Viết `tools/studio/studio/launcher.py`: `ensure()` (đọc `server.json`, kiểm `pid` và `/health`, chọn cổng 8787–8799, chạy `uvicorn` tách hẳn, đợi tối đa 5 s), `status()`, `stop()` (chỉ tắt đúng máy chủ của xưởng)
- [ ] T017 [US1] Thêm `GET /jobs`, `GET /jobs/{id}`, `GET /events` (quét `.studio` mỗi 1 s) vào `tools/studio/studio/server.py`
- [ ] T018 [US1] Nối `ui open|status|stop` và `job start|step|log|run|done|fail|stop|show` trong `tools/studio/studio_cli.py` theo contracts/cli.md
- [ ] T019 [US1] Viết `tools/studio/studio/web/index.html`, `style.css`, `app.js` phần khung: định tuyến `#/…`, thanh điều hướng (Việc · Phim · Hồ sơ đo · Phong cách), trang Việc (danh sách, lọc, nổi bật việc chờ duyệt, trạng thái trống có hướng dẫn), trang Việc chi tiết (bước, tiến độ, nhật ký, lỗi, liên kết kết quả), `EventSource` tự nối lại, tiêu đề tab `(n) chờ duyệt`

**Checkpoint**: US1 chạy độc lập.

## Phase 4: User Story 2 - Duyệt trên giao diện (P2)

**Goal**: Duyệt lần 1 và lần 2 bằng nút bấm; việc tự chạy tiếp.

**Independent Test**: `review request` → trang duyệt hiện đủ nội dung → `POST` quyết định → `review wait` trả trong < 3 s; quyết định thứ hai → 409 / mã 4.

- [ ] T020 [P] [US2] `tests/ui/test_reviews_api.py`: `GET /reviews?status=pending`, `GET /reviews/{id}` (`summary_html` an toàn: HTML thô bị bỏ), `POST /decision` 201 / 409 / 422 `note_required` / 422 `value_not_allowed`; `style-2` có số liệu `compare` và đường dẫn ảnh
- [ ] T021 [P] [US2] `tests/ui/test_cli_reviews.py`: `review request` đặt việc `waiting_review`; `review wait` nhận quyết định từ API trong < 3 s (SC-003) và việc về `running`; hết giờ → mã 3; `review decide --source chat` → giao diện thấy nguồn `chat`; quyết định thứ hai → mã 4; phiên đóng (không có `wait`) → quyết định được lưu, `wait` sau đó nhận ngay; việc → `waiting_resume` khi không có `wait` trong 60 s
- [ ] T022 [US2] Thêm `GET /reviews`, `GET /reviews/{id}`, `POST /reviews/{id}/decision`, sự kiện `review.created` / `review.decided` vào `tools/studio/studio/server.py`
- [ ] T023 [US2] Nối `review request|wait|decide|status` trong `tools/studio/studio_cli.py`
- [ ] T024 [US2] Thêm trang Duyệt vào `tools/studio/studio/web/app.js`:
  - lần 1: tóm tắt đã chuyển HTML;
  - lần 2: ảnh gốc và ảnh tự vẽ cạnh nhau (bấm để phóng to), bảng 4 chỉ số có ngưỡng và dấu ✓/✗, số vòng;
  - các nút Đồng ý · Yêu cầu sửa (ô góp ý bắt buộc) · Chấp nhận dù chưa đạt / Dừng khi `final_round`;
  - trạng thái "đã duyệt (giao diện/khung chat)" và chặn gửi lần hai;
  - hỏi quyền thông báo sau khi người dùng bấm, thông báo trình duyệt dẫn tới trang duyệt (FR-006a)
- [ ] T025 [US2] Cập nhật `.claude/skills/style-learn/SKILL.md` theo contracts/skill-integration.md (`job start/step/run/done/fail`, `review request/wait/decide`, xử lý `revise` / `accept_anyway` / `stop`, chạy tiếp khi chưa cài `deps ui`)

**Checkpoint**: US1 và US2 chạy độc lập.

## Phase 5: User Story 3 - Xem kết quả (P3)

**Goal**: Xem phim, hồ sơ đo, phong cách riêng trên giao diện.

**Independent Test**: Với phim mẫu, bộ mẫu và phong cách mẫu: phát phim (Range 206), phụ đề WebVTT, hồ sơ đo có số liệu và ảnh ghép, phong cách có `style_html` và khung chứng minh.

- [ ] T026 [P] [US3] `tests/ui/test_resources_api.py`: `/films`, `/films/{name}`, `/video` có `Range` → 206, `/poster`, `/subtitles.vtt` bắt đầu bằng `WEBVTT`; phim đang render → `rendering: true`; `/sets`, `/sets/{set}` không có `origin`/`title`/`channel`/`source_id`, `/sheets` liệt kê hoặc `removed: true`, ảnh ghép, ảnh chứng minh; `/styles`, `/styles/{slug}` (`style_html`, `evidence_html`), `/styleframe`; tệp thiếu → 404 tiếng Việt
- [ ] T027 [US3] Thêm các điểm `/films*`, `/sets*`, `/styles*` vào `tools/studio/studio/server.py` (dùng `resources.py`, `FileResponse` có `Range`)
- [ ] T028 [US3] Thêm trang Phim (trình phát, poster, phụ đề bật tắt, CREDITS, TREATMENT), Hồ sơ đo (bảng số liệu, ô màu, cảnh báo, xem ảnh ghép lần lượt, báo "đã xoá cùng video tham chiếu"), Phong cách (danh sách, chi tiết có khung chứng minh, nguồn học, `STYLE.md`) vào `tools/studio/studio/web/app.js`
- [ ] T029 [US3] Cập nhật luồng làm phim trong `CLAUDE.md` theo contracts/skill-integration.md (`job start/step/run/done`, in link giao diện)

## Phase 6: Polish

- [ ] T030 [P] Cập nhật `README.md` (giao diện: `deps ui`, `ui`, ảnh chụp mô tả), `CLAUDE.md` (cấu trúc: `tools/studio/`, `.studio/`, `tests/ui/`)
- [ ] T031 [P] Kiểm thử trình duyệt tuỳ chọn `tests/ui/test_browser.py`: dùng `playwright-core` của thư viện mở trang Việc và trang Duyệt, bấm Đồng ý; bỏ qua nếu không có trình duyệt
- [ ] T032 Chạy `sh tests/ui/run.sh`, `sh tests/run.sh`, `sh tests/learn/run.sh`; chạy thật máy chủ trong phiên này và chụp các trang để xem; ghi kết quả (đạt / chưa chạy được kèm lý do) vào cuối file này

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 → US2 → US3 → Polish.
- US2 cần `jobs.py` và `server.py` của US1; US3 chỉ cần Phase 2 và khung giao diện (T019).
- T025 và T029 (skill, CLAUDE.md) làm sau khi CLI tương ứng chạy.

## Parallel Opportunities

- T004 ∥ T005; T011 ∥ T012; T013 ∥ T014 ∥ T015; T020 ∥ T021; T030 ∥ T031.
- Các task cùng sửa `server.py`, `studio_cli.py` hay `app.js` làm tuần tự.

## Implementation Strategy

MVP = Phase 1 + 2 + US1 (thấy việc chạy trên giao diện). Sau đó là US2 (duyệt, giá trị lớn nhất), rồi US3 (xem kết quả).
