# Contract: API kênh và bài học (online)

Các đường API đặt trong `api_online.py`, chỉ có ở chế độ online, và cần đăng nhập hoặc mã API (009).
- Mọi `POST` và `PUT` cần `X-Studio: 1`, như các đường khác.
- Kênh thuộc người đang đăng nhập. Người khác nhận **404** (SC-005).
- Lỗi dùng khuôn dạng chung `{"error": {code, message}}`.

| Phương thức · Đường dẫn | Body | Trả về | Lỗi |
|---|---|---|---|
| `GET /channels` | | `{channels: [{slug, name, language, seconds, style, lessons_active, lessons_draft}]}` | |
| `POST /channels` | Channel (không có `decisions`, `updated`) | `201 Channel` | `422 invalid` · `409 exists` · `409 limit` (20) |
| `GET /channels/{slug}` | | `Channel` kèm `lessons: [Lesson]` (cả `retired`) | `404` |
| `PUT /channels/{slug}` | các trường cần đổi | `Channel` | `422` · `404` |
| `POST /channels/{slug}/decisions` | `{text}` | `201 Channel` | `422` · `404` |
| `POST /channels/{slug}/lessons` | `{what, why, stop, film?, rule?}` | `201 Lesson` (`active`) | `422` · `409 limit` (200) |
| `PUT /channels/{slug}/lessons/{n}` | `{what?, why?, stop?, rule?}` | `Lesson` | `409 not_draft` · `404` |
| `POST /channels/{slug}/lessons/{n}/approve` | | `Lesson` | `409 not_draft` · `404` |
| `POST /channels/{slug}/lessons/{n}/retire` | | `Lesson` | `404` |
| `GET /lessons/shared` | | `{lessons: [Lesson]}` | `403` khi không phải admin |
| `POST /lessons/shared` | `{what, why, stop, rule?}` | `201 Lesson` | `403` · `422` |
| `POST /lessons/shared/{n}/retire` | | `Lesson` | `403` · `404` |

**Thay đổi ở đường có sẵn:**
- `POST /jobs` (phim) thêm `channel?`. Khi có kênh, `style` và `seconds` không bắt buộc và lấy từ hồ sơ. Kênh không có thì `404 not_found`; phong cách của kênh không còn thì `422 invalid`.
- `POST /jobs` (sửa phim, `revise_of`) thêm `lesson?: bool`. Phim gốc không có kênh mà vẫn gửi `lesson` thì `422`.
- `GET /jobs/{id}` có `input.channel`, `qa.publish.blocked_by_lesson` và `lesson_draft`.

**Giao diện (`app.js`):**
- **Thanh trên:** link "Channels" ở chế độ online.
- **`#/channels`:** bảng kênh và nút "New channel".
- **`#/channels/<slug>`:**
  - form hồ sơ (các trường của data-model; `hashtags` và `banned` mỗi mục một dòng);
  - danh sách quyết định với ô thêm;
  - bảng bài học với nút Approve, Edit (chỉ khi còn `draft`) và Retire;
  - form "Add a lesson".
- **Settings → Shared lessons (admin):** bảng bài học chung, form thêm, nút Retire.
- **Form giao phim:** `<select id="f-channel">` với "No channel" và các kênh. Chọn kênh thì điền phong cách và độ dài; người dùng vẫn sửa được.
- **Trang việc:**
  - ô "Request changes" có ô chọn "Save this as a lesson for <kênh>" khi phim có kênh;
  - khối Publish hiện "⚠ Do not publish yet: repeats lesson #n" khi `blocked_by_lesson` có số;
  - khi có `lesson_draft`: "A draft lesson is waiting on the channel page".
- **Màn hình 360 px:** không có thanh cuộn ngang.
