# Implementation Plan: Kiểm lỗi kiểu cho code giao diện

**Branch**: `006-app-ts-check` | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-app-ts-check/spec.md`

## Summary

Thêm `// @ts-check` vào đầu `app.js` và sửa 27 lỗi kiểu bằng chú thích JSDoc (ép kiểu phần tử DOM, kiểu cho bảng route, lỗi có `code`), không đổi logic. Thêm một test Python trong `tests/ui/` gọi `npx typescript@5.6.3 tsc` để kiểm `app.js`. Test tự bỏ qua khi không có `npx` hoặc không tải được TypeScript. Mức **Nhẹ**: không cần `research.md`, `data-model.md`, `contracts/`.

## Technical Context

**Language/Version**: JavaScript ES2022 chạy thẳng trong trình duyệt; Python 3 cho test

**Primary Dependencies**: TypeScript 5.6.3, chỉ dùng làm công cụ kiểm. Test gọi qua `npx -y -p typescript@5.6.3`, bản tải về nằm trong bộ nhớ đệm npm `~/.npm`, không nằm trong repo

**Storage**: không áp dụng

**Testing**: `sh tests/ui/run.sh` (unittest), thêm `tests/ui/test_typecheck.py`

**Target Platform**: Linux, macOS; VS Code dùng bộ kiểm TypeScript có sẵn

**Project Type**: giao diện web cục bộ, không có bước biên dịch

**Constraints**: không thêm `package.json`, `tsconfig.json` hay `node_modules/` vào repo (FR-005); kết quả ổn định nhờ ghim phiên bản

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec là nguồn sự thật | ✓ Theo FR-001 đến FR-005 |
| II. Không đoán | ✓ Cách kiểm do người dùng chốt |
| III. MVP | ✓ Một story P1 |
| IV. Đo được | ✓ SC-001: 0 lỗi, kiểm bằng test |
| V. Đơn giản | ✓ Một dòng `@ts-check`, chú thích tại chỗ, một test; không có tệp cấu hình |
| VI. Thư viện gốc | ✓ Không đụng `lib/`; không dùng `node_modules` của thư viện cho TypeScript |
| VII, VIII, IX | Không liên quan |

Kiểm lại sau thiết kế: đạt.

## Thiết kế

**Sửa `tools/studio/studio/web/app.js`** (FR-001, FR-002). Thêm dòng 1 `// @ts-check`. Sửa 27 lỗi theo nhóm:

| Nhóm lỗi | Số lỗi | Cách sửa |
|---|---|---|
| `querySelector`/`getElementById` trả `Element`/`HTMLElement` nhưng dùng `.value`, `.dataset`, `.onclick`, `.disabled`, `.src` | ~22 | ép kiểu bằng JSDoc, ví dụ `/** @type {HTMLInputElement} */ (…)`; `querySelectorAll` có kiểu `NodeListOf<HTMLElement>` |
| `e.target` là `EventTarget` | 2 | ép sang `HTMLElement` hoặc `HTMLInputElement` |
| lỗi API có thêm `code` | 1 | `@typedef` cho lỗi kèm `code`, hoặc ép kiểu khi tạo |
| bảng route là mảng hỗn hợp `[RegExp, hàm]` | 2 | `@type {Array<[RegExp, (id: string) => Promise<void>]>}` |
| gán số cho thuộc tính chữ (dòng 405) | 1 | `String(…)` hoặc dùng thuộc tính đúng kiểu, giữ nguyên kết quả hiển thị |

Không bật chế độ `strict`.

**Thêm `tests/ui/test_typecheck.py`** (FR-003, FR-004). Test làm các việc sau:
- Bỏ qua kèm lý do nếu không tìm thấy `npx`.
- Chạy trong một thư mục tạm, để không đọc hay ghi cấu hình nào trong repo: `npx -y -p typescript@5.6.3 tsc --noEmit --allowJs --checkJs --target es2022 --lib es2022,dom,dom.iterable <đường dẫn app.js>`, giới hạn 180 s.
- Mã 0: đạt.
- Mã khác 0 và đầu ra có `error TS`: thất bại, in các dòng lỗi (có số dòng).
- Mã khác 0 mà không có `error TS` (không tải được), hoặc quá giờ: bỏ qua kèm lý do.

VS Code tự đọc `// @ts-check`, không cần `jsconfig.json`.

## Project Structure

```text
specs/006-app-ts-check/
├── spec.md · plan.md · quickstart.md · checklists/requirements.md
└── tasks.md          # /speckit-tasks
tools/studio/studio/web/app.js     # sửa
tests/ui/test_typecheck.py         # mới
```

**Structure Decision**: Sửa một tệp, thêm một tệp test.

## Complexity Tracking

Không có vi phạm hiến pháp.
