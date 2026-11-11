# Contract: API chọn đề (online) và proxy

## API của người dùng (`api_online.py`, cần đăng nhập)

Kênh thuộc người đang đăng nhập (012). Người khác nhận **404**.

| Phương thức · Đường dẫn | Body | Trả về | Lỗi |
|---|---|---|---|
| `GET /channels/{slug}/topics` | | `{topics: [Topic không có raw], queue: [n…], usage: {today, limit}}` | `404` |
| `POST /channels/{slug}/topics/score` | `{topics: [str] (1–20), suggest?: bool}` | `201 Job` (loại `topics`) | `422` · `404` · `429 topics_limit` (kèm `retry_at`) · `503 youtube_not_ready` |
| `POST /channels/{slug}/topics/{n}/type` | `{type}` | `Topic` | `422` · `404` |
| `POST /channels/{slug}/topics/{n}/fit` | `{score: 0-10}` | `Topic` (tổng và kết luận tính lại) | `422` · `404` |
| `POST /channels/{slug}/topics/take` | `{allow_stale?: bool}` | `{topic: Topic, skipped: [{n, reason}]}`. Đề chuyển sang `in_progress` khi phim được giao | `409 none_left` (kèm `skipped`) · `404` |
| `GET /channels/{slug}/references` | | `{channels: [...]}` | `404` |
| `PUT /channels/{slug}/references` | `{channels: [id]}` (≤ 10) | `{channels}` | `422` · `404` |

- `POST /jobs` (phim) thêm `topic?: n`, kèm `channel` bắt buộc. Giao phim với `topic` thì đề chuyển sang `in_progress`, gắn phim. Việc phim xong thì đề chuyển sang `made`.
- **Settings (admin):**
  - `PUT /admin/youtube-key {key}`: thử khoá rồi lưu; trả `{set: true, last4}`. Khoá không bao giờ được trả về.
  - `DELETE /admin/youtube-key`: xoá khoá.
  - `GET /admin/settings` có thêm `youtube_key_set`, `youtube_key_last4`, `youtube_daily_units`, `topics_per_day` và `youtube_units_today`.

## Proxy (`proxy.py`)

`POST /internal/youtube`, kèm mã của việc (chỉ việc loại `topics`), body `{endpoint: "search"|"videos"|"channels"|"playlistItems", params: {…}}`:
- **200**: JSON của YouTube, có thêm `_cached: bool` và `_units: int`.
- **429 `youtube_quota`**: vượt `youtube_daily_units`.
- **503 `youtube_not_ready`**: chưa có khoá.
- **502 `youtube_error`**: YouTube báo lỗi; thông báo đã bỏ khoá.
- **403**: mã không phải của một việc `topics`.

Log chỉ ghi endpoint, số đơn vị và có dùng số liệu tạm hay không. Không ghi tham số `q` hay khoá.

## Giao diện

- **Trang kênh có mục "Topics":**
  - ô dán đề (mỗi dòng một đề), ô chọn "Suggest up to 10 more", nút "Score";
  - bảng điểm: kết luận, tổng, 5 điểm, kiểu đề (chọn được), điểm "hợp kênh" (sửa được), video bằng chứng (đường dẫn mở tab mới), ngày tuổi, nhãn "stale" khi quá 14 ngày;
  - hàng đợi, nút "Make a film" mở `#/new?channel=<slug>&topic=<n>` với ý tưởng điền sẵn;
  - mục "Reference channels" (danh sách id).
- **Settings → General (admin):** ô khoá YouTube (chỉ ghi), hiện "Key set (…abcd)"; hai số `youtube_daily_units` và `topics_per_day`; số đơn vị đã dùng hôm nay.
