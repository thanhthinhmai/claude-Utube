# Quickstart: kiểm chứng giao diện và API

## Kiểm thử tự động

```sh
sh bin/studio deps ui
sh tests/ui/run.sh
```

Phủ:
- API: danh sách việc, chi tiết, `inactive` sau 600 s (giả thời gian), quyết định đầu tiên thắng (`409`), góp ý bắt buộc (`422`), giá trị không hợp lệ cho `style-1`, phim `Range` → `206`, `.srt` → WebVTT, ảnh ghép đã xoá → `removed`.
- Bảo mật: `Host` lạ → `403`; `POST` thiếu `X-Studio` → `403`; tên tệp có `..` hay `/` → `400`; không lộ `origin`, `title`, `channel` của video tham chiếu.
- SSE: tạo việc → nhận `job.updated` trong < 5 s.
- CLI: `job start` bật máy chủ (< 5 s) và in URL; `review wait` trả trong < 3 s sau khi `POST` quyết định; `review decide --source chat` sau `POST` → mã 4; `job run` giữ mã thoát lệnh con và gửi nhịp sống; `ui stop` tắt máy chủ.
- `tests/run.sh` và `tests/learn/run.sh` vẫn đạt.

## Trên máy người dùng (WSL)

1. `git pull` → `sh bin/studio deps ui` → `sh bin/studio ui`. Mở URL trong Edge/Chrome của Windows (SC-001: đo thời gian từ lệnh tới khi trang hiện).
2. Thấy phim `banh-mi-dem`, bộ `thu-kenh`, phong cách `toi-tram` (tài nguyên có sẵn từ trước). Phát phim có tiếng, bật phụ đề (SC-005).
3. Từ một máy khác (điện thoại cùng Wi-Fi), thử mở `http://<IP máy>:8787/` → không vào được (SC-006).
4. Trong Claude Code: "Học phong cách của kênh <link>, 3 video, tên bộ thu-ui". Bấm vào link Claude in; theo dõi các bước; khi có thông báo, duyệt lần 1 và lần 2 trên giao diện; không gõ gì trong khung chat (SC-009).
