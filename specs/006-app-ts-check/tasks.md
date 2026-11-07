# Tasks: Kiểm lỗi kiểu cho code giao diện

**Input**: `specs/006-app-ts-check/` (spec.md, plan.md, quickstart.md)

**Tests**: có, theo FR-003.

## Phase 1: Setup và Phase 2: Foundational

Không có việc: không thêm gói hay tệp cấu hình (FR-005).

## Phase 3: User Story 1 - Lỗi kiểu lộ ra trước khi chạy giao diện (P1) 🎯 MVP

**Goal**: `app.js` có `// @ts-check` và 0 lỗi kiểu; test kiểm kiểu chạy trong bộ test giao diện.

**Independent Test**: `tools/.venv/bin/python -m unittest discover -s tests/ui -t tests/ui -k typecheck -v` đạt. Thêm tạm `document.title = 5;` thì test thất bại.

- [X] T001 [US1] Tạo `tests/ui/test_typecheck.py`, lớp `TypeCheck`, test `test_app_js_has_no_type_errors`. Test làm như sau:
  - `shutil.which("npx")` không có thì `skipTest`.
  - Chạy `npx -y -p typescript@5.6.3 tsc --noEmit --allowJs --checkJs --target es2022 --lib es2022,dom,dom.iterable <REPO>/tools/studio/studio/web/app.js` với `cwd` là `tempfile.TemporaryDirectory()`, `timeout=180`.
  - `TimeoutExpired` thì skip.
  - Mã 0 thì đạt.
  - Có `error TS` trong đầu ra thì `fail` với các dòng lỗi.
  - Mã khác 0 mà không có `error TS` thì `skipTest("không tải được TypeScript: …")` (FR-003, FR-004).

  Chạy test phải thất bại với 27 lỗi trước T002.
- [X] T002 [US1] Trong `tools/studio/studio/web/app.js`, thêm dòng đầu `// @ts-check`. Sửa toàn bộ lỗi kiểu bằng chú thích JSDoc theo bảng "Thiết kế" trong `specs/006-app-ts-check/plan.md`:
  - ép kiểu DOM bằng `/** @type {HTMLInputElement} */ (…)`, `HTMLElement`, `HTMLButtonElement`, `HTMLImageElement`;
  - `@typedef` hoặc ép kiểu cho lỗi có `code`;
  - kiểu cho bảng route;
  - `String(…)` chỗ gán số cho thuộc tính chữ.

  Không đổi logic hay chữ hiển thị, không bật `strict` (FR-001, FR-002). Xong khi T001 đạt.

**Checkpoint**: T001 đạt.

## Phase 4: Polish

- [X] T003 Chạy `sh tests/ui/run.sh` (gồm test trình duyệt), `sh tests/run.sh`, `sh tests/learn/run.sh`, rồi đối chiếu:
  - SC-002: thử `document.title = 5;` thì test thất bại; sau đó xoá dòng đó.
  - SC-004: `git status` chỉ có `app.js`, `tests/ui/test_typecheck.py` và `specs/006-app-ts-check/`.

## Dependencies

T001 → T002 → T003 (cùng chuỗi, không song song).

## Implementation Strategy

Test đỏ (T001) → sửa đến xanh (T002) → kiểm toàn bộ (T003).
