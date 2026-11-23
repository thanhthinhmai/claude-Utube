# Implementation Plan: Tiết kiệm token cho agent của việc

**Branch**: `030-agent-token-savings` | **Date**: 2026-11-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/030-agent-token-savings/spec.md`

**Mức quy trình**: Nhẹ (3 tệp code + test; không đổi dữ liệu hay API dùng chung). Bỏ `research.md` và `contracts/`.

## Summary

1. **Proxy giữ tài khoản cho mỗi việc** (`tools/runner/proxy.py`): một bảng trong bộ nhớ `job → slot`. Ở mỗi lượt gọi, slot đang giữ (nếu còn trong `claude_plan.usable()`) được đưa lên đầu danh sách thử; lượt thành công ghi slot vào bảng; 429 hoặc lỗi đăng nhập thì thử slot kế tiếp như hiện nay và slot mới thành slot giữ. Việc chưa giữ slot nào: ở chế độ `auto`, ưu tiên slot đang được ít việc giữ nhất rồi mới tới số token 5 giờ (tránh hai việc bắt đầu cùng lúc dồn vào một slot); chế độ `manual` giữ nguyên thứ tự tay. Bảng tự dọn mỗi ≤ 60 giây các việc đã ở trạng thái kết thúc (worker là tiến trình khác nên không gọi trực tiếp được).
2. **Worker truyền ngưỡng gọn và giới hạn đầu ra** (`tools/runner/worker.py`): thêm `CLAUDE_CODE_AUTO_COMPACT_WINDOW` (mặc định 300000, đọc từ `STUDIO_AUTO_COMPACT_WINDOW`) và `BASH_MAX_OUTPUT_LENGTH` (mặc định 20000, đọc từ `STUDIO_BASH_MAX_OUTPUT`) vào `env` của việc; giá trị sai thì dùng mặc định và ghi cảnh báo.
3. **Agent có hướng dẫn gọn và hook trước khi gọn** (`tools/runner/agent.py`): nối mục "When the conversation is compacted" vào `rules()`; thêm `HookMatcher` cho `PreCompact` gọi `save_compact_state()` ghi `WORK/.compact-state.md` (≤ 8 KB): thời điểm, `trigger`, bước gần nhất (dòng `job step <mã> "<bước>"` cuối cùng trong transcript), 20 tệp đổi gần nhất trong `WORK/films/` kèm giờ, tóm tắt `checks.json` của phim (tầng nào đạt/chưa, số lỗi). Mọi lỗi bị bắt, ghi stderr, trả `{}`.

## Technical Context

**Language/Version**: Python 3.12 (venv `tools/.venv`)

**Primary Dependencies**: FastAPI + httpx (proxy), `claude_agent_sdk` 0.2.179 (`HookMatcher`, sự kiện `PreCompact` có `transcript_path`, `trigger`)

**Storage**: Không thêm bảng. Bảng `job → slot` nằm trong bộ nhớ của tiến trình proxy; tệp trạng thái nằm trong thư mục việc.

**Testing**: `unittest` trong `tests/online/` (Studio giả, Claude giả `fake_claude`, `test_rotation.py`, `test_agent_thrift.py`)

**Target Platform**: Linux (VPS, container của việc) và app desktop chế độ trên máy (cùng worker/proxy/agent)

**Project Type**: dịch vụ web + bộ chạy việc

**Performance Goals**: Đưa slot giữ lên đầu danh sách: O(số slot); dọn bảng ≤ 1 lần/60 s. Hook ghi trạng thái < 1 s.

**Constraints**: Không đổi model (specs/024), giới hạn token, cách tính token, đường dự phòng khoá API.

**Scale/Scope**: Vài tài khoản, vài việc chạy cùng lúc.

## Constitution Check

| Nguyên tắc | Kiểm | Kết quả |
|---|---|---|
| I. Spec là nguồn sự thật | spec.md có, plan theo spec | Đạt |
| II. Không đoán | Spec không còn `[NEEDS CLARIFICATION]`; chỗ chọn (ưu tiên slot ít việc giữ) ghi rõ ở đây | Đạt |
| III. MVP theo user story | P1 (giữ tài khoản) tự chạy và tự test được; P2, P3 độc lập | Đạt |
| IV. Đo được, có test | SC-001…006 có test tự động; bài thật tốn tiền không chạy, nói rõ | Đạt |
| V. Đơn giản | Bảng trong bộ nhớ, không đổi schema; một hàm hook | Đạt |
| VI. Thư viện gốc giữ nguyên | Không đụng `lib/` | Đạt |
| VII–IX, bản quyền, phần mềm hệ thống | Không liên quan | Đạt |

Kiểm lại sau thiết kế: không đổi.

## Project Structure

### Documentation (this feature)

```text
specs/030-agent-token-savings/
├── spec.md
├── plan.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
tools/runner/
├── proxy.py            # bảng job → slot, thứ tự thử, dọn bảng
├── worker.py           # hai biến môi trường mới cho việc
└── agent.py            # mục hướng dẫn gọn trong rules(), hook PreCompact, save_compact_state()

tests/online/
├── test_rotation.py    # thêm: giữ slot, đổi khi 429, phân tải việc mới, dọn bảng
└── test_agent_thrift.py  # thêm: env của việc, mục hướng dẫn gọn, tệp trạng thái
```

**Structure Decision**: sửa tại chỗ ba tệp của bộ chạy việc; test thêm vào hai tệp test có sẵn đúng chủ đề.

## Rủi ro

- `test_sc105_ten_jobs_spread_evenly` (chênh ≤ 20% giữa 2 tài khoản) có thể lệch hơn khi việc giữ slot; ưu tiên "slot ít việc giữ nhất" cho việc mới là để giữ phân tải. Nếu test vẫn lệch, ghi số đo và chỉnh thứ tự chọn, không nới ngưỡng test.
- `test_sc104` mong `vias[:2] == ["plan:1", "plan:2"]`: với hành vi mới vẫn đúng (lượt 2 của slot 1 bị 429 → chuyển sang slot 2 và ở lại).

## Complexity Tracking

Không có.
