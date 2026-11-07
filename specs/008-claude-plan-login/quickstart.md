# Quickstart: kiểm chứng 008

## Test tự động (không cần mạng, không tốn hạn mức)
```sh
sh tests/run.sh && sh tests/learn/run.sh && sh tests/ui/run.sh && sh tests/online/run.sh
```
Các test online mới dùng:
- một **Claude Code giả** (`tests/online/fake_claude`), đặt qua `STUDIO_CLAUDE_BIN`, giả `auth login` (in URL, đợi mã), `auth status --json`, `auth logout`, `-p`, và ghi `.credentials.json` giả;
- **dịch vụ Claude giả** của 007 sau bộ chuyển tiếp, thêm cách trả `429` của gói (kèm giờ dùng lại) và `401` theo từng mã truy cập.

| Kiểm | Tiêu chí |
|---|---|
| Đăng nhập, dán mã đúng hoặc sai, đăng xuất, thêm tài khoản thứ 6, xoá slot 1 | US1 #2–4, US2 #1, #7 |
| Tìm mã truy cập giả trong `/data/jobs`, nhật ký, phản hồi API, môi trường và danh sách gắn của container | SC-103 = 0 lần |
| 2 tài khoản, 10 việc giả như nhau | SC-105: token lệch ≤ 20% |
| Tài khoản 1 trả `429` của gói giữa việc | SC-104: việc vẫn xong; slot 1 thành `limited` kèm `rest_until` |
| `401` không làm mới được | `needs_signin` + đúng 1 thư `claude_signin` |
| Hết tài khoản, có hoặc không có khoá API | FR-110: đi qua khoá; không có khoá thì lỗi do xưởng sau ≤ 15 giây, trả lượt, lý do có giờ |
| `POST /auth/signup` · lời mời đúng, hết hạn, thu hồi, đã dùng | SC-106 |
| Tổng token của `/admin/usage` so với tổng bảng Call | SC-107 = lệch 0 |
| Tài khoản thường gọi `/admin/claude*` | `403` |

## Kiểm bằng tay với tài khoản thật (tasks T001, rồi bài chạy thật)
1. `sh bin/studio online up` với `deploy/.env` **không** có `ANTHROPIC_API_KEY`.
2. `sh bin/studio online admin <email>`, đăng nhập, mở Admin → Claude accounts: thấy cảnh báo "No Claude account signed in".
3. Bấm Sign in → đăng nhập trên trang Claude → dán mã. Trong ≤ 10 giây thấy email và gói (SC-101: cả lượt dưới 2 phút).
4. Giao một phim 20 giây. Phim xong, đạt −14 ±1 LUFS, đỉnh ≤ −1 dB, kiểm đọc chữ đạt (SC-102). Trang mức dùng hiện token theo `plan:1` và 0 USD.
5. `sh tests/online/live.sh` (đã sửa để in token thay cho tiền) để ghi số token thực tế, rồi chỉnh `job_token_cap` nếu cần (research R7).
