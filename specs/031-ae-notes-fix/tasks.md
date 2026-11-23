---

description: "Tasks: sửa ghi chú phim After Effects tự động trên app (031)"
---

# Tasks: Sửa ghi chú phim After Effects tự động trên app

**Input**: `specs/031-ae-notes-fix/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Tests**: Có (hiến pháp IV; SC-003, SC-004, SC-006, SC-007 đo bằng test tự động).

**Organization**: theo user story: US1 bộ dựng chung, US2 cầu nối, US3 Fix with Claude, US4 bộ cài, US5 phim AE mới.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Tạo `tools/ae/` (`__init__.py`, `kit/`), `tests/ae/run.sh` (unittest như `tests/filmcheck/run.sh`), `tests/ae/test_ae.py` rỗng; thêm `sh tests/ae/run.sh` vào danh sách test của CLAUDE.md
- [X] T002 Chép bộ dựng chung từ `films/ae-crayon-test/ae/` (ngoài git) vào `tools/ae/kit/`: `lib.jsx`, `chars.jsx`, `scene.jsx`, `persp.jsx`, `build_core.jsx`; thay mọi đường dẫn `E:/claude-utube-ae/crayon10/…` bằng `CU.WORK + "/…"`; ghi nguồn gốc trong đầu mỗi tệp

---

## Phase 2: Foundational

- [X] T003 `tools/ae/film.py`: đọc `film.json` (data-model: `engine`, `fps`, `size`, `shots`, `ae_files`, `audio`); `require_ae(film_dir)` từ chối phim không phải `"ae"` với thông báo nói bộ máy hiện tại (FR-002); thêm `engine` vào `tools/studio/studio/resources.py` `film_summary`
- [X] T004 [P] `tools/ae/bundle.py`: tạo `bundle.tar` gồm `kit/*.jsx` + `ae/<ae_files>` + `entry.jsx` (đặt `CU.WORK` lúc chạy từ biến của app/lệnh, `CU.PROJ`, `CU.build([...])`, ghi `log.txt` với `START`, `CHECK …`, `DONE`) theo contracts/film-ae.md
- [X] T005 [P] `tools/ae/splice.py`: ghép nhiều shot vào video hiện có theo khung trong một lần mã hoá (từ `fixshots.sh`: `trim=start_frame/end_frame`, `setpts=N/FPS/TB`, ép fps, giữ tiếng), đọc mốc từ `shots.json`
- [X] T006a [P] `desktop/test/fake-ae.mjs`: AE giả đóng vai `AfterFX` (đọc entry, ghi `log.txt` với `START`/`DONE`, chế độ treo để thử thời hạn) và `aerender` (sinh mp4 ngắn bằng ffmpeg hoặc chép mp4 mẫu nhỏ ở `desktop/test/vectors/`); dùng chung cho T010 và T019
- [X] T006 [P] Test `tests/ae/test_ae.py`: `film.json` thiếu/sai; phim web bị từ chối; gói chứa đúng tệp và không chép thừa; ghép 2 shot vào video thử 30 khung/giây (ffmpeg testsrc) → đúng số khung, các đoạn ngoài shot trùng khung gốc (PSNR > 40 dB)

---

## Phase 3: User Story 1 - Bộ dựng chung và lệnh `ae` (P1) 🎯 MVP

- [X] T007 [US1] `tools/ae/local.py`: chạy AE trên máy từ dòng lệnh (WSL: `AfterFX.exe -r` + chờ `log.txt`, tắt AfterFX, `aerender` từng comp; macOS: `osascript … DoScriptFile`), đường dẫn từ `~/.config/claude-utube/ae.json`; mã lỗi `ae_missing`, `ae_scripting_off`, `ae_stalled`, `shot_timeout`, `build_error`, `render_error`, `disk_low` (kiểm thư mục làm việc còn ≥ 2 GB trống trước khi dựng) (data-model)
- [X] T008 [US1] `tools/ae/uses.py`: quét `ae/*.jsx` tìm `CU.<hàm>` (kèm bảng gọi trong `kit/`), `shots_using(film_dir, funcs)` (FR-005, R6)
- [X] T009 [US1] `tools/ae/cli.py` + `bin/studio`: `ae build|render|fix|uses|status|new` và `config ae` theo contracts/cli.md; trong việc (`STUDIO_PROXY` có) thì đi qua cầu nối (US2), ngoài việc thì `local.py`; `ae fix` ngoài việc gọi `shotnotes.replace_video`
- [X] T010 [P] [US1] Test: `ae uses` trên phim thử (2 shot gọi hàm khác nhau); `config ae` lưu và đọc; `ae build` với AE giả (biến `STUDIO_AE_FAKE=1` dùng `desktop/test/fake-ae.mjs`) báo `ae_missing` ≤ 10 s khi đường dẫn sai (SC-004)
- [X] T011 [US1] (phim tập luyện, ngoài git) Chuyển `films/ae-crayon-test` sang `film.json` + `ae/shots_a…e3.jsx`; `sh bin/studio ae fix ae-crayon-test S13` so với video hiện có: 4128 khung, 0 khung dưới 30 dB, ≤ 60 s (SC-001, FR-015)

**Checkpoint**: dựng phim AE bằng bộ dựng chung từ dòng lệnh.

---

## Phase 4: User Story 2 - Cầu nối trong app desktop (P1)

- [X] T012 [US2] `tools/ae/aequeue.py` (không đặt tên `queue.py`: trùng mô-đun chuẩn khi chạy `tools/ae/cli.py`): hàng đợi trong `$STUDIO_DATA/ae/requests/<mã>/` (tạo, `next` một lượt mỗi lúc, tiến độ, kết quả, `finish`, nhịp; `claimed/running` không nhịp 60 s → `failed: bridge_lost`); trạng thái `hello` của app desktop (thời điểm, `found`, đường dẫn AE)
- [X] T013 [US2] `tools/studio/studio/server.py`: `/api/v1/ae/bridge/{next,hello}` và `/{id}/{bundle,progress,result/<shot>,finish}` theo contracts/bridge-api.md: chỉ nhận header `X-CU-Bridge` khớp `STUDIO_AE_BRIDGE` (so sánh hằng thời gian) và client 127.0.0.1, bỏ qua phiên/CSRF chỉ cho các đường này
- [X] T014 [US2] `tools/studio/studio/host.py` + `bin/studio app start --bridge <tệp>`: đọc khoá vào `STUDIO_AE_BRIDGE` cho web và proxy (như `--gate`)
- [X] T015 [US2] `tools/runner/proxy.py`: `/internal/ae/requests` (POST multipart gói, GET trạng thái, GET kết quả) cho việc; 409 `ae_unavailable` khi app desktop chưa `hello` trong 30 s (FR-009)
- [X] T016 [US2] `desktop/aebridge.js` (logic thuần, `@ts-check`): tìm AE theo hệ điều hành (chỗ cài mặc định, bản mới nhất), lệnh AfterFX/osascript/aerender, vòng hỏi việc (1 s khi bận, 5 s khi rảnh), khoá một lượt, thời hạn 120 s chờ `START` và 300 s mỗi shot, dừng tiến trình khi quá hạn, `hello` mỗi 10 s; kiểm thư mục làm việc còn ≥ 2 GB trống trước mỗi lượt dựng AE, thiếu thì trả `disk_low`
- [X] T017 [US2] `desktop/main.js` + `desktop/core.js`: tạo khoá 32 byte mỗi lần khởi động vào `CONFIG_DIR/bridge.json`, thêm `--bridge` (Windows: `wslPath`) vào `app start`; chạy cầu nối khi phần lõi sẵn sàng; dừng khi thoát
- [X] T018 [US2] `desktop/ae.html` + `preload.js` + mục khay "After Effects…": hiện đường dẫn tìm được, chọn đường dẫn, nút "Test" (chạy một entry thử ghi `DONE`), lưu vào `config.json` → `ae`
- [X] T019 [P] [US2] `desktop/test/aebridge.test.js` (dùng AE giả của T006a): 10 lần hai yêu cầu cùng lúc → 0 lần song song, yêu cầu 2 bắt đầu ≤ 2 s sau (SC-003); thiếu AE ≤ 10 s; treo → dừng khi hết hạn (SC-004); thư mục làm việc tên "thư mục thử" (tiếng Việt, khoảng trắng) chạy đúng; ổ thiếu chỗ → `disk_low`
- [X] T020 [P] [US2] Test phần lõi `tests/online/test_ae_bridge.py` (cần proxy và mã việc của bộ test online): khoá sai, thiếu, từ IP khác → 403 (SC-006); `next` chỉ giao một yêu cầu; hết nhịp → `bridge_lost`; proxy 409 khi không `hello`

**Checkpoint**: app desktop dựng AE theo yêu cầu của phần lõi.

---

## Phase 5: User Story 3 - Fix with Claude (P2)

- [X] T021 [US3] `tools/filmcheck/shotnotes.py`: `start_lot(film_dir, job, limit=10)` (ghi chú mở theo thời gian trong phim), `end_lot`, `merge_lot_replies(lib_dir, work_dir)` dùng `reply` với `base` mới nhất (R7, FR-012)
- [X] T022 [US3] Loại việc `fix`: `jobs.KINDS`, `quotas.KIND_FIELD` (không tốn lượt phim), `api_online.JobIn.kind`, `make_job` nhánh `fix` (từ `post_revision`); `POST /films/{name}/fix` (409 `in_progress`, 422 `not_ae`/`no_open_notes`, 409 `ae_unavailable`)
- [X] T023 [US3] `tools/runner/worker.py`: `prepare` chép phim vào thư mục việc cho `fix`; `finished` nhánh `fix`: `replace_video` lên kho khi có `out/fix.mp4`, `merge_lot_replies`, `end_lot`; lỗi thì chỉ `end_lot` (FR-014)
- [X] T024 [US3] `tools/runner/agent.py` `fix_prompt`: đúng các bước 3c (liệt kê ghi chú vào nhật ký, mở ảnh, sửa shot hoặc `kit/` rồi `ae uses`, `ae fix` các shot bị ảnh hưởng, `notes reply` từng ghi chú, thử lại tối đa 1 lần khi dựng lỗi)
- [X] T025 [US3] `web/app.js`: nút "Fix with Claude" (gọi `POST /films/{name}/fix`, đường dẫn tới việc), trạng thái "Fixing…" khi có `lot`, ghi chú trong lượt có dấu; nút tắt kèm lý do (không phải AE, không có ghi chú mở, app desktop không có AE); ô "Copy" giữ lại cho dòng lệnh
- [X] T026 [P] [US3] Test `tests/online/test_fix_job.py`: tạo việc, lượt ≤ 10, không tạo trùng; ghi chú thêm trong lúc chạy không vào lượt; `finished` với kết quả giả (video + trả lời) cập nhật kho đúng ghi chú của lượt; việc lỗi giữ video cũ; token ghi trên việc (FR-013)
- [ ] T027 [US3] Chạy thật trên máy (app + app desktop + AE): 3 ghi chú ở 3 shot của `ae-crayon-test` (SC-005), ghi kết quả vào quickstart

**Checkpoint**: bấm "Fix with Claude" là xong một lượt sửa.

---

## Phase 6: User Story 4 - Bộ cài có cầu nối (P3)

- [X] T028 [US4] `.github/workflows/desktop.yml`: bước smoke `ae` (fake core có hàng đợi giả + AE giả) trên Windows và macOS; `desktop/test/fake-core.mjs` thêm `/api/v1/ae/bridge/*` giả
- [X] T029 [US4] `desktop/package.json` / danh sách tệp đóng gói: thêm `aebridge.js`, `ae.html`; `test/package-files.test.js` kiểm có mặt
- [ ] T030 [US4] Hỏi người dùng rồi mới chạy `desktop.yml` trên nhánh (tốn phút chạy, macOS gấp 10); ghi kết quả (SC-007)
- [ ] T031 [US4] Kiểm tay với AE thật: Windows (máy người dùng) và macOS (máy người dùng cung cấp) theo quickstart US4 (SC-009)

---

## Phase 7: User Story 5 - Phim AE mới trên app (P3)

- [X] T032 [US5] `JobIn.engine: "page" | "ae"` cho việc `film`; `make_job` từ chối `"ae"` khi app desktop không có AE (FR-018); `web/app.js` `pageNew`: chọn bộ máy (After Effects tắt kèm lý do khi không có cầu nối)
- [X] T033 [US5] `tools/runner/agent.py` `film_prompt` nhánh `engine == "ae"` theo R8: bước chung giữ nguyên; bước hình: `ae new`, bảng shot, `ae/shots_*.jsx` dùng `tools/ae/kit`, `ae build` (CHECK phải sạch), `ae render`, trộn tiếng giọng + nhạc, `shots.json`; worker `finished` chép phim AE như phim web (không chép `kit/`)
- [X] T034 [P] [US5] Test: việc `film` `engine: "ae"` khi không có cầu nối → 409; `film.json` của phim mới có `engine: "ae"`; `finished` không chép tệp `tools/ae/kit` vào phim (SC-008)
- [ ] T035 [US5] Chạy thật: phim AE mới khoảng 30 giây từ một ý tưởng (SC-008), ghi kết quả vào quickstart

---

## Phase 8: Polish

- [X] T036 CLAUDE.md: luồng làm phim AE (bộ máy, `ae …`, cầu nối, chỉ chế độ app), mục Cấu trúc thêm `tools/ae/`, `desktop/aebridge.js`
- [X] T037 Chạy đủ: `sh tests/run.sh`, `sh tests/render/run.sh`, `sh tests/learn/run.sh`, `sh tests/ui/run.sh`, `sh tests/filmcheck/run.sh`, `sh tests/ae/run.sh`

---

## Dependencies & Execution Order

- Phase 1 → 2 → US1 → US2 → US3; US4 sau US2; US5 sau US2 (và dùng US1).
- Trong mỗi story: test trước, chạy thấy đỏ, rồi mã.
- T030, T031, T027, T035 cần máy thật, AE thật hoặc tốn phút chạy: hỏi người dùng khi tới.

## Parallel Opportunities

- T004, T005, T006 song song; T010 song song với T008; T019, T020 song song; T026, T034 song song với mã của story khác khi đã có nền.

## Implementation Strategy

1. MVP = Phase 1–3 (US1): dựng phim AE bằng bộ dựng chung từ dòng lệnh; kiểm khung phim tập luyện.
2. US2 cầu nối → US3 Fix with Claude (giá trị chính) → US4 bộ cài → US5 phim AE mới.
3. Commit sau mỗi phase; PR khi xong (dựa trên 029).
