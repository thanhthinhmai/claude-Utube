# Tasks: Một model Claude cho cả xưởng

**Input**: `specs/024-one-claude-model/` (spec.md, plan.md, quickstart.md)

**Tests**: có (spec FR-011, SC-002, SC-003 đòi test tự động).

## Phase 1: Setup

- [X] T001 Tạo `tools/models.json`: `{"_note": "The studio's Claude models (specs/024). Every Claude call uses the one chosen model; add a model here with its price in tools/studio/studio/db.py price_table.", "default": "claude-opus-5-5", "allowed": {"claude-opus-5-5": "Opus 5.5"}}`

## Phase 2: Foundational

- [X] T002 Tạo `tools/filmcheck/models.py` (chỉ thư viện chuẩn): `allowed() -> dict`, `default() -> str`, `resolve(value, warn=True) -> str` (ngoài danh sách → mặc định, cảnh báo một dòng stderr `model X is not allowed; using claude-opus-5-5`), `current()` (thứ tự `STUDIO_MODEL` → `.studio/config.json` `model` → mặc định, qua `resolve`), `set_model(value)` (ValueError ngoài danh sách; ghi `.studio/config.json` giữ các khoá khác), `helper_env(env, model)` (đặt `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`), `main_model(out, want)` (plan R4). Đường dẫn config dùng `STUDIO_ROOT` như `editor.config_path()`.

## Phase 3: User Story 1 - Mọi lượt gọi dùng đúng model (P1) 🎯 MVP

**Goal**: mọi lượt gọi Claude truyền model từ cài đặt chung; lượt phụ cùng model; kết quả ghi model chính.

**Independent Test**: `sh tests/filmcheck/run.sh` (test_one_model) đạt; một lượt thật có tìm web chỉ có `claude-opus-5-5` trong `modelUsage`.

- [X] T003 [P] [US1] Viết `tests/filmcheck/test_one_model.py`: (a) `models.resolve/current/set_model/main_model/helper_env` (thứ tự nguồn, giá trị lạ → mặc định + cảnh báo, `editor_model`/`STUDIO_EDITOR_MODEL` bị bỏ qua); (b) hàm quét mã theo plan R7 (±12 dòng) trên `tools/**/*.py` (trừ `.venv`, `license`) → 0 chỗ vi phạm; (c) ca tự kiểm: đoạn mã giả `subprocess.run([claude_bin(), "-p", "hi"])` không có model → hàm quét báo 1 chỗ.
- [X] T004 [US1] Sửa `tools/filmcheck/editor.py`: bỏ `MODELS`, `set_editor_model`, `editor_model`; `model_args()` trả `["--model", models.current()]`; `run()` dùng `models.helper_env(env, want)` và `models.main_model(out, want)`; bỏ `same_model_env`, `main_model`, `HELPER_ENV`, `DEFAULT_MODEL` cục bộ (giữ `read_config`, `config_path`, render setting).
- [X] T005 [P] [US1] Sửa `tools/filmcheck/topics_fit.py`: model qua `editor.model_args()`, lượt phụ qua `models.helper_env`.
- [X] T006 [P] [US1] Sửa `tools/filmcheck/labeler.py`: bỏ `MODEL`, `STUDIO_LABELER_MODEL`; `--model models.current()`, `models.helper_env`, `models.main_model`.
- [X] T007 [US1] Sửa `tools/studio/studio/quotas.py`: đọc `tools/models.json` (đường dẫn `Path(__file__).resolve().parents[2] / "models.json"`), hàm `model()` trả `settings()["model"]` đã chuẩn hoá; `settings()` chuẩn hoá `model` và bỏ khoá `editor_model`; bỏ `EDITOR_MODELS` và kiểm `editor_model` trong `update_settings`.
- [X] T008 [US1] Sửa `tools/studio/studio/db.py`: bỏ `"editor_model": "inherit"` khỏi `SETTINGS_DEFAULT` (giá trị cũ trong DB chỉ bị bỏ qua).
- [X] T009 [US1] Sửa `tools/studio/studio/moderation.py`: dùng `quotas.model()` cho `claude -p` và `messages.create`; lượt `claude -p` đặt biến lượt phụ cùng model (qua tham số `env_extra` mới của `claude_plan.run` trong `tools/studio/studio/claude_plan.py`).
- [X] T010 [US1] Sửa `tools/runner/worker.py`: `STUDIO_MODEL`, `.input.json` `model`, hai biến lượt phụ = `quotas.model()`; bỏ `STUDIO_EDITOR_MODEL`. Sửa `tools/runner/agent.py`: `model=os.environ.get("STUDIO_MODEL") or inp.get("model")` không còn `None` (lỗi rõ nếu thiếu).
- [X] T011 [US1] Sửa test cũ theo hành vi mới: `tests/filmcheck/test_foundation.py` (ca editor_model → models), `tests/filmcheck/test_cli.py` (ca `STUDIO_EDITOR_MODEL`), `tests/filmcheck/test_labeler.py`, `tests/learn/test_shots.py`, `tests/online/test_script_step.py`, `tests/online/test_quality_view.py`. Chạy `sh tests/filmcheck/run.sh`, `sh tests/learn/run.sh`.

**Checkpoint**: US1 tự test được.

## Phase 4: User Story 2 - Chọn model ở một chỗ (P2)

**Goal**: một ô chọn trong Settings, lệnh `config model`, từ chối giá trị lạ.

**Independent Test**: test online Settings và test CLI đạt; Settings chỉ có một ô chọn model.

- [X] T012 [US2] Sửa `tools/studio/studio/quotas.py` `update_settings`: `model` ngoài danh sách → 422 `model must be one of: claude-opus-5-5`; `editor_model` → 422 (không còn trong `RANGES`). Sửa `tools/studio/studio/api_online.py` `GET /admin/settings`: thêm `models: [{id, name}]`.
- [X] T013 [US2] Sửa `tools/studio/studio/web/app.js`: `model` là ô chọn lấy từ `s.models`; bỏ dòng `editor_model` trong `SETTING`.
- [X] T014 [US2] Sửa `tools/filmcheck/cli.py`: lệnh `config model [value]` (không đối số in model; hợp lệ ghi và in `model: <id>`; không hợp lệ stderr + mã 2); bỏ `config editor-model`.
- [X] T015 [US2] Test: `tests/online/test_admin.py` (thay `test_editor_model_setting` bằng ca model: GET có `models`, PUT haiku → 422, PUT `editor_model` → 422, member → 403); thêm ca CLI `config model` vào `tests/filmcheck/test_one_model.py`. Chạy `sh tests/online/run.sh`.

## Phase 5: Polish

- [X] T016 [P] Cập nhật `CLAUDE.md` (`config model …` thay `config editor-model …`) và ghi chú "thay bởi specs/024" trong `specs/003-studio-ui/contracts/cli.md`, `specs/010-script-review-qc/contracts/cli.md`.
- [X] T017 Chạy đủ các bộ test (`tests/run.sh`, `tests/filmcheck`, `tests/learn`, `tests/ui`, `tests/online`) và quickstart §2; ghi kết quả vào cuối file này.
- [X] T018 Kiểm SC-001 bằng một lượt thật nhỏ (`claude -p` có WebSearch qua `models.helper_env`, như plan R2) và một vòng `script review` nếu người dùng đồng ý tốn token; ghi kết quả.

## Dependencies

- T001 → T002 → US1 (T003–T011) → US2 (T012–T015) → Polish.
- Trong US1: T004 trước T005/T006 (dùng `editor.model_args`); T007 trước T009, T010.
- [P]: T003 song song với T004; T005 ‖ T006; T016 bất kỳ lúc nào sau T014.

## Implementation Strategy

MVP = US1 (luật "chỉ một model" có hiệu lực ở mọi lượt gọi). US2 thêm chỗ chọn; khi danh sách chỉ có Opus 5.5 thì US2 chủ yếu là giao diện và từ chối giá trị lạ.

## Ngoài 024 (cùng nhánh, đã làm trước spec)

- Việc A: `job run` ghi log và tiến độ N/M trong lúc chạy, trả bước cho lệnh dài khi lệnh ngắn chạy song song kết thúc (`tools/studio/studio_cli.py`, `tools/studio/studio/jobs.py`, test `tests/ui/test_cli_events.py::test_job_run_live_log_progress_and_step_handback`).

## Kết quả (2026-11-18)

- Test: `tests/run.sh` 87/87 · `tests/filmcheck` 209 OK (có `test_one_model`: quét mã 0 chỗ vi phạm, ca tự kiểm bắt 1 chỗ) · `tests/learn` 42 OK · `tests/ui` 93 OK + node 33/33 · `tests/online` 196 OK. **Đạt.**
- Quickstart §2: `config model` in `claude-opus-5-5`; `config model claude-haiku-5-5` → mã 2, `.studio/config.json` không đổi. **Đạt.**
- SC-001 (lượt thật nhỏ qua `editor.model_args` + `models.helper_env`, có 1 lần WebSearch): `modelUsage` = `{claude-opus-5-5: 14 329 vào / 1 068 ra}`, ghi `claude-opus-5-5`. **Đạt.** Một vòng `script review` đầy đủ chưa chạy (tốn token hơn; chờ phim kế tiếp).
- SC-004: test trình duyệt thấy ô `#s-model` có đúng 1 lựa chọn "Opus 5.5", 0 ô `#s-editor_model`. **Đạt.**
- Việc A (cùng nhánh): `job run` ghi log mỗi 3 s, tiến độ N/M (local qua `runs`, online qua lệnh step của proxy, nhịp sống giữ tiến độ), trả bước khi lệnh ngắn song song kết thúc; tối đa 50 dòng mỗi lần gửi.
