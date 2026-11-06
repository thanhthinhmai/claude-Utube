# Research: Giao diện và API của xưởng (giai đoạn 1)

## 1. Làm sao để việc đang chạy "chờ" quyết định từ giao diện

- **Decision**: Claude gọi `sh bin/studio review request …` (tạo yêu cầu, in mã), rồi `sh bin/studio review wait <id> --timeout 540`. Lệnh `wait` đọc file quyết định mỗi 1 giây và kết thúc khi có quyết định (mã 0, in JSON quyết định), hoặc khi hết giờ (mã 3, Claude gọi lại). 540 giây là để dưới giới hạn 10 phút của một lệnh trong Claude Code.
- **Rationale**: Claude Code chỉ "đợi" được khi có một lệnh đang chạy; lệnh chặn có giới hạn là cách duy nhất để việc tự đi tiếp mà không cần người dùng gõ gì (FR-008). Hỏi mỗi giây cho độ trễ < 10 s (SC-003) mà không cần cơ chế thông báo giữa các tiến trình.
- **Duyệt trong khung chat (FR-009)**: người dùng bấm Esc để dừng lệnh đang chờ rồi gõ quyết định; Claude ghi lại bằng `review decide <id> --value … --source chat`.
- **Phiên đã đóng (FR-011)**: quyết định vẫn được ghi vào file; phiên mới gọi `review wait` và nhận ngay.
- **Alternatives considered**: Claude tự gọi lại `review status` theo vòng (tốn token mỗi vòng); webhook vào phiên Claude (không có trong Claude Code cục bộ).

## 2. Quyết định đầu tiên thắng (FR-010)

- **Decision**: Ghi quyết định bằng `os.open(path, O_CREAT | O_EXCL | O_WRONLY)` vào `.studio/reviews/<id>.decision.json`. Lần tạo thứ hai lỗi `FileExistsError` → API trả `409 already_decided`, CLI trả mã 4. Nội dung ghi vào file tạm rồi `os.link` sang tên đích (tạo nguyên tử, không bao giờ thấy file dở).
- **Rationale**: Đúng một người thắng, kể cả khi giao diện và khung chat cùng gửi; không cần cơ sở dữ liệu hay khoá.

## 3. Lưu trạng thái

- **Decision**: Mỗi việc là `.studio/jobs/<id>.json`; mỗi yêu cầu duyệt là `.studio/reviews/<id>.json`. Ghi nguyên tử (file tạm + `os.replace`). Cập nhật bước hay nhật ký dùng khoá theo việc (`fcntl.flock` trên `<id>.lock`). Mã việc dạng `j-YYYYMMDD-HHMMSS-xxxx`.
- **Rationale**: Không cơ sở dữ liệu (hiến pháp V); xem được bằng mắt; nhiều tiến trình CLI và máy chủ cùng đọc ghi an toàn. Giai đoạn 2 thay `store.py` bằng cơ sở dữ liệu mà giữ nguyên API.
- **Không còn hoạt động (FR-005)**: tính lúc đọc: `running` và `now − updated_at > 600 s` → trả `inactive`. Không cần tiến trình nền.

## 4. Máy chủ và tài liệu API

- **Decision**: FastAPI + uvicorn, tiền tố `/api/v1`, OpenAPI ở `/api/v1/openapi.json`, trang tài liệu `/api/v1/docs`. Lỗi có dạng `{"error": {"code": "...", "message": "..."}}`. Mọi bản ghi có `owner` (giai đoạn 1: `"local"`).
- **Rationale**: FR-015 và FR-016; dùng lại được ở giai đoạn 2.
- **Cần kiểm chứng khi code**: `FileResponse` của Starlette hỗ trợ `Range` (tua phim). Có kiểm thử gửi `Range: bytes=0-99` và chờ mã `206`.

## 5. Cập nhật trực tiếp

- **Decision**: Server-Sent Events `GET /api/v1/events`. Máy chủ quét thời gian sửa của `.studio/jobs` và `.studio/reviews` mỗi 1 giây, gửi `job.updated` / `review.created` / `review.decided` kèm mã. Trình duyệt dùng `EventSource` rồi gọi lại API để lấy dữ liệu. Mất kết nối thì `EventSource` tự nối lại.
- **Rationale**: Một chiều là đủ; không cần WebSocket; SC-002 < 5 s.

## 6. Bảo mật cục bộ

- **Decision**:
  1. uvicorn chỉ nghe `127.0.0.1` (FR-017: máy khác trong mạng không tới được).
  2. Kiểm `Host` ∈ {`127.0.0.1:<port>`, `localhost:<port>`}, chặn DNS rebinding.
  3. Mọi lệnh ghi (`POST`) bắt buộc `Content-Type: application/json` và header `X-Studio: 1`, nên một trang web lạ không gửi được nếu không qua preflight CORS, mà máy chủ không trả CORS.
  4. Kiểm địa chỉ nguồn là loopback.
- **Tệp (FR-019)**: chỉ phục vụ theo mã: tên phim, tên bộ, slug phong cách khớp `[a-z0-9-]{1,60}`, tên ảnh ghép khớp `v\d\d_\d{4}\.jpg`; đường dẫn được `resolve()` và phải nằm trong thư mục gốc tương ứng.
- **WSL**: WSL2 chuyển tiếp `localhost` của Windows vào WSL theo mặc định (`localhostForwarding`). **Cần kiểm chứng trên máy người dùng** (bước quickstart). Nếu không được: in thêm địa chỉ IP của WSL và hướng dẫn.

## 7. Bật nền và tắt

- **Decision**: `launcher.ensure()`:
  1. đọc `.studio/server.json` (`pid`, `port`); kiểm `pid` còn sống và `GET /api/v1/health` trả lời;
  2. nếu không: chọn cổng 8787 (bận thì thử 8788…8799), chạy `python -m uvicorn …` tách hẳn (`start_new_session=True`, đầu ra vào `.studio/server.log`), đợi `health` tối đa 5 s, ghi `server.json`.

  `ui stop` gửi `SIGTERM` theo `pid` (chỉ khi `pid` đó chạy đúng máy chủ của xưởng) rồi xoá `server.json`.
- **Rationale**: FR-020a; SC-001 < 5 s.

## 8. Nhịp sống cho lệnh dài

- **Decision**: `sh bin/studio job run <id> --step "…" -- <lệnh…>` chạy lệnh con, cứ 30 giây cập nhật `updated_at`, đưa 50 dòng đầu ra cuối vào nhật ký, giữ nguyên mã thoát của lệnh con.
- **Rationale**: Render phim có thể mất 10–30 phút; không có nhịp sống thì việc sẽ bị coi là "không còn hoạt động" sau 10 phút.

## 9. Giao diện

- **Decision**: Một trang `index.html` + `app.js` (định tuyến bằng `#/…`) + `style.css`, không thư viện. Trang: Việc · Việc (chi tiết) · Duyệt · Phim · Hồ sơ đo · Phong cách. Markdown (`STYLE.md`, tóm tắt duyệt) được máy chủ chuyển sang HTML bằng gói `markdown`, tắt HTML thô. Phụ đề `.srt` được chuyển sang WebVTT khi phục vụ.
- **Thông báo (FR-006a)**: `Notification.requestPermission()` sau khi người dùng bấm một nút, kèm giải thích; tiêu đề tab `(n) chờ duyệt · Xưởng phim`.
- **Rationale**: Không bước build (hiến pháp V); dễ sửa.

## 10. Việc và phim có sẵn từ trước

- **Decision**: `resources.py` liệt kê trực tiếp `films/*/`, `references/*/set.json`, `my-styles/*/style.json`, kể cả khi không có bản ghi việc (giả định trong spec).
