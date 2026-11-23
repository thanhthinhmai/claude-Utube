# Data Model: Tiết kiệm token cho agent của việc

## Tài khoản giữ của việc (bộ nhớ của proxy)

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `job_id` | str | khoá |
| `slot` | int | slot Claude đang giữ |

- **Sinh**: lượt gọi thành công đầu tiên (mã < 400) của việc qua một slot.
- **Đổi**: lượt gọi thành công qua slot khác (sau 429, lỗi đăng nhập, hoặc slot giữ không còn trong `usable()`).
- **Mất**: dọn định kỳ (≤ 60 s) khi tài liệu việc không còn hoặc có `status` thuộc `jobs.FINAL`; hoặc proxy khởi động lại.
- Không lưu xuống đĩa.

## Tệp trạng thái trước khi gọn: `<thư mục việc>/.compact-state.md`

Markdown, ghi đè mỗi lần gọn, ≤ 8 KB (cắt bớt danh sách nếu vượt):

```text
# Before compaction (<ISO time>, auto|manual)
- Last step: <bước> | unknown
## Recently changed files (newest first, max 20)
- films/<phim>/<tệp>  <HH:MM:SS>
## Checks (films/<phim>/checks.json)
- <tầng>: pass|fail (<số lỗi> errors)
```

- "Last step" lấy từ lệnh `job step <mã> "<bước>"` cuối cùng trong transcript (đọc tối đa 2 MB cuối).
- Không có phim hoặc `checks.json` thì ghi "none".
