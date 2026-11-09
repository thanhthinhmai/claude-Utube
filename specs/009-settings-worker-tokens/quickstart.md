# Quickstart: kiểm 009 bằng tay

Chạy xưởng online trên máy như 008 (web, bộ chuyển tiếp, worker; hoặc `sh bin/studio online up`). Có một Owner và một Member, một tài khoản Claude đã đăng nhập.

## 1. Tab Worker (US1)
1. Owner mở Settings → **Worker**: thấy "Running · idle", "last beat … s ago", bốn ô đếm bằng 0 hoặc đúng số việc.
2. Member giao một phim → tab Worker (tự đọc lại mỗi 5 giây) đổi sang "busy with <việc>", ô "jobs running" lên 1, việc nằm đầu Latest jobs.
3. Dừng worker ở terminal → trong 70 giây trang hiện "Not responding"; quá 10 phút hiện "No worker is running" kèm lệnh bật.
4. Member mở `#/settings/worker` → bị từ chối.

## 2. Mã API của mình (US2)
1. Member mở **Your account → API tokens → New token**: tên "laptop", để mặc định (Member, không dùng lượt, 60/phút, 90 ngày) → mã hiện một lần, có nút Copy.
2. `curl -H "Authorization: Bearer <mã>" <URL>/api/v1/jobs` → danh sách việc của Member.
3. `curl -X POST … /api/v1/jobs` để giao phim → `403 spend_not_allowed`. Tạo mã thứ hai có quyền dùng lượt → giao được, lượt của Member giảm 1.
4. `curl … /api/v1/admin/usage` bằng mã Member → `403 forbidden`. Gọi `/api/v1/me/tokens` bằng bất kỳ mã nào → `403 token_forbidden`.
5. Gọi 61 lần trong một phút → lần thứ 61 `429` kèm `Retry-After`.

## 3. Quản lý mã (US3)
1. Member thấy hai mã của mình, mã đã dùng hiện số yêu cầu hôm nay và lần dùng gần nhất.
2. Owner mở Settings → **API tokens**: thấy mã của mọi người; thu hồi một mã của Member → mã đó bị `401` ngay.

## 4. Claude Code qua MCP (SC-207, SC-208)
1. Ở khung **For agents**, chép lệnh `claude mcp add --transport http film-studio <URL>/api/mcp --header "Authorization: Bearer <mã>"` (mã có quyền dùng lượt) và chạy trong Claude Code.
2. Nhờ Claude Code: "Make a 20-second film in the Sci-Fi Sitcom Toon style about …, then give me the download link." → Claude Code dùng `list_styles`, `make_film`, `get_job` (cho tới khi xong), `film_download_url`, rồi tải phim bằng `curl`.
3. Nhờ Claude Code: "Learn a style from these 3 videos: …" → `start_upload` ×3 + `curl -T`, `learn_style`, trả lời hai lần duyệt bằng `get_review` / `answer_review`.
4. Với mã Member, Claude Code không thấy `worker_status` hay `usage`.

## 5. Bí mật
Tìm chuỗi mã vừa tạo trong `studio.db`, nhật ký web, proxy, worker, Caddy: không có (SC-204).
