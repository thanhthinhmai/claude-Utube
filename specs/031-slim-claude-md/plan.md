# Implementation Plan: CLAUDE.md gọn

**Branch**: `031-slim-claude-md` | **Date**: 2026-11-23 | **Spec**: [spec.md](spec.md)

**Mức quy trình**: Nhẹ (chỉ tài liệu chỉ dẫn; không đổi code). Bỏ research, data-model, contracts.

## Summary

Tách `CLAUDE.md` (35.730 byte) thành bốn tệp, chép nguyên văn từng đoạn, rồi kiểm bằng script:

| Tệp | Nội dung |
|---|---|
| `CLAUDE.md` (gốc, ≤ 9 KB) | giới thiệu; bảng luồng (Làm phim → skill); 014 chạy app trên máy; 015–018 mỗi spec ≤ 2 dòng + trỏ `desktop/CLAUDE.md`; luật "không sửa `lib/`"; Luật bắt buộc; Chọn mức quy trình; Quy trình đầy đủ; bản đồ thư mục một dòng mỗi mục, trỏ `tools/CLAUDE.md` và `sh bin/studio --help` |
| `.claude/skills/film-make/SKILL.md` | frontmatter `name`, `description`; nguyên văn bước 1–5, 2a, 2b, 3, 3a, 3b, 3c; dòng lệnh `bin/studio` của "Cấu trúc" |
| `desktop/CLAUDE.md` | nguyên văn mục 015, 016, 017, 018 |
| `tools/CLAUDE.md` | nguyên văn các dòng `tools/studio/`, chế độ online, `tools/filmcheck/`, `tools/render/`, `tools/style-learn/` của "Cấu trúc"; lệnh test |

Kiểm: `specs/031-slim-claude-md/check_split.py` đọc bản cũ từ `git show main:CLAUDE.md`, bỏ tiêu đề và dòng trống, kiểm từng dòng có nguyên văn trong một trong bốn tệp mới (dòng được thay bằng lời trỏ ghi trong danh sách ngoại lệ có lý do), in số dòng thiếu và kích thước `CLAUDE.md`.

## Technical Context

**Language/Version**: Markdown; script kiểm Python 3 (chỉ thư viện chuẩn)

**Testing**: script kiểm + 5 bộ test của xưởng (không có test nào đọc nội dung `CLAUDE.md`, đã grep)

**Constraints**: không đổi `tools/runner/JOB.md`, `agent.py`; agent online/app không nạp skill của dự án (gọi skill theo đường dẫn), nên skill mới không ảnh hưởng tới họ

## Constitution Check

| Nguyên tắc | Kết quả |
|---|---|
| I. Spec trước | Đạt |
| II. Không đoán | Đạt: không còn chỗ mơ hồ |
| III. P1 tự test được | Đạt |
| IV. Đo được | Đạt: kích thước byte, script đối chiếu, grep, test |
| V. Đơn giản | Đạt: chép nguyên văn, không viết lại |
| VI. Không sửa `lib/` | Đạt, và luật này giữ ở `CLAUDE.md` gốc |

## Project Structure

```text
CLAUDE.md                               # gọn
.claude/skills/film-make/SKILL.md       # mới
desktop/CLAUDE.md                       # mới
tools/CLAUDE.md                         # mới
.claude/skills/style-learn/SKILL.md     # đổi một tham chiếu
specs/031-slim-claude-md/check_split.py # script kiểm
```

## Complexity Tracking

Không có.
