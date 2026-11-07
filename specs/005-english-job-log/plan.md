# Implementation Plan: Bước và nhật ký việc bằng tiếng Anh trên Film Studio

**Branch**: `005-english-job-log` | **Date**: 2026-11-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-english-job-log/spec.md`

## Summary

Đổi các chuỗi tiếng Việt mà xưởng tự ghi vào việc (bước, nhật ký) sang tiếng Anh theo bảng FR-001, và đổi chỉ dẫn ghi bước trong CLAUDE.md, skill học phong cách và contract 003 sang danh sách chuẩn (FR-002, FR-003, FR-005). Chỉ đổi chữ: không đổi dữ liệu, API hay mã lỗi. Mức **Nhẹ**: không cần `research.md`, `data-model.md`, `contracts/` mới.

## Technical Context

**Language/Version**: Python 3 (tools/studio), Markdown (tài liệu)

**Primary Dependencies**: không thêm

**Storage**: `.studio/jobs/*.json`, `.studio/reviews/*.json`: định dạng giữ nguyên; việc cũ không chuyển đổi

**Testing**: `sh tests/ui/run.sh` (unittest), cùng `sh tests/run.sh` và `sh tests/learn/run.sh`

**Target Platform**: Linux, macOS (như 003)

**Project Type**: công cụ CLI và giao diện web cục bộ

**Performance Goals / Constraints / Scale**: không áp dụng (chỉ đổi chữ)

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec là nguồn sự thật | ✓ Mọi chỗ đổi đều theo FR-001 đến FR-005 |
| II. Không đoán | ✓ Phạm vi do người dùng chốt; spec không còn chỗ cần hỏi |
| III. MVP, theo user story | ✓ Một story P1 |
| IV. Đo được | ✓ SC-001 có test tự động kiểm không còn chữ tiếng Việt |
| V. Đơn giản | ✓ Thay chuỗi tại chỗ, không thêm lớp dịch hay tệp ngôn ngữ |
| VI. Thư viện gốc giữ nguyên | ✓ Không đụng `lib/` |
| VII, VIII, IX | Không liên quan |

Kiểm lại sau thiết kế: vẫn đạt, không có vi phạm.

## Thay đổi theo tệp

| Tệp | Đổi | Theo |
|---|---|---|
| `tools/studio/studio/jobs.py` | bước đầu `Starting`, nhật ký `Job started`; bước cuối `Done` / `Failed` / `Stopped` | FR-001 |
| `tools/studio/studio/reviews.py` | `KINDS` → `review 1` / `review 2`; `LABEL` → Approve, Request changes, Accept anyway, Stop (trùng `DECISION` trong `web/app.js`); bước `Waiting for review n`; nhật ký `Review n requested`, `Review n: <label> (via UI\|via chat)[: note]`, `Resumed after review n: <label>` | FR-001 |
| `tools/studio/studio_cli.py` | `(command exited with code N)`; thông báo terminal giữ tiếng Việt | FR-001, FR-004 |
| `tests/ui/test_cli_events.py` | đổi chỗ kiểm `mã 7`; thêm test đủ vòng (start → 3 bước → duyệt qua giao diện và qua chat → `job run` → kết thúc) kiểm từng dòng do xưởng ghi khớp bảng và không có chữ có dấu tiếng Việt | SC-001, SC-003 |
| `CLAUDE.md` | dòng 24–25: danh sách bước làm phim | FR-002 |
| `.claude/skills/style-learn/SKILL.md` | 10 tên bước | FR-003 |
| `specs/003-studio-ui/contracts/skill-integration.md` | thêm bảng dòng xưởng ghi và hai danh sách bước | FR-005 |

Hai chỗ thiết kế đáng chú ý:
- Dòng `Failed`: `job fail` vẫn ghi nội dung lỗi của Claude vào nhật ký như hiện tại; chỉ tên bước đổi thành `Failed` (FR-004).
- Kiểm "không có chữ tiếng Việt" trong test: chuỗi chỉ gồm chữ ASCII (các dòng do xưởng ghi), loại trừ dòng lệnh con in ra và ghi chú người dùng.

## Project Structure

```text
specs/005-english-job-log/
├── spec.md
├── plan.md          # tệp này
├── quickstart.md
├── checklists/requirements.md
└── tasks.md         # /speckit-tasks
```

**Structure Decision**: Không thêm tệp mã nguồn; sửa tại chỗ các tệp ở bảng trên.

## Complexity Tracking

Không có vi phạm hiến pháp.
