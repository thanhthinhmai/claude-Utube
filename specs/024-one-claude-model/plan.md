# Implementation Plan: Một model Claude cho cả xưởng

**Branch**: `024-one-claude-model` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/024-one-claude-model/spec.md`

**Mức**: Nhẹ (đổi một cài đặt dùng chung và API Settings; bỏ `research.md`, `contracts/`, `data-model.md` riêng: các quyết định và hợp đồng nhỏ nằm ngay trong plan này).

## Summary

Danh sách model được phép nằm ở **một** tệp `tools/models.json` (giống `tools/asr.json` của specs/020), đọc bởi một module nhỏ `tools/filmcheck/models.py` (công cụ phim, chat) và bởi `tools/studio/studio/quotas.py` (online/app, đọc thẳng tệp JSON, không import chéo). Mọi lượt gọi Claude lấy model qua `models.current()` (công cụ phim) hoặc `quotas.model()` (máy chủ), luôn truyền `--model`/`model=` tường minh và đặt `ANTHROPIC_DEFAULT_HAIKU_MODEL` + `ANTHROPIC_SMALL_FAST_MODEL` bằng cùng model để lượt phụ của Claude Code (tìm web, tóm tắt) không xuống Haiku. Bỏ cài đặt `editor_model` ở mọi nơi. Settings đổi ô chữ "Claude model" thành ô chọn lấy từ danh sách máy chủ trả về. Lệnh chat `config model [<id>]` thay `config editor-model`. Một test quét mã chặn chỗ gọi Claude mới không qua cài đặt chung.

## Technical Context

**Language/Version**: Python 3.12 (công cụ, máy chủ FastAPI, worker), JavaScript thuần (giao diện `web/app.js`)

**Primary Dependencies**: Claude Code CLI (`claude -p`), Claude Agent SDK (agent online), `anthropic` SDK (duyệt ý tưởng bằng khoá API dự phòng); không thêm gói

**Storage**: `tools/models.json` (vào git); cài đặt online trong SQLite `settings` (khoá `model` đã có; bỏ `editor_model`); chat: `.studio/config.json` khoá `model`

**Testing**: `unittest` trong `tests/filmcheck`, `tests/online`, `tests/learn`, `tests/ui`; một lượt thật có tìm web cho SC-001 (tốn một ít token, chạy tay)

**Target Platform**: Linux/WSL2, macOS (app), container online

**Project Type**: công cụ dòng lệnh + web app nội bộ

**Performance Goals**: không đổi

**Constraints**: không sửa `lib/` (hiến pháp VI); khoá API và mã không bao giờ in ra

**Scale/Scope**: khoảng 12 file mã, 6 file test, 2 tài liệu (CLAUDE.md, contracts cũ của 003/010 ghi chú "thay bởi 024")

## Quyết định (thay research.md)

- **R1. Một tệp danh sách** `tools/models.json`: `{"_note": …, "default": "claude-opus-5-5", "allowed": {"claude-opus-5-5": "Opus 5.5"}}`. Lý do: máy chủ (`--app-dir tools/studio`) không có `tools/` trên `sys.path`; một tệp JSON đọc được ở cả hai phía, giống `asr.json`. Đã cân nhắc: hằng số Python ở hai nơi (dễ lệch), import chéo `filmcheck` vào máy chủ (thêm phụ thuộc).
- **R2. Lượt phụ cùng model** bằng `ANTHROPIC_DEFAULT_HAIKU_MODEL` và `ANTHROPIC_SMALL_FAST_MODEL`. Đã kiểm 2026-11-18: một lượt `claude -p --model claude-opus-5-5` có WebSearch → `modelUsage` có `claude-haiku-5-5` (12 608 token vào) và Opus; đặt hai biến → chỉ còn `claude-opus-5-5`. Đã cân nhắc: proxy đổi model trong từng yêu cầu (chỉ có ở online, không phủ chế độ chat).
- **R3. Chọn model thứ tự**: biến `STUDIO_MODEL` (worker đặt từ Settings cho container và LocalRunner) → `.studio/config.json` `model` → `default`. Giá trị ngoài danh sách → `default` + một dòng cảnh báo trên stderr (FR-010). `STUDIO_EDITOR_MODEL`, `editor_model` bị bỏ qua (FR-009).
- **R4. Ghi model chính**: `models.main_model(out, want)`: `want` nếu có trong `modelUsage`, không thì model có nhiều `outputTokens` nhất (đã có ở labeler từ specs/021, đưa về một chỗ).
- **R5. Online cài đặt cũ**: `quotas.settings()` trả `model` đã chuẩn hoá (ngoài danh sách → mặc định) và bỏ khoá `editor_model` khỏi kết quả; `update_settings` từ chối `model` ngoài danh sách (422, thông báo nêu danh sách) và từ chối `editor_model` (422 "không có cài đặt") — cài đặt cũ đã lưu trong DB chỉ bị bỏ qua, không cần di chuyển dữ liệu.
- **R6. Biến test của gán cảnh** `STUDIO_LABELER_MODEL` bị bỏ; test dùng Claude giả (`STUDIO_CLAUDE_BIN`) nên không cần đổi model.
- **R7. Test quét mã** (`tests/filmcheck/test_one_model.py`): đọc mọi `.py` trong `tools/` (trừ `.venv`, `tools/license`), tìm nơi khởi chạy Claude: dòng có `"-p"` cạnh `claude_bin(`/`claude` hoặc `ClaudeAgentOptions(` hoặc `messages.create(`; mỗi nơi PHẢI có trong vòng 12 dòng `models.current()`, `model_args()`, `quotas.model()` hoặc `STUDIO_MODEL`. Kèm một ca tự kiểm: một đoạn mã giả thiếu model thì hàm quét báo lỗi (SC-002).

## Hợp đồng (thay contracts/)

**CLI (chat)** — `sh bin/studio config model [<id>]`
- không đối số: in model đang dùng, mã 0;
- `<id>` trong danh sách: ghi `.studio/config.json` `model`, in `model: <id>`, mã 0;
- ngoài danh sách: stderr `model must be one of: claude-opus-5-5`, mã 2, không ghi.
- `config editor-model …`: lệnh bị bỏ; argparse báo lệnh lạ (mã 2).

**API (online/app)**
- `GET /api/v1/admin/settings`: thêm `models: [{"id": "claude-opus-5-5", "name": "Opus 5.5"}]`; `model` luôn là giá trị trong danh sách; không còn `editor_model`.
- `PUT /api/v1/admin/settings` `{"model": X}`: X ngoài danh sách → 422 `model must be one of: claude-opus-5-5`; `{"editor_model": …}` → 422.

**Giao diện**: Settings → General: ô chọn "Claude model" (từ `models`), bỏ "Script editor model". Khối Quality của trang việc vẫn hiện "editor model …" từ kết quả biên tập.

## Constitution Check

| Nguyên tắc | Đánh giá |
|---|---|
| I. Spec là nguồn sự thật | Spec 024 đã duyệt 2026-11-18; spec không nêu công nghệ ngoài tên model là chủ đề |
| II. Không đoán | Phạm vi và danh sách do chủ xưởng chọn; không còn câu hỏi mở |
| III. MVP, chia story | US1 (mọi lượt dùng đúng model) tự test được trước US2 (ô chọn, lệnh) |
| IV. Đo được | SC-001 đo bằng `modelUsage` của một lượt thật; SC-002 bằng test quét; SC-003 bằng test 422/mã 2 |
| V. Đơn giản | Một tệp JSON + một module ~40 dòng; không lớp trừu tượng mới |
| VI. Thư viện giữ nguyên | Không đụng `lib/` |
| VII–IX | Không liên quan |

Kết quả: đạt, không có vi phạm. Sau thiết kế: vẫn đạt.

## Project Structure

### Documentation (this feature)

```text
specs/024-one-claude-model/
├── spec.md
├── plan.md              # file này (có quyết định và hợp đồng)
├── quickstart.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
tools/models.json                     # mới: danh sách, mặc định
tools/filmcheck/models.py             # mới: allowed(), current(), resolve(), helper_env(), main_model(), set_model()
tools/filmcheck/editor.py             # bỏ editor_model/MODELS/set_editor_model; model_args() = ["--model", models.current()]
tools/filmcheck/topics_fit.py         # models.helper_env
tools/filmcheck/labeler.py            # models.current(); bỏ STUDIO_LABELER_MODEL, MODEL
tools/filmcheck/cli.py                # config model [<id>]; bỏ config editor-model
tools/studio/studio/quotas.py         # đọc models.json; model() ; kiểm model; bỏ editor_model
tools/studio/studio/db.py             # bỏ editor_model khỏi mặc định
tools/studio/studio/api_online.py     # GET settings có models
tools/studio/studio/moderation.py     # quotas.model() + helper env cho claude -p
tools/studio/studio/claude_plan.py    # (nếu cần) env lượt phụ cho run()
tools/studio/studio/web/app.js        # ô chọn model; bỏ editor_model
tools/runner/worker.py                # STUDIO_MODEL = quotas.model(); bỏ STUDIO_EDITOR_MODEL
tools/runner/agent.py                 # model = STUDIO_MODEL (luôn có)
tests/filmcheck/test_one_model.py     # mới: quét mã, models.py, CLI
tests/filmcheck/test_foundation.py, test_cli.py, test_labeler.py   # sửa ca editor_model
tests/online/test_admin.py, test_script_step.py, test_quality_view.py  # sửa ca editor_model → model
tests/learn/test_shots.py             # bỏ STUDIO_EDITOR_MODEL
CLAUDE.md                             # config model thay config editor-model
```

**Structure Decision**: giữ cấu trúc hiện có; chỉ thêm `tools/models.json` và `tools/filmcheck/models.py`.

## Complexity Tracking

Không có.
